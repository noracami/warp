import { defineConfig, type PluginOption } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { appendFileSync, writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import type { IncomingMessage, ServerResponse } from 'node:http'

const HERE = dirname(fileURLToPath(import.meta.url))
const LOG_FILE = resolve(HERE, '.dev-log.jsonl')

function devLogPlugin(): PluginOption {
  return {
    name: 'dev-log-sink',
    apply: 'serve',
    configureServer(server) {
      writeFileSync(LOG_FILE, '')
      server.middlewares.use('/__log', (req: IncomingMessage, res: ServerResponse) => {
        if (req.method === 'DELETE') {
          writeFileSync(LOG_FILE, '')
          res.statusCode = 204
          return res.end()
        }
        if (req.method !== 'POST') {
          res.statusCode = 405
          return res.end()
        }
        const chunks: Buffer[] = []
        req.on('data', (c: Buffer) => chunks.push(c))
        req.on('end', () => {
          const body = Buffer.concat(chunks).toString('utf8')
          let parsed: Record<string, unknown>
          try {
            parsed = JSON.parse(body)
          } catch {
            parsed = { raw: body }
          }
          const line = JSON.stringify({ at: new Date().toISOString(), ...parsed }) + '\n'
          appendFileSync(LOG_FILE, line)
          res.statusCode = 204
          res.end()
        })
      })
    },
  }
}

export default defineConfig({
  plugins: [svelte(), devLogPlugin()],
})
