import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
export default defineConfig({
  testDir: './tests', fullyParallel: false, workers: 1,
  use: { baseURL: 'http://127.0.0.1:8081', viewport: { width: 1440, height: 1000 }, screenshot: 'only-on-failure' },
  webServer: {
    command: `${root}/.venv/bin/uvicorn runner.api.main:app --host 127.0.0.1 --port 8081`,
    cwd: root,
    env: { TFPREP_STATE: `${root}/.state/browser-tests`, TFPREP_WORKSPACES: `${root}/.state/browser-workspaces` },
    url: 'http://127.0.0.1:8081/api/health', reuseExistingServer: false, timeout: 30000,
  },
});
