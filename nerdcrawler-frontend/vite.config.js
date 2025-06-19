import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // allow external access
    allowedHosts: ['ap.projectkryptos.xyz'], // <- add your custom domain here
    port: 5173
  }
});
