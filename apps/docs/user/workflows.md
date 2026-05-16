# 工作流程

> 給 PM / Editor 角色看。建立可以自動跑的 application。

## 概念

Workflow = 一張節點圖（DAG）。每個節點做一件事：

| 節點類型     | 用途                                |
| ------------ | ----------------------------------- |
| `start`      | 入口（每張圖一個）                  |
| `llm`        | 呼叫 LLM                            |
| `knowledge_retrieval` | RAG 取知識庫片段           |
| `condition`  | true / false 分支                  |
| `switch`     | 多 case 分支                       |
| `loop` / `map` / `reduce` | 迭代處理 list           |
| `http_request` | 打外部 API                        |
| `variable`   | 設 / 算變數                         |
| `answer`     | 串接最終回應給使用者                |
| `webhook` / `notify` / `email` | 對外通知            |
| `schedule`   | 排程子任務                         |
| `transform` / `merge` | 資料整形                  |
| `parameter_extraction` | 從文字抽 JSON           |
| `intent`     | 意圖分類器                          |
| `image_generate` / `image_understand` | DALL-E / vision |
| `speech_to_text` / `text_to_speech`  | whisper / TTS  |
| `mcp_tool`   | 呼叫已註冊的 MCP server tool       |
| `shell`      | 跑 shell 指令（**需 sandbox 模式**）|

## Workflow Manager（執行策略）

設 application 時可選：

| 策略       | 行為                                                       |
| ---------- | ---------------------------------------------------------- |
| `simple`   | 預設；單線執行                                              |
| `retry`    | 節點失敗自動重試（exponential backoff，最多 3 次）         |
| `parallel` | 多子節點時 `asyncio.gather` 並行                           |
| `batch`    | `map` 節點分塊並行（chunk_size 預設 5）                    |
| `sandbox`  | `shell` 節點走 `SubprocessSandbox`（rlimit + timeout）     |

## 快捷鍵（編輯器）

| 鍵            | 動作                                |
| ------------- | ----------------------------------- |
| Cmd/Ctrl + S  | 儲存                                |
| Cmd/Ctrl + Z  | undo                                |
| Cmd/Ctrl + Y / Shift+Z | redo                       |
| Cmd/Ctrl + C / V | 複製 / 貼上選取節點              |
| Delete        | 刪除選取節點                        |
| 拖曳放開       | 自動 snap 到 20px 網格              |

## 版本

每次儲存可以手動 snapshot。歷史頁可一鍵 rollback；rollback 前會先把當前狀態快照保留 audit。
