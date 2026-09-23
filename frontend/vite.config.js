import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
  },
  server: {
    port: 5173,
    proxy: {
      // REST API -> Django
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      // WebSockets -> Django Channels (used from Phase 6 onward)
      '/ws': {
        target: 'ws://127.0.0.1:8080',
        changeOrigin: true,
        ws: true,
      },
      // User-uploaded avatars -> Django (MEDIA_URL)
      '/media': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
  },
})