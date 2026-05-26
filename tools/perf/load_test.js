// 全棧負載壓測 harness（k6）— 指向「已部署的 staffKM stack」打 HTTP，量 p95/錯誤率/吞吐。
//
// ⚠ 工具就緒、**非「跑過」**：本檔需要一個 served stack（gateway + services 全跑）才能真跑。
//   repo 內的 DB 層規模驗證見 tools/perf/scale_validation.py（那個是真跑過的）；本檔是 HTTP
//   全棧層，留待對 staging/prod 環境執行。runbook 見 docs/perf/load-test.md。
//
// 用法：
//   k6 run -e BASE_URL=https://staffkm.example.com \
//          -e USERNAME=loadtest -e PASSWORD=*** -e WORKSPACE_ID=<uuid> \
//          -e VUS=50 -e DURATION=3m tools/perf/load_test.js
//   （或給 -e TOKEN=<jwt> 跳過登入；都不給 → 只壓 /health 基線）
//
// 通過門檻（threshold，可用 env 調）：http_req_duration p95 < P95_MS、http_req_failed < ERROR_RATE。
// 預設**只讀**情境（list / search / health）— 不做寫入/刪除，避免污染目標環境。

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost';
const TOKEN_ENV = __ENV.TOKEN || '';
const USERNAME = __ENV.USERNAME || '';
const PASSWORD = __ENV.PASSWORD || '';
const WORKSPACE_ID = __ENV.WORKSPACE_ID || '';
const SEARCH_KB_ID = __ENV.SEARCH_KB_ID || '';
const SEARCH_QUERY = __ENV.SEARCH_QUERY || '請假 流程';

const VUS = parseInt(__ENV.VUS || '20', 10);
const DURATION = __ENV.DURATION || '1m';
const RAMP = __ENV.RAMP || '15s';
const P95_MS = parseInt(__ENV.P95_MS || '800', 10);
const ERROR_RATE = parseFloat(__ENV.ERROR_RATE || '0.01'); // 1%

// 自訂指標（分端點看延遲；business 失敗率獨立於 http 4xx/5xx）
const errors = new Rate('staffkm_errors');
const tList = new Trend('lat_list_conversations', true);
const tSearch = new Trend('lat_knowledge_search', true);
const tHealth = new Trend('lat_health', true);

export const options = {
  scenarios: {
    ramp: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: RAMP, target: VUS },     // 爬升
        { duration: DURATION, target: VUS }, // 穩態
        { duration: RAMP, target: 0 },       // 降載
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    http_req_failed: [`rate<${ERROR_RATE}`],
    http_req_duration: [`p(95)<${P95_MS}`],
    staffkm_errors: [`rate<${ERROR_RATE}`],
  },
};

// setup 跑一次：拿 token（TOKEN 直接給 > 帳密登入 > 無 → health-only）
export function setup() {
  if (TOKEN_ENV) return { token: TOKEN_ENV };
  if (USERNAME && PASSWORD) {
    const res = http.post(
      `${BASE_URL}/api/v1/auth/login`,
      JSON.stringify({ username: USERNAME, password: PASSWORD }),
      { headers: { 'Content-Type': 'application/json' }, tags: { name: 'login' } },
    );
    const ok = check(res, { 'login 200': (r) => r.status === 200 });
    if (ok) {
      try {
        const tok = res.json('data.access_token');
        if (tok) return { token: tok };
      } catch (_e) { /* fallthrough */ }
    }
    console.warn('login 失敗 → 退化為 health-only 壓測');
  }
  return { token: '' };
}

function authHeaders(token) {
  const h = { 'Content-Type': 'application/json' };
  if (token) h['Authorization'] = `Bearer ${token}`;
  if (WORKSPACE_ID) h['X-Workspace-ID'] = WORKSPACE_ID; // workspace-scoped 端點需要（見 CLAUDE.md §7）
  return h;
}

export default function (data) {
  const token = data && data.token;

  // 基線：health（永遠打，反映 gateway 純轉發吞吐）
  group('health', () => {
    const res = http.get(`${BASE_URL}/api/v1/health`, { tags: { name: 'health' } });
    tHealth.add(res.timings.duration);
    errors.add(!check(res, { 'health ok': (r) => r.status === 200 }));
  });

  if (token) {
    // 讀熱路徑 1：列對話
    group('list_conversations', () => {
      const res = http.get(`${BASE_URL}/api/v1/chat/conversations?page=1&page_size=20`,
        { headers: authHeaders(token), tags: { name: 'list_conversations' } });
      tList.add(res.timings.duration);
      errors.add(!check(res, { 'list 2xx': (r) => r.status >= 200 && r.status < 300 }));
    });

    // 讀熱路徑 2：知識檢索（RAG hot path；需給 SEARCH_KB_ID）
    if (SEARCH_KB_ID) {
      group('knowledge_search', () => {
        const body = JSON.stringify({ kb_ids: [SEARCH_KB_ID], query: SEARCH_QUERY, top_k: 5 });
        const res = http.post(`${BASE_URL}/api/v1/knowledge/search`, body,
          { headers: authHeaders(token), tags: { name: 'knowledge_search' } });
        tSearch.add(res.timings.duration);
        errors.add(!check(res, { 'search 2xx': (r) => r.status >= 200 && r.status < 300 }));
      });
    }
  }

  sleep(Math.random() * 1 + 0.5); // think-time 0.5~1.5s，避免不真實的零間隔狂打
}
