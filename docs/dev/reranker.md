# Reranker — Cross-encoder service（v3.4 P3）

## 背景

v3.3-C3 在 `services/knowledge/app/core/reranker.py` 加了 `_rerank_ollama`，
用「query / doc 各自跑 embedding 後算 cosine」當 fallback。問題：

- bi-encoder 的相似度跟 cross-encoder 的相關性**完全不是同一件事**
- 對長 doc / 多語對齊效果差，rerank 後 top-k 順序常常跟單純 vector search 差不多
- 沒有 query-aware 的 token interaction，failures 都 silent

v3.4-P3 引入獨立 cross-encoder service（`services/reranker/`），預設跑
`BAAI/bge-reranker-v2-m3`（多語、512 token、~568MB 權重）。

## 啟用

profile opt-in，預設不會被 `docker compose up -d` 拉起來：

```bash
docker compose --profile reranker up -d reranker
# 首次 cold start ~2 min（download model ~1GB 含 tokenizer / config）
# 之後 model 寫進 named volume reranker_hf_cache，restart 秒起
```

健康檢查：

```bash
curl http://localhost:8010/health
# {"status":"ok","service":"reranker","model":"BAAI/bge-reranker-v2-m3"}
```

## API

`POST /rerank`

```json
{
  "query": "公司去年營收",
  "documents": ["2024 年度報告...", "員工手冊...", "..."],
  "top_n": 5
}
```

回：

```json
{
  "indices": [0, 2, 1],
  "scores": [8.42, 1.05, -2.31]
}
```

- `indices` 對應原 `documents` 的 0-based 位置，依分數**降序**
- `scores` 是 cross-encoder logit；可正可負，沒有 0~1 normalize
- 上限 200 docs / request，內部會用 `BATCH_SIZE=32` 分批跑

額外端點：`GET /health`、`GET /metrics`（Prometheus）。

## 從 knowledge service 使用

`services/knowledge/app/core/reranker.py` 的 dispatcher 新增 `cross_encoder` 類型：

```json
{
  "type": "cross_encoder",
  "endpoint": "http://reranker:8000"
}
```

KB / hit-test API 帶這個 reranker_config 進去就會 route 過去；失敗
fallback 回原始順序（不會炸 search）。

## 效能參考

|              | top-20 doc, max_length=512 |
| ------------ | -------------------------- |
| CPU (4 vCPU) | ~50 ms                     |
| CUDA (T4)    | ~5 ms                      |

torch 預設裝 CPU wheel。要 GPU 要自己改 Dockerfile（裝 cu121 wheel + base image 換）。

## 模型選擇

| 模型                       | 大小   | 語言                | 備註                  |
| -------------------------- | ------ | ------------------- | --------------------- |
| BAAI/bge-reranker-v2-m3    | ~568MB | 100+ 多語（含中文）| **預設**，準確 + 快   |
| BAAI/bge-reranker-large    | ~1.3GB | 中 / 英            | 精度略高，慢          |
| 自家 fine-tune             | -      | 對 domain corpus    | 給 PoC 後 production  |

切換：`.env` 設 `RERANKER_MODEL=...` 再 `docker compose --profile reranker up -d --force-recreate reranker`。
