import {expect, test} from '@playwright/test';
import type {Page} from '@playwright/test';

async function labFixture(page: Page) {
  const id = 'workspace-demo';
  const files = [{path: 'main.tf', content: '# Fix the starter\n'}, {path: 'variables.tf', content: '# Lab inputs\n'}];
  const jobs: any[] = [];
  let status = 'active', hash = 'initial', verified: string | null = null, applied = false;
  let pending: any = null, reads = 0, saves = 0, hold = false;
  const canceled: string[] = [];
  const submitted: string[] = [];
  const finish = () => {
    if (!pending) return;
    pending.status = 'succeeded';
    if (pending.operation === 'apply') {applied = true; status = 'active'; verified = null;}
    if (pending.operation === 'validate-lab') {status = 'apply_verified'; verified = hash;}
    if (pending.operation === 'destroy') status = 'cleanup_pending';
    if (pending.operation === 'teardown-check') status = 'complete';
    pending = null;
  };
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    const percentage = status === 'complete' ? 100 : verified ? 50 : 0;
    if (path === '/api/progress') {
      await route.fulfill({json: {domains: [{domain_id: '01', attempts: [{id, status, percentage}], mastery: {mastered: false}, checkpoints: []}], exams: []}});
    } else if (path === '/api/connection') {
      await route.fulfill({json: {connected: true, account: '123456789012', region: 'us-east-1', mode: 'profile', profile: 'course-sandbox'}});
    } else if (path === `/api/attempts/${id}/files`) {
      if (route.request().method() === 'PUT') {
        const input = route.request().postDataJSON();
        files.find(file => file.path === input.path)!.content = input.content;
        hash = `saved-${++saves}`; verified = null; status = 'active';
        await route.fulfill({json: {saved: true}});
      } else await route.fulfill({json: files});
    } else if (path === `/api/attempts/${id}`) {
      if (pending && reads-- === 0) finish();
      await route.fulfill({json: {id, domain_id: '01', status, percentage: status === 'complete' ? 100 : verified ? 50 : 0,
        account: '123456789012', region: 'us-east-1', workspace: '/workspaces/workspace-demo',
        current_hash: hash, verified_hash: verified, jobs, results: [], resources: []}});
    } else if (path === `/api/attempts/${id}/terminal`) {
      const input = route.request().postDataJSON();
      if (input.command === 'help') {await route.fulfill({json: {message: 'Terraform commands: terraform init, terraform plan -out=tfplan. Lab tools: lab grade, lab check-cleanup.'}}); return;}
      if (input.command === 'terraform destroy' && !input.confirmed) {await route.fulfill({json: {confirmation_required: true, message: 'Type yes to destroy the lab resources, or no to cancel.'}}); return;}
      const words = input.command.split(' ');
      const operation = words[0] === 'lab' ? words[1] === 'grade' ? 'validate-lab' : 'teardown-check' : words[1];
      submitted.push(operation);
      pending = {id: String(jobs.length + 1), operation, status: 'running', config_hash: hash,
        params: {terminal_command: input.command, terminal_args: words.slice(1), save_plan: input.command.includes('-out=tfplan'), detailed_exitcode: input.command.includes('-detailed-exitcode')},
        created: Date.now() / 1000, exit_code: operation === 'plan' && !applied && input.command.includes('-detailed-exitcode') ? 2 : 0,
        log: `Terraform ${operation}: sample output`};
      jobs.unshift(pending); reads = hold ? 100 : 1; hold = false;
      await route.fulfill({json: {job: pending}});
    } else if (path.startsWith('/api/jobs/') && path.endsWith('/events')) {
      const job = jobs.find(job => path.includes('/' + job.id + '/'));
      await route.fulfill({contentType: 'text/event-stream', body: `data: ${JSON.stringify(job)}\n\n`});
    } else if (path.startsWith('/api/jobs/') && path.endsWith('/cancel')) {
      const job = jobs.find(job => path.includes('/' + job.id + '/'));
      job.status = 'canceled'; pending = null; canceled.push(job.id);
      await route.fulfill({json: {cancel_requested: true}});
    } else await route.continue();
  });
  return {files, submitted, jobs, canceled, holdNext: () => {hold = true;}};
}

async function typeCommand(page: Page, command: string) {
  const input = page.getByRole('textbox', {name: 'Terminal command', exact: true});
  await input.fill(command); await input.press('Enter');
}

test('challenge, editable files and actions stay together; file switches preserve drafts', async ({page}, testInfo) => {
  const fixture = await labFixture(page);
  await page.goto('/lab/01');
  await expect(page.getByRole('heading', {name: 'The challenge', exact: true})).toBeVisible();
  await expect(page.getByRole('heading', {name: 'Workspace editor', exact: true})).toBeVisible();
  await expect(page.getByRole('region', {name: 'Lab terminal', exact: true})).toBeVisible();
  const challenge = await page.locator('.lab-challenge').boundingBox();
  const editor = await page.locator('.lab-editor').boundingBox();
  const actions = await page.locator('.lab-output').boundingBox();
  expect(challenge!.x + challenge!.width).toBeLessThanOrEqual(editor!.x);
  expect(editor!.x + editor!.width).toBeLessThanOrEqual(actions!.x);
  await page.getByLabel('Edit main.tf').fill('# My repaired configuration\n');
  await page.getByLabel('Workspace file', {exact: true}).selectOption('variables.tf');
  await page.getByLabel('Edit variables.tf').fill('# My input changes\n');
  await page.getByLabel('Workspace file', {exact: true}).selectOption('main.tf');
  await expect(page.getByLabel('Edit main.tf')).toHaveValue('# My repaired configuration\n');
  await typeCommand(page, 'terraform plan -out=tfplan');
  await expect(page.getByLabel('Terminal output')).toContainText('Save your edited files first');
  expect(fixture.submitted).toHaveLength(0);
  await expect(page.getByRole('status').filter({hasText: 'Next: save your changes'})).toContainText('2 unsaved files');
  await page.getByRole('button', {name: 'Save changes', exact: true}).click();
  await expect(page.getByText('All changes saved', {exact: true})).toBeVisible();
  expect(fixture.files.map(file => file.content)).toEqual(['# My repaired configuration\n', '# My input changes\n']);
  await typeCommand(page, 'terraform plan -detailed-exitcode -out=tfplan');
  await expect(page.getByLabel('Terminal output').getByText('Terraform plan: sample output')).toBeVisible();
  await expect(page.getByRole('heading', {name: 'The challenge', exact: true})).toBeVisible();
  await expect(page.getByLabel('Edit main.tf')).toHaveValue('# My repaired configuration\n');
  await page.getByRole('button', {name: 'Compare reference solution', exact: true}).click();
  await expect(page.getByRole('button', {name: 'Hide reference solution', exact: true})).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByLabel('Edit main.tf')).toBeVisible();
  await page.getByRole('button', {name: 'Hide reference solution', exact: true}).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({path: testInfo.outputPath('lab-desktop.png'), fullPage: true});
});

test('progress explains each next action through grading, cleanup and reload', async ({page}) => {
  const fixture = await labFixture(page);
  await page.goto('/lab/01');
  await expect(page.getByText('0 of 4 stages complete', {exact: true})).toBeVisible();
  for (const command of ['terraform init', 'terraform fmt', 'terraform validate', 'terraform plan -detailed-exitcode -out=tfplan', 'terraform apply tfplan', 'terraform plan -detailed-exitcode -out=tfplan']) {
    const before = fixture.submitted.length;
    await typeCommand(page, command);
    await expect.poll(() => fixture.submitted.length).toBe(before + 1);
    await expect.poll(() => fixture.jobs[0].status).toBe('succeeded');
    await expect(page.locator('.terminal-exit').last()).toContainText('succeeded');
  }
  await expect(page.getByText('2 of 4 stages complete', {exact: true})).toBeVisible();
  await expect(page.getByRole('status').filter({hasText: 'Next:'})).toContainText('Next: Grade lab');
  await typeCommand(page, 'lab grade');
  await expect(page.getByText('50% apply verified', {exact: true})).toBeVisible();
  await expect(page.getByText('3 of 4 stages complete', {exact: true})).toBeVisible();
  await expect(page.getByRole('status').filter({hasText: 'Next:'})).toContainText('Next: Destroy lab resources');
  await typeCommand(page, 'terraform destroy');
  await expect(page.getByLabel('Terminal output')).toContainText('Type yes');
  await typeCommand(page, 'yes');
  await expect(page.getByRole('status').filter({hasText: 'Next:'})).toContainText('Next: Verify cleanup');
  await typeCommand(page, 'lab check-cleanup');
  await expect(page.getByText('100% complete', {exact: true})).toBeVisible();
  await expect(page.getByText('4 of 4 stages complete', {exact: true})).toBeVisible();
  await expect(page.locator('.nav-label')).toContainText('1/8');
  await expect(page.getByLabel('Edit main.tf')).toBeDisabled();
  await page.reload();
  await expect(page.getByText('100% complete', {exact: true})).toBeVisible();
  await expect(page.getByRole('link', {name: 'Continue to next domain', exact: false})).toHaveAttribute('href', '/domain/02');
});

test('mobile workspace has no hidden lab tabs or horizontal overflow', async ({page}, testInfo) => {
  await page.setViewportSize({width: 390, height: 844});
  await labFixture(page);
  await page.goto('/lab/01');
  await expect(page.getByLabel('Edit main.tf')).toBeVisible();
  for (const selector of ['.lab-challenge', '.lab-editor', '.lab-output']) {
    await page.locator(selector).scrollIntoViewIfNeeded();
    await expect(page.locator(selector)).toBeVisible();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await expect(page.getByRole('button', {name: 'Commands & results', exact: true})).toHaveCount(0);
  await expect(page.getByRole('navigation', {name: 'Workspace sections'})).toBeVisible();
  await page.getByRole('navigation', {name: 'Workspace sections'}).getByRole('link', {name: 'Editor', exact: true}).click();
  await expect(page).toHaveURL(/#editor-title$/);
  await expect(page.getByRole('heading', {name: 'Workspace editor', exact: true})).toBeInViewport();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({path: testInfo.outputPath('lab-mobile.png'), fullPage: true});
});

test('failed operations remain inspectable and saved edits invalidate completed configuration steps', async ({page}) => {
  const fixture = await labFixture(page);
  await page.goto('/lab/01');
  await typeCommand(page, 'terraform validate');
  await expect(page.getByText('1 of 4 stages complete', {exact: true})).toBeVisible();
  await typeCommand(page, 'terraform plan -detailed-exitcode -out=tfplan');
  await expect.poll(() => fixture.submitted.length).toBe(2);
  await expect.poll(() => fixture.jobs[0].status).toBe('succeeded');
  await expect(page.locator('.terminal-exit').last()).toContainText('succeeded');
  fixture.jobs[0].status = 'failed';
  fixture.jobs[0].log = 'Error: Invalid resource configuration';
  await expect(page.locator('.terminal-exit').last()).toContainText('failed');
  await expect(page.getByLabel('Terminal output')).toContainText('Error: Invalid resource configuration');
  await expect(page.getByLabel('Terminal output')).toContainText('Terraform validate: sample output');
  await page.getByLabel('Edit main.tf').fill('# Fix the configuration error\n');
  await page.getByRole('button', {name: 'Save changes', exact: true}).click();
  await expect(page.getByText('0 of 4 stages complete', {exact: true})).toBeVisible();
  await expect(page.getByRole('textbox', {name: 'Terminal command', exact: true})).toBeEditable();
});


test('terminal has history, clear, cancellation, and interactive destroy confirmation', async ({page}) => {
  const fixture = await labFixture(page);
  await page.goto('/lab/01');
  const input = page.getByRole('textbox', {name: 'Terminal command', exact: true});
  await typeCommand(page, 'help');
  await expect(page.getByLabel('Terminal output')).toContainText('Terraform commands');
  await typeCommand(page, 'terraform validate');
  await expect.poll(() => fixture.jobs[0]?.status).toBe('succeeded');
  await input.press('ArrowUp');
  await expect(input).toHaveValue('terraform validate');
  await input.press('ArrowDown');
  await expect(input).toHaveValue('');
  await input.press('Control+l');
  await expect(page.getByLabel('Terminal output')).not.toContainText('sample output');
  await input.press('ArrowUp');
  await expect(input).toHaveValue('terraform validate');
  fixture.holdNext();
  await typeCommand(page, 'terraform plan -out=tfplan');
  await expect(page.getByLabel('Terminal output')).toContainText('Terraform plan: sample output');
  await input.press('Control+c');
  await expect.poll(() => fixture.canceled.length).toBe(1);
  await expect(page.locator('.terminal-exit').last()).toContainText('canceled');
  const before = fixture.submitted.length;
  await typeCommand(page, 'terraform destroy');
  await expect(input).toHaveAttribute('placeholder', 'Type yes or no');
  await typeCommand(page, 'no');
  expect(fixture.submitted.length).toBe(before);
  await expect(page.getByLabel('Terminal output')).toContainText('Canceled. No command was run.');
});
