import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '../../frontend/src'),
      '@schemas': path.resolve(__dirname, '../../schemas')
    }
  },
  build: {
    outDir: 'build',
    emptyOutDir: true
  },
  server: {
    port: 3000,
    host: '0.0.0.0'
  }
})
