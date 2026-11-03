import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), "REACT_APP_"), ...process.env };
  return {
    plugins: [react()],
    define: { "process.env.REACT_APP_BACKEND_URL": JSON.stringify(env.REACT_APP_BACKEND_URL) },
    server: { host: "0.0.0.0", port: 3000, allowedHosts: true, hmr: { clientPort: 443 } },
    build: { outDir: "build" },
  };
});
