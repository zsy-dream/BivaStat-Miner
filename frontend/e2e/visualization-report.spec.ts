import { test, expect, type APIRequestContext } from '@playwright/test';

const backendBase = 'http://127.0.0.1:8001';

async function prepareAnalysisState(request: APIRequestContext) {
  const loadResp = await request.post(`${backendBase}/api/data/load_sample_dataset`, {
    data: { dataset_type: 'retail', n_samples: 1500 },
  });
  expect(loadResp.ok()).toBeTruthy();

  const algoResp = await request.post(`${backendBase}/api/algorithm/run_algorithm`, {
    data: {
      algorithm_type: 'apriori',
      parameters: {
        min_support: 0.03,
        min_confidence: 0.4,
        min_lift: 1.0,
        max_len: 3,
        test_method: 'auto',
        p_value_threshold: 0.05,
        numeric_bins: 5,
        max_columns_for_mining: 20,
        max_unique_per_categorical: 30,
      },
    },
  });
  expect(algoResp.ok()).toBeTruthy();
  const algoJson = await algoResp.json();
  expect(algoJson.success).toBeTruthy();
  expect((algoJson.results?.association_rules ?? []).length).toBeGreaterThan(0);
}

async function waitForTaskCompleted(request: APIRequestContext, taskId: string, timeoutMs = 180_000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const resp = await request.get(`${backendBase}/api/algorithm/task_status/${taskId}`);
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    const status = body.task?.status;
    if (status === 'completed') return body.task;
    if (status === 'failed' || status === 'cancelled' || status === 'stopped') {
      throw new Error(`Task ${taskId} ended unexpectedly with status: ${status}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  throw new Error(`Task ${taskId} did not complete within ${timeoutMs}ms`);
}

test.describe('Visualization and report flows', () => {
  test('renders a visualization chart and downloads a report', async ({ page, request }) => {
    await prepareAnalysisState(request);

    const chartResponsePromise = page.waitForResponse((response) =>
      response.url().includes('/api/visualization/create_chart') && response.request().method() === 'POST'
    );
    await page.goto('/visualization?preset=correlation_overview&auto=1');
    const chartResponse = await chartResponsePromise;
    expect(chartResponse.ok()).toBeTruthy();

    const chartFrame = page.locator('iframe[title]');
    await expect(chartFrame).toBeVisible();
    await expect(page.getByTitle('下载 HTML 图表')).toBeEnabled();

    await page.goto('/report');
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: /生成并下载报告/ }).click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toContain('.html');
    await expect(page.getByText(/文件流已装卸到您的本地磁盘/)).toBeVisible();
  });

  test('completes the core UI journey from data management to analysis, visualization, and report', async ({ page, request }) => {
    const loadResp = await request.post(`${backendBase}/api/data/load_sample_dataset`, {
      data: { dataset_type: 'retail', n_samples: 1500 },
    });
    expect(loadResp.ok()).toBeTruthy();
    await page.goto('/data');
    await expect(page.getByText(/当前激活数据集:/)).toBeVisible({ timeout: 30_000 });

    await page.goto('/algorithm');
    await expect(page.getByRole('button', { name: '开始分析' })).toBeVisible();
    await page.getByRole('button', { name: '开始分析' }).click();

    await page.waitForURL(/\/analysis_result\?task_id=/, { timeout: 30_000 });
    const resultUrl = page.url();
    const taskId = new URL(resultUrl).searchParams.get('task_id');
    expect(taskId).toBeTruthy();
    await waitForTaskCompleted(request, taskId!);
    await page.goto(resultUrl);
    await expect(page.getByRole('heading', { name: '分析结果' })).toBeVisible({ timeout: 120_000 });

    const chartResponsePromise = page.waitForResponse((response) =>
      response.url().includes('/api/visualization/create_chart') && response.request().method() === 'POST'
    );
    await page.getByRole('button', { name: /规则网络/ }).click();
    await page.waitForURL(/\/visualization\?preset=rule_network&auto=1/, { timeout: 20_000 });
    const chartResponse = await chartResponsePromise;
    expect(chartResponse.ok()).toBeTruthy();
    await expect(page.locator('iframe[title]')).toBeVisible({ timeout: 20_000 });

    await page.goto(resultUrl);
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: /生成分析报告/ }).click();
    await page.waitForURL(/\/report/, { timeout: 20_000 });
    await page.getByRole('button', { name: /生成并下载报告/ }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('.html');
    await expect(page.getByText(/文件流已装卸到您的本地磁盘/)).toBeVisible();
  });
});
