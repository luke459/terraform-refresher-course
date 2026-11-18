import {expect, test} from '@playwright/test';

test('lab polling refreshes shared progress after grading and cleanup without reloading', async ({page}) => {
  const attemptId = 'progress-regression';
  let status = 'active';
  let pendingStatus: string | null = null;
  let runningReads = 0;
  let job: {id: string; operation: string; status: string; log: string} | null = null;
  const progressPercentages: number[] = [];
  const percentage = () => status === 'complete' ? 100 : status === 'apply_verified' ? 50 : 0;

  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/progress') {
      progressPercentages.push(percentage());
      await route.fulfill({json: {
        domains: [{domain_id: '01', attempts: [{id: attemptId, status, percentage: percentage()}],
          mastery: {mastered: false}, checkpoints: []}], exams: [],
      }});
    } else if (path === `/api/attempts/${attemptId}/terminal`) {
      const command = route.request().postDataJSON().command;
      pendingStatus = command === 'lab grade' ? 'apply_verified' : 'complete';
      runningReads = 1;
      job = {id: pendingStatus, operation: command === 'lab grade' ? 'validate-lab' : 'teardown-check', status: 'running', log: ''};
      await route.fulfill({json: {job}});
    } else if (path === `/api/attempts/${attemptId}`) {
      if (pendingStatus && runningReads-- === 0) {
        status = pendingStatus;
        pendingStatus = null;
        if (job) job.status = 'succeeded';
      }
      await route.fulfill({json: {id: attemptId, domain_id: '01', status, percentage: percentage(),
        account: '123456789012', region: 'us-east-1', workspace: '/workspaces/progress-regression',
        verified_hash: status === 'apply_verified' || status === 'complete' ? 'verified-config' : null,
        jobs: job ? [job] : [], results: [], resources: [],
      }});
    } else if (path === `/api/attempts/${attemptId}/files`) {
      await route.fulfill({json: [{path: 'main.tf', content: '# Editable starter\n'}]});
    } else if (path.startsWith('/api/jobs/') && path.endsWith('/events')) {
      await route.fulfill({contentType: 'text/event-stream', body: `data: ${JSON.stringify(job)}\n\n`});
    } else {
      await route.continue();
    }
  });

  await page.goto('/lab/01');
  await expect(page.getByText('Not yet graded', {exact: true})).toBeVisible();
  await expect(page.locator('.nav-label')).toContainText('0/8');
  await page.getByRole('textbox', {name: 'Terminal command', exact: true}).fill('lab grade');
  await page.getByRole('textbox', {name: 'Terminal command', exact: true}).press('Enter');
  await expect(page.getByText('50% apply verified', {exact: true})).toBeVisible();
  await expect.poll(() => progressPercentages.includes(50)).toBeTruthy();
  await expect(page.locator('.nav-label')).toContainText('0/8');

  await page.getByRole('textbox', {name: 'Terminal command', exact: true}).fill('lab check-cleanup');
  await page.getByRole('textbox', {name: 'Terminal command', exact: true}).press('Enter');
  await expect(page.getByText('100% complete', {exact: true})).toBeVisible();
  await expect(page.locator('.nav-label')).toContainText('1/8');
  await expect.poll(() => progressPercentages.includes(100)).toBeTruthy();
  await page.getByRole('link', {name: 'Overview', exact: true}).click();
  await expect(page.locator('.domain-card[href="/domain/01"] .badge')).toHaveText('Complete');
  await expect(page.getByRole('link', {name: /Continue learning/})).toHaveAttribute('href', '/domain/02');
});
