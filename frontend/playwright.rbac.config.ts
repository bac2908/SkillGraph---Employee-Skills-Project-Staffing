import { defineConfig } from '@playwright/test';
import config from './playwright.auth-stack.config';

export default defineConfig({
  ...config,
  testMatch: 'rbac.spec.ts',
  outputDir: 'test-results/rbac',
  retries: 0,
  use: { ...config.use, video: 'off' },
  webServer: [
    {
      command: '.venv\\Scripts\\python.exe -B -m tests.auth_browser_server --rbac',
      cwd: '../backend',
      url: 'http://127.0.0.1:18000/health',
      reuseExistingServer: false,
    },
    {
      command: 'node node_modules/vite/bin/vite.js --port 5174',
      env: { SKILLGRAPH_API_TARGET: 'http://127.0.0.1:18000' },
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
    },
  ],
});
