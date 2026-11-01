import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The UI calls /api/...; Vite forwards it to the Thunder-X service.
const THUNDERX_API = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: THUNDERX_API,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
