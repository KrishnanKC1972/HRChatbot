import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'production' ? '/app/' : '/',
  server: {
    port: 5173,
    proxy: {
      '/chat': 'http://127.0.0.1:8000',
      '/metrics': 'http://127.0.0.1:8000',
      '/history': 'http://127.0.0.1:8000',
      '/evaluate': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
}))
