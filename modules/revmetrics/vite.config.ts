import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  base: '/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '../../frontend/src'),
      '@schemas': path.resolve(__dirname, '../../schemas')
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  },
  server: {
    port: 3400,
    host: '0.0.0.0',
    proxy: {
      '/api/revmetrics': {
        target: 'http://localhost:8401',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/revmetrics/, '')
      },
      '/schemas': {
        target: 'http://localhost',
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 3400,
    host: '0.0.0.0'
  }
})
