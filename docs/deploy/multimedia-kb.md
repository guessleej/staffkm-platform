# 多媒體進知識庫 — 圖片 / 音檔 / 字幕 / 影片（v5.13）

知識庫除了文件，也能吃**圖片、音檔、字幕**，影片為 Phase 2。全部**地端優先、資料不出境**，切完一律走既有的 chunk → embedding → 檢索管線（命中可定位時間碼）。

---

## 1. 支援格式一覽

| 類型 | 副檔名 | 處理方式 | 額外需求 |
|---|---|---|---|
| 文件 | pdf/docx/doc/xlsx/xls/csv/odt/ods/txt/md/html | 既有 loader | — |
| 圖片 | png/jpg/jpeg/webp/tiff/bmp | **OCR 抽字 ＋ 看圖說話（vision LLM 描述）** | 描述需 VLM（見 §3）|
| 音檔 | mp3/wav/m4a/flac/ogg/aac | **地端 ASR 逐字稿（帶 [mm:ss] 時間碼）** | faster-whisper + worker ≥4g |
| 字幕 | srt/vtt | 直接解析成 [mm:ss] 文字 | 零成本、零依賴 |
| 影片 | mp4/mov/webm | **Phase 2（規劃中）** | ffmpeg 抽影格 + 音軌 ASR |

上傳上限：文件 50MB；音檔 500MB（`MAX_AUDIO_FILE_SIZE_MB`）。

---

## 2. 圖片：OCR ＋ 看圖說話（Phase 1）

每張圖**兩段並進**，合併後切塊嵌入：

```
【圖片文字】        ← tesseract OCR（或 OCR_ENGINE=vision）逐字
【圖片內容描述】    ← vision LLM「看圖說話」：人物/動作/場景/物件/圖表/流程圖的結構與意義
```

- **純圖像 / 流程圖 / 照片**也能被語意檢索（不再只靠 OCR 文字）。
- **視覺描述失敗 → 自動退回只用 OCR**（不會壞）。
- 關閉描述：`IMAGE_DESCRIBE_ENABLED=false`（只留 OCR）。

---

## 3. 視覺模型（VLM）設定 — 「看圖說話」要指到一個 vision 模型

`embedder` 容器只有 embedding 模型、**無 vision**。把 `VISION_OCR_*` 指向有 vision 模型的 endpoint：

```bash
# .env — 指向主機 ollama 的 vision 模型（範例：glm-ocr）
VISION_OCR_BASE_URL=http://host.docker.internal:11434/v1
VISION_OCR_MODEL=glm-ocr:bf16
```

- `glm-ocr` 偏 OCR，描述能力一般但可用。要更好的「看圖說話」建議拉通用 VLM
  （`ollama pull qwen2.5-vl` / `minicpm-v` / `llama3.2-vision`），再把 `VISION_OCR_MODEL` 換過去。
- 也可在 `/admin/models` 設 `default.vision`（runtime 解析、免改 env）。
- workflow 的「圖像理解」節點同樣吃 `default.vision`（v5.13 起不再寫死 gpt-4o）。

---

## 4. 音檔：地端 ASR（faster-whisper）

- **地端推論、音軌不出境**（符合公文/政府資料主權）。
- VAD 內建切段（自動跳靜音、長音檔分段），每段帶時間碼 → 逐字稿 `[mm:ss] ...`。
- 模型在 **knowledge-worker** 跑，首次轉錄會**下載 ~1.5GB 模型**（快取 `/app/.whisper_cache`）。

### 設定
```bash
ASR_MODEL=medium          # small(快/中文略差) | medium(預設) | large-v3(最準，需 worker ≥6g)
ASR_DEVICE=cpu            # 有 GPU 改 cuda
ASR_COMPUTE_TYPE=int8     # cpu 省記憶體；GPU 可 float16
ASR_LANGUAGE=zh           # 空字串 = 自動偵測
```

### 硬體需求（重要）
| ASR_MODEL | worker 記憶體上限 |
|---|---|
| small | ≥ 2g |
| **medium（預設）** | **≥ 4g** |
| large-v3 | ≥ 6g |

`knowledge-worker` 預設上限已設 `${KNOWLEDGE_WORKER_MEM_LIMIT:-4g}`（上限非保留，平時 idle ~300MB，
只有實際轉錄才用到）。**不用音檔 ASR** 可設 `KNOWLEDGE_WORKER_MEM_LIMIT=1g` 收斂。
記憶體不足時 worker 不會 OOM，而是把該文件標 error 並提示「請調高記憶體」。

> 字幕檔（.srt/.vtt）**零 ASR 成本**，會議有字幕時優先上字幕。

---

## 5. Phase 2 — 影片（規劃）

```
.mp4/.mov/.webm
  ├─ ffmpeg 抽關鍵影格（每 N 秒 / 場景變化）→ 每張 → vision 描述（＋必要時 OCR）
  └─ ffmpeg 抽音軌 → ASR（接既有 jt-live-whisper 容器 / faster-whisper）
  → 合併成「帶時間戳的逐字稿 ＋ 影格描述」→ 切塊嵌入（命中標第幾分幾秒）
```

ASR 後端 Phase 2 將支援指向**外部 jt-live-whisper 容器**（OpenAI-compat），免在本容器打包模型。

---

## 6. 疑難排解
- 圖片只出現「【圖片文字】」沒有描述 → VLM endpoint 沒配或模型不存在（看 worker log `image_describe_failed`），按 §3 設定。
- 音檔文件卡 error、訊息「ASR 不可用：記憶體不足」 → 調高 `KNOWLEDGE_WORKER_MEM_LIMIT` ≥4g 後重部署。
- 第一次轉音檔很久 → 在下載 faster-whisper 模型（~1.5GB），之後就快。
