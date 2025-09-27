import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    port: 3000,
  },
  // TODO: config vite path of build output
  build: {
    outDir: '../release',
  },
  define: {
    // Make environment variables available at build time
    __DEV__: JSON.stringify(mode === 'development'),
  },
}))
