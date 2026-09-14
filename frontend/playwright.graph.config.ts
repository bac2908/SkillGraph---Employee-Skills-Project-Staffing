import { defineConfig } from '@playwright/test';
import config from './playwright.config';

if (!/^\d{18}$/.test(process.env.SKILLGRAPH_E2E_RUN || '') || !process.env.SKILLGRAPH_E2E_APPROVED)
  throw new Error(
    'Use backend: python -m scripts.graph_e2e run with explicit test-target approval.',
  );

export default defineConfig({
  ...config,
  testMatch: 'graph.spec.ts',
  outputDir: `test-results/graph-${process.env.SKILLGRAPH_E2E_RUN}`,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 600000,
  expect: { timeout: 30000 },
  use: {
    ...config.use,
    baseURL: 'http://127.0.0.1:5175',
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
  webServer: [
    {
      command: '.venv\\Scripts\\python.exe -B -m tests.graph_browser_server',
      cwd: '../backend',
      url: 'http://127.0.0.1:18001/health/ready',
      timeout: 60000,
      reuseExistingServer: false,
    },
    {
      command: 'node node_modules/vite/bin/vite.js --port 5175',
      env: { SKILLGRAPH_API_TARGET: 'http://127.0.0.1:18001' },
      url: 'http://127.0.0.1:5175',
      reuseExistingServer: false,
    },
  ],
});
