# @staffkm/sdk

TypeScript SDK for the staffKM platform.

## Install

```bash
npm install @staffkm/sdk
# or, in this monorepo:
pnpm --filter @staffkm/sdk install
```

## Quick start

```typescript
import { StaffKM } from '@staffkm/sdk'

const client = new StaffKM({
  baseURL: 'https://staffkm.example.com',
  apiKey: 'sk_xxx',
  workspaceId: 'ws_abc',
})

// non-streaming
const res = await client.chat.send('app_123', 'hello')
console.log(res)

// streaming
await client.chat.stream('app_123', 'tell me a joke', {
  onToken: (t) => process.stdout.write(t),
  onDone: () => console.log('\n[done]'),
})
```

## Exposed resources

| Resource | Methods |
|---|---|
| `auth` | login, refresh, me |
| `workspaces` | list, create, get |
| `knowledge` | kbs.list/create, docs.upload, hitTest |
| `applications` | list, create, get, run |
| `chat` | send, stream |
| `quota` | summary, set, list |
| `billing` | users.list, users.detail, users.csv |
| `plugins` | list, reload |

See `docs/dev/sdks.md` for the cross-language overview.
