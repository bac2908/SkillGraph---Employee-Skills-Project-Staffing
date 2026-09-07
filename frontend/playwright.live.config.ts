import { defineConfig } from '@playwright/test';
import config from './playwright.config';

export default defineConfig(config, { testMatch: 'live.spec.ts', fullyParallel: false, workers: 1 });
