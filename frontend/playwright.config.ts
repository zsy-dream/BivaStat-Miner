import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: {
    timeout: 20_000,
  },
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'C:\\Users\\acer\\Desktop\\编程开发\\软著开发\\双变量关联挖掘与非参数统计分析平台_V1.0\\venv\\Scripts\\python.exe C:\\Users\\acer\\Desktop\\编程开发\\软著开发\\双变量关联挖掘与非参数统计分析平台_V1.0\\app.py',
      url: 'http://127.0.0.1:8001/',
      timeout: 120_000,
      reuseExistingServer: true,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 4173',
      cwd: 'C:\\Users\\acer\\Desktop\\编程开发\\软著开发\\双变量关联挖掘与非参数统计分析平台_V1.0\\frontend',
      url: 'http://127.0.0.1:4173/',
      timeout: 120_000,
      reuseExistingServer: true,
    },
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
