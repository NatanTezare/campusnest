import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, forward API calls and uploaded photos to the FastAPI server.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/uploads': 'http://127.0.0.1:8000',
    },
  },
})
