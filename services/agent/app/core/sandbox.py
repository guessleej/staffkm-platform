"""Sandbox 子程序執行器（M2 收尾 — Sandbox 容器最小可運作版）。

設計目標
- 為 workflow `shell` 節點與任何 user-supplied 程式碼提供基本隔離與資源上限
- 不依賴特權（不需要 root / Docker-in-Docker / privileged container），只靠 OS 原生機制：
    * resource.setrlimit       — CPU 時間 / 記憶體 / 開檔上限 / 子程序上限
    * asyncio.wait_for         — wall-clock timeout
    * subprocess.PIPE          — stdout/stderr 捕捉
    * shell=False + 白名單 args — 防止 command injection
- 不阻塞 main event loop（用 asyncio.create_subprocess_exec）

未涵蓋（M4 升級）
- 網路隔離（需要 namespace / nsjail）
- 檔案系統隔離（需要 chroot / mount namespace / read-only filesystem）
- syscall filtering（需要 seccomp）

未來升級路徑：
- M4-A：把 SubprocessSandbox 換成 NsjailSandbox（args 不變，後端用 nsjail）
- M4-B：把整個 agent service container 自身降權；shell 節點走 sidecar
- M4-C：firecracker microVM（per-execution；最強隔離）

呼叫端：
    res = await run_sandboxed(
        ["/usr/bin/python3", "-c", "print('hi')"],
        stdin="optional input\\n",
        timeout_sec=10,
        mem_mb=128,
        cpu_secs=5,
    )
    print(res.stdout, res.exit_code)
"""
from __future__ import annotations

import asyncio
import os
import resource
from dataclasses import dataclass


@dataclass
class SandboxResult:
    exit_code: int
    stdout:    str
    stderr:    str
    timed_out: bool
    elapsed_ms: int


def _preexec_apply_limits(*, mem_mb: int, cpu_secs: int, nproc: int, nofile: int):
    """子程序 fork 後、exec 前套用 rlimit。

    macOS 對 RLIMIT_AS 支援不一致，遇到 OSError 退讓不掛掉父程序。
    """
    def _apply():
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_secs, cpu_secs))
        except (ValueError, OSError):
            pass
        try:
            mem_bytes = mem_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except (ValueError, OSError):
            pass
        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (nofile, nofile))
        except (ValueError, OSError):
            pass
        try:
            resource.setrlimit(resource.RLIMIT_NPROC, (nproc, nproc))
        except (ValueError, OSError, AttributeError):
            pass
        # 新 session 避免子程序拿到 controlling tty
        try:
            os.setsid()
        except OSError:
            pass
    return _apply


async def run_sandboxed(
    argv: list[str],
    *,
    stdin:        str | None = None,
    timeout_sec:  int        = 10,
    mem_mb:       int        = 128,
    cpu_secs:     int        = 5,
    nproc:        int        = 16,
    nofile:       int        = 64,
    cwd:          str | None = None,
    env:          dict[str, str] | None = None,
) -> SandboxResult:
    """在資源受限的子程序中執行 argv，回傳 SandboxResult。

    - shell=False（asyncio.create_subprocess_exec），須 caller 自行解析 args
    - 預設 env 只保留 PATH / LANG / LC_ALL（不繼承父程序所有環境）
    - timeout 觸發時送 SIGKILL 並回 timed_out=True
    """
    import time
    safe_env = env or {
        "PATH":    "/usr/local/bin:/usr/bin:/bin",
        "LANG":    "C.UTF-8",
        "LC_ALL":  "C.UTF-8",
    }
    start = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.PIPE if stdin is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=safe_env,
        preexec_fn=_preexec_apply_limits(
            mem_mb=mem_mb, cpu_secs=cpu_secs, nproc=nproc, nofile=nofile,
        ),
    )
    timed_out = False
    try:
        out, err = await asyncio.wait_for(
            proc.communicate(input=stdin.encode() if stdin else None),
            timeout=timeout_sec,
        )
    except asyncio.TimeoutError:
        timed_out = True
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        out, err = b"", b""

    elapsed_ms = int((time.monotonic() - start) * 1000)
    return SandboxResult(
        exit_code=proc.returncode if proc.returncode is not None else -1,
        stdout=out.decode("utf-8", errors="replace"),
        stderr=err.decode("utf-8", errors="replace"),
        timed_out=timed_out,
        elapsed_ms=elapsed_ms,
    )


async def run_python_code(
    code: str,
    inputs: dict,
    *,
    timeout_sec: int = 15,
    mem_mb:      int = 256,
    cpu_secs:    int = 10,
) -> dict:
    """在 sandbox 子程序執行使用者 `def run(**kwargs) -> dict` 程式碼。

    供 custom / AI 生成工具（tool_exec）與 workflow code 節點共用（DRY）。
    以 stdin 傳 JSON 參數，從 stdout 的 marker 之後取回 JSON 結果。

    回傳 dict：
      ok:         成功且 output 不含 error
      output:     run() 回傳的 dict（解析失敗為 None）
      error:      失敗原因（逾時 / 非零碼 / run() 內部回傳 error）
      elapsed_ms: 耗時
      raw:        無法解析 marker 時的原始 stdout（debug；成功時 None）

    隔離：rlimit（CPU/記憶體/開檔/子程序）+ wall-clock timeout + 清空環境
    + `-I` isolated 模式。網路 / fs namespace 隔離待 M4（見本檔頭）。
    """
    import json as _json
    import sys
    import time

    if not code or "def run" not in code:
        return {"ok": False, "output": None, "error": "code 缺少 def run(**kwargs)", "elapsed_ms": 0, "raw": None}

    marker = "__STAFFKM_RESULT__"
    harness = (
        "import sys, json\n"
        f"{code}\n"
        "\nif __name__ == '__main__':\n"
        "    _args = json.loads(sys.stdin.read() or '{}')\n"
        "    try:\n"
        "        _res = run(**_args)\n"
        "    except Exception as _e:\n"
        "        _res = {'error': str(_e)}\n"
        f"    sys.stdout.write({marker!r} + json.dumps(_res, ensure_ascii=False, default=str))\n"
    )
    started = time.monotonic()
    res = await run_sandboxed(
        [sys.executable, "-I", "-c", harness],
        stdin=_json.dumps(inputs, ensure_ascii=False),
        timeout_sec=timeout_sec, mem_mb=mem_mb, cpu_secs=cpu_secs,
    )
    elapsed = int((time.monotonic() - started) * 1000)
    if res.timed_out:
        return {"ok": False, "output": None, "error": f"執行逾時（>{timeout_sec}s）", "elapsed_ms": elapsed, "raw": None}
    if res.exit_code != 0:
        return {"ok": False, "output": None, "error": (res.stderr or "程式以非零碼結束").strip()[:1000], "elapsed_ms": elapsed, "raw": None}
    out = None
    idx = res.stdout.rfind(marker)
    if idx >= 0:
        try:
            out = _json.loads(res.stdout[idx + len(marker):])
        except Exception:
            out = None
    err = out.get("error") if isinstance(out, dict) else None
    return {
        "ok": isinstance(out, dict) and err is None,
        "output": out if isinstance(out, dict) else None,
        "error": err,
        "elapsed_ms": elapsed,
        "raw": None if isinstance(out, dict) else (res.stdout[:2000] or None),
    }
