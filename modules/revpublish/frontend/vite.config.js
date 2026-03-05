import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/revflow_os/revpublish/',
  server: {
    host: '0.0.0.0',
    port: 3550,
    allowedHosts: [
      'automation.smarketsherpa.ai',
      '217.15.168.106',
      'localhost',
      '127.0.0.1'
    ],
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8550',
        changeOrigin: true
      },
      // When app is served at base path, API may be requested as /revflow_os/revpublish/api/...
      '/revflow_os/revpublish/api': {
        target: 'http://127.0.0.1:8550',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/revflow_os\/revpublish/, '')
      }
    }
  }
})
