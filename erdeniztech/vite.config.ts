import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const mehlrOrigin = env.MEHLR_ORIGIN || 'http://127.0.0.1:8001'
  const mehlrServiceKey = env.MEHLR_SERVICE_API_KEY || ''

  const mehlrProxy = {
    '/mehlr': {
      target: mehlrOrigin,
      changeOrigin: true,
      configure(proxy) {
        proxy.on('proxyReq', (proxyReq) => {
          if (mehlrServiceKey) {
            proxyReq.setHeader('X-API-Key', mehlrServiceKey)
          }
        })
      },
    },
  }

  return {
    // Cloudflare Pages (subpath/relative assets) safe default
    base: './',
    plugins: [react()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: { proxy: mehlrProxy },
    preview: { proxy: mehlrProxy },
  }
})

