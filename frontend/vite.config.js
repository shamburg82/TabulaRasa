import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// const proxyPaths = ['/studies', '/reference', '/search', '/healthz'];

// Vite dev server proxies /api -> FastAPI on port 8000.
// In production both are served from the same Posit Connect URL,
// so /api works without any proxy.
export default defineConfig({
  plugins: [react()],
  base: './',
  // server: {
  //   host: true,
  //   port: 5173,
  //   strictPort: true,
  //   hmr: {
  //     protocol: 'ws',
  //     host: 'localhost'
  //   },
  //   allowedHosts: ['dse-prod-wb.jazzpharma.com']
  // },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
