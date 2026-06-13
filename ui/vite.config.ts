import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    // give jsdom a real origin so localStorage works (config persistence)
    environmentOptions: { jsdom: { url: "http://localhost/" } },
  },
});
