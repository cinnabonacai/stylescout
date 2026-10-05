import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Allow the dev server to be reached by its host-mapped port when
    // previewed from outside this container.
    host: '0.0.0.0',
  },
})
