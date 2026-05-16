# RFC-010 — Workflow Sandbox 隔離策略

| 項目      | 內容                                           |
| --------- | ---------------------------------------------- |
| 狀態      | Draft（M2 收尾：subprocess + rlimit 版上 main） |
| 提案日期  | 2026-05-16                                     |
| 對應里程碑 | M2 GA（最小可運作版） / M4 進階能力（強化版）   |
| 相關 PR   | feat/m2e-sandbox-isolation                     |

## 1. 動機

Workflow Engine v2 設計上要支援 `shell`、`mcp_tool`、未來的 user-supplied code
等「會執行外部程式」的節點。目前 executor 直接以 `asyncio.create_subprocess_shell`
跑這類指令會帶來明顯風險：

- 沒有 CPU / 記憶體上限 → 一個壞掉的指令可拖垮整個 agent service
- 環境變數全繼承 → 洩漏 DB_URL / API key
- 沒有逾時 → 死迴圈會卡住 worker
- shell=True 容易被注入

故需要一個明確的 sandbox 層，把所有 user-supplied 程式碼執行集中收斂。

## 2. 範圍切割（漸進升級）

| 階段      | 後端              | 風險覆蓋                                           |
| --------- | ----------------- | -------------------------------------------------- |
| **M2 收尾（本 PR）** | SubprocessSandbox | CPU / 記憶體 / 開檔 / 子程序上限 + timeout + 環境變數白名單 + shell=False + argv 絕對路徑 |
| M4-A      | NsjailSandbox     | + filesystem 隔離（chroot / mount ns）+ syscall filtering（seccomp）+ 網路 ns |
| M4-B      | Firecracker microVM | + KVM 級隔離；per-execution VM；強網路隔離     |

> 升級時 `run_sandboxed()` 函式簽章保持不變；caller 不用改。

## 3. 本 PR 範圍（M2 收尾最小可運作）

### 3.1 模組

```
services/agent/app/core/sandbox.py
└─ run_sandboxed(argv, *, stdin, timeout_sec, mem_mb, cpu_secs, nproc, nofile,
                  cwd, env) -> SandboxResult
```

### 3.2 隔離機制

- `asyncio.create_subprocess_exec(..., preexec_fn=apply_rlimits)`：
  - `RLIMIT_CPU`     — CPU 秒
  - `RLIMIT_AS`      — 虛擬位址空間（≈ 記憶體；macOS 容錯）
  - `RLIMIT_NOFILE`  — 開檔數
  - `RLIMIT_NPROC`   — 子程序數
- `asyncio.wait_for(..., timeout=timeout_sec)`：wall-clock 上限，逾時 SIGKILL
- `shell=False` + argv 必須 list[str]：完全避開 shell 注入
- 環境變數預設只保留 `PATH / LANG / LC_ALL`，不繼承父程序所有環境
- `os.setsid()`：脫離 controlling tty
- `stdout/stderr` 由父程序 PIPE 捕捉

### 3.3 Workflow 接入

新增 `shell` 節點型別：

```yaml
- node_type: shell
  config:
    argv: ["/usr/bin/python3", "-c", "print(2+2)"]
    stdin: "optional input"
    timeout_sec: 10
    mem_mb: 128
    cpu_secs: 5
    output_variable: shell_output   # context[shell_output] = {stdout, stderr, exit_code, ...}
```

**強制檢查**（雙保險）：
1. `workflow_manager` 必須是 `'sandbox'`，否則 yield `shell_blocked` 並中止
2. `argv` 必須是 `list[str]` 且 `argv[0]` 為絕對路徑

→ 這保證 staffKM 預設（`simple` manager）下 shell 節點完全無法執行，
   只有明確切到 sandbox 才會走 sandbox 通道。

### 3.4 SSE 事件

- `shell_exec` — 開始執行（含 argv / timeout）
- `shell_done` — 結束（exit_code / timed_out / elapsed_ms）
- `shell_blocked` — 被安全檢查阻擋（manager 不對 / argv 不合法）

## 4. 未涵蓋（明確列出）

- **網路隔離**：subprocess 仍可走 outbound network（會繼承父 socket / 走預設路由）。
  M4-A 用 nsjail `--disable_proc --use_cgroupv2 --net=none` 解決。
- **檔案系統隔離**：subprocess 看得到整個 root fs。M4-A 用 chroot + bind mounts。
- **syscall filtering**：不擋危險 syscall（如 fork bomb 受 RLIMIT_NPROC 約束但
  open(/etc/shadow) 還是會 readable）。M4-A 用 seccomp。
- **多租戶熔斷**：一個 workspace 的 shell 節點吃滿 CPU 可拖慢其他 workspace。
  M4-A 用 cgroup v2 per-workspace。

## 5. 風險與權衡

- **macOS 開發環境**：`RLIMIT_AS` / `RLIMIT_NPROC` 在 macOS 行為與 Linux 不一致；
  `_preexec_apply_limits` 已用 try/except 容錯。生產走 Linux 容器，影響限定 dev 機。
- **rlimit 不是強隔離**：rlimit 只防意外，不防有惡意意圖的程式。
  staffKM 假設 workflow 由 workspace editor 以上建立 → 已有 RBAC 守第一線；
  sandbox 是縱深防禦的最後一層，rlimit 等級足以擋掉「壞掉 / 失控」類事故。
- **不引入新依賴**：本 PR 只用 Python stdlib (`asyncio`, `resource`, `subprocess`)；
  M4 升 nsjail / firecracker 才會加 deps。

## 6. 升級判準

升級到 M4-A（nsjail）的觸發條件（任一）：
- 開始接受 workspace member（非 admin）建立 shell 節點
- 出現需要跑「不信任原始碼」的場景（如 user uploaded Python script）
- 安全事件回報：sandbox 程式跑到資料外洩
