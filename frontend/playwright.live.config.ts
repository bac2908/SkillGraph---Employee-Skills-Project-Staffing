import { defineConfig } from '@playwright/test';
import config from './playwright.config';

export default defineConfig(config, {
  testMatch: 'live.spec.ts',
  outputDir: 'test-results/live',
  fullyParallel: false,
  workers: 1,
  use: { ...config.use, trace: 'off', screenshot: 'off', video: 'off' },
});
