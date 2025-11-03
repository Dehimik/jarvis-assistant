import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': '/src' } },  // працює і в dev, і в build
  server: { port: 5173, strictPort: true },
  base: './',                            // важливо для Tauri build
})
