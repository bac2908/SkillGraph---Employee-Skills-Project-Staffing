import { defineConfig } from '@playwright/test';
import config from './playwright.config';

export default defineConfig(config, {
  testMatch: 'auth-stack.spec.ts',
  outputDir: 'test-results/auth-stack',
  fullyParallel: false,
  workers: 1,
  use: { ...config.use, baseURL: 'http://127.0.0.1:5174', trace: 'off', screenshot: 'off' },
  webServer: [
    {
      command: '.venv\\Scripts\\python.exe -B -m tests.auth_browser_server',
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
