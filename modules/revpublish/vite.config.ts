import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/revflow_os/revpublish/',
  publicDir: 'frontend/public', // Serve files from frontend/public directory
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
      // Proxy all /api/* requests to backend on port 8550
      // When frontend requests: http://localhost:3550/api/sites
      // Vite proxies to: http://127.0.0.1:8550/api/sites
      '/api': {
        target: 'http://127.0.0.1:8550',
        changeOrigin: true,
        secure: false,
        // Keep the /api path - backend expects /api/sites
        // No rewrite needed - pass through as-is
      },
      // Also handle requests with base path
      '/revflow_os/revpublish/api': {
        target: 'http://127.0.0.1:8550',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/revflow_os\/revpublish\/api/, '/api'),
      },
    }
  }
})