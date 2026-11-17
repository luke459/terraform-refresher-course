import {defineConfig} from '@playwright/test';
import {fileURLToPath} from 'node:url';

const root=fileURLToPath(new URL('../../',import.meta.url));
export default defineConfig({
  testDir:'./live',workers:1,timeout:300000,
  use:{baseURL:'http://127.0.0.1:8083',viewport:{width:1440,height:1000},actionTimeout:20000,screenshot:'only-on-failure',trace:'retain-on-failure'},
  webServer:{command:`${root}/.venv/bin/uvicorn runner.api.main:app --host 127.0.0.1 --port 8083`,cwd:root,
    env:{TFPREP_STATE:`${root}/.state/live-browser-${process.pid}`,TFPREP_WORKSPACES:`${root}/.state/live-browser-workspaces-${process.pid}`},
    url:'http://127.0.0.1:8083/api/health',reuseExistingServer:false,timeout:30000},
});
