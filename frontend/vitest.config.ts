import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  // run in LA so the "don't shift dates through UTC" test actually means something
  test: { env: { TZ: 'America/Los_Angeles' } },
})
