/**
 * Stream tokens from a chat application.
 *
 * Usage:
 *   BASE_URL=http://localhost API_KEY=sk_xxx WORKSPACE_ID=ws_abc APP_ID=app_123 \
 *     ts-node examples/chat-stream.ts
 */
import { StaffKM } from '../src'

async function main() {
  const client = new StaffKM({
    baseURL: process.env.BASE_URL!,
    apiKey: process.env.API_KEY!,
    workspaceId: process.env.WORKSPACE_ID,
  })
  const appId = process.env.APP_ID!
  await client.chat.stream(appId, '用一句話介紹 staffKM。', {
    onToken: (t) => process.stdout.write(t),
    onDone: () => process.stdout.write('\n'),
    onError: (e) => console.error('stream error:', e),
  })
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
