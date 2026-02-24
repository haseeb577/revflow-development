import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    proxy: {
      '/api': {
        target: 'http://localhost:8100',
        changeOrigin: true
      }
    }
  },
  // Use root path in dev mode for easier development
  // In production, this will be overridden by build command
  base: '/'
})

