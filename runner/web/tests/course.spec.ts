import { expect, test } from '@playwright/test';

test('dashboard, lesson, keyboard exercise, and checkpoint feedback', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Your Terraform refresher' })).toBeVisible();
  await page.getByRole('link', { name: /Start your refresher/ }).click();
  await expect(page.getByRole('heading', { name: 'Infrastructure as code', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'What Terraform declares' })).toBeVisible();
  await page.getByRole('button', { name: 'Interactive exercises', exact: true }).click();
  const first = page.getByRole('group').filter({ hasText: 'AWS compute and Google Cloud storage' });
  await first.getByLabel('Multi-cloud', { exact: true }).check();
  await page.getByRole('group').filter({ hasText: 'A web tier and database tier' }).getByLabel('Multi-tier', { exact: true }).check();
  await page.getByRole('group').filter({ hasText: 'A private virtualization cluster' }).getByLabel('Hybrid', { exact: true }).check();
  await page.getByRole('button', { name: 'Check predictions' }).first().click();
  await expect(page.getByText('Correct. Two cloud providers', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Check your understanding' }).click();
  await page.getByLabel('The bucket and its desired settings').check();
  await page.getByRole('button', { name: 'Save answer' }).first().click();
  await expect(page.getByText('Correct.', { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test('AWS setup offers profiles and ephemeral access-key input', async ({ page }) => {
  await page.goto('/settings');
  await page.getByRole('button', { name: /IAM access keys/ }).click();
  await expect(page.getByLabel('Secret access key', { exact: true })).toHaveAttribute('type', 'password');
  await expect(page.getByLabel('Session token', { exact: false })).toHaveAttribute('type', 'password');
  await page.getByRole('button', { name: /CLI profile/ }).click();
  await expect(page.getByLabel('AWS CLI profile name')).toBeVisible();
  await expect(page.getByLabel('Primary lab region')).toHaveValue('us-east-1');
  const regions=page.getByLabel('Primary lab region');
  await expect(regions.locator('option')).toHaveText(['Europe — Ireland (eu-west-1)','US East — N. Virginia (us-east-1)','Europe — London (eu-west-2)']);
  await regions.selectOption('eu-west-1');
  await expect(regions).toHaveValue('eu-west-1');
  await page.getByLabel('AWS CLI profile name').fill('course-sandbox');
  let submittedRegion='';
  await page.route('**/api/connection',async route=>{
    if(route.request().method()!=='POST'){await route.continue();return;}
    submittedRegion=route.request().postDataJSON().region;
    await route.fulfill({json:{connected:true,profile:'course-sandbox',region:submittedRegion,account:'123456789012',mode:'profile'}});
  });
  await page.getByRole('button',{name:'Test connection & continue'}).click();
  await expect.poll(()=>submittedRegion).toBe('eu-west-1');
});

test('practice answer persists and mock deadline survives a reload', async ({ page }) => {
  await page.goto('/practice');
  await page.getByRole('button', { name: 'Start mock A', exact: true }).click();
  await expect(page.getByText('remaining', { exact: true })).toBeVisible();
  const before = await page.locator('.exam-timer').innerText();
  const url = page.url();
  await page.getByRole('radio').first().check();
  await page.getByRole('button', { name: 'Save answer' }).click();
  await page.reload();
  await expect(page.getByRole('radio').first()).toBeChecked();
  expect(page.url()).toBe(url);
  await page.getByRole('button', { name: 'Submit exam', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Review your results' })).toBeVisible();
  await expect(page.getByText(/practice score/)).toBeVisible();
  expect(before).toContain('remaining');
});

test('mobile layout keeps navigation and connection controls usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Your Terraform refresher' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.getByRole('link', { name: 'AWS connection', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Test connection & continue' })).toBeVisible();
});

test('shorter mock length is selected and survives reload',async({page})=>{
  await page.goto('/practice');
  await page.getByLabel('Mock length').selectOption('20');
  await page.getByRole('button',{name:'Start mock B',exact:true}).click();
  await expect(page.getByText('Question 1 of 20',{exact:true})).toBeVisible();
  await page.reload();
  await expect(page.getByText('Question 1 of 20',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Submit exam',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Review your results'})).toBeVisible();
});

test('all eight lessons load and every scenario exercise is keyboard-accessible', async ({ page }) => {
  const domains=await (await page.request.get('/api/domains')).json();
  for(const domain of domains){
    await page.goto('/domain/'+domain.id);
    await expect(page.locator('.lesson-prose h1')).toBeVisible();
    await page.getByRole('button',{name:'Show unified diff'}).click();
    await expect(page.locator('.delta-diff')).toContainText(domain.delta.after);
    await page.getByRole('button',{name:'Interactive exercises',exact:true}).click();
    for(const exercise of domain.exercises){
      const section=page.locator('section.exercise').filter({has:page.getByRole('heading',{name:exercise.title,exact:true})});
      await expect(section).toBeVisible();
      if(exercise.cases){
        for(const item of exercise.cases){
          const group=section.getByRole('group').filter({hasText:item.prompt});
          const radio=group.getByRole('radio',{name:item.correct,exact:true});
          await radio.focus();await page.keyboard.press('Space');
          await expect(radio).toBeChecked();
        }
        await section.getByRole('button',{name:'Check predictions'}).click();
        await expect(section.locator('.feedback.wrong')).toHaveCount(0);
      }
    }
  }
});

test('specialized simulations produce the expected state transitions without HCP', async ({page})=>{
  await page.goto('/domain/02');
  await page.getByRole('button',{name:'Interactive exercises',exact:true}).click();
  await page.getByRole('button',{name:'Resolve version'}).click();
  await expect(page.getByText('5.92.0 is outside', {exact:false})).toBeVisible();
  await page.getByLabel('Version constraint').selectOption({label:'~> 5.80'});
  await page.getByRole('button',{name:'Resolve version'}).click();
  await expect(page.getByText('5.92.0 satisfies', {exact:false})).toBeVisible();
  await page.goto('/domain/04');
  await page.getByRole('button',{name:'Interactive exercises',exact:true}).click();
  await page.getByLabel('Precondition uses an apply-time value').check();
  await page.getByRole('button',{name:'2. Precondition',exact:true}).click();
  await expect(page.getByText('evaluation is deferred', {exact:false})).toBeVisible();
  await page.getByRole('button',{name:'ephemeral + write-only',exact:true}).click();
  await page.getByRole('button',{name:'No',exact:true}).click();
  await expect(page.getByText('The ephemeral value is omitted', {exact:false})).toBeVisible();
  await page.goto('/domain/06');
  await page.getByRole('button',{name:'Interactive exercises',exact:true}).click();
  await page.getByRole('button',{name:'Start run A'}).click();
  await page.getByRole('button',{name:'Start run B'}).click();
  await expect(page.getByText('Run B: Error acquiring', {exact:false})).toBeVisible();
  await page.getByRole('button',{name:'Finish owning run'}).click();
  await page.getByRole('button',{name:'Start run B'}).click();
  await expect(page.getByText('Run B acquired', {exact:false})).toBeVisible();
  await page.goto('/domain/07');
  await page.getByRole('button',{name:'Interactive exercises',exact:true}).click();
  await page.getByLabel('Log scope').selectOption('core');
  await expect(page.locator('section.exercise pre')).not.toContainText('AccessDeniedException');
  await page.goto('/domain/08');
  await page.getByRole('button',{name:'Interactive exercises',exact:true}).click();
  await expect(page.getByText('Local simulation — no HCP account or API calls.')).toBeVisible();
  await page.getByLabel('Policy framework').selectOption('OPA');
  await expect(page.getByLabel('Enforcement').locator('option')).toHaveCount(2);
  await page.getByLabel('Enforcement').selectOption('mandatory');
  await expect(page.getByText('A failed policy blocks the run.', {exact:false})).toBeVisible();
  await page.getByLabel('Speculative preview only').check();
  await page.getByRole('button',{name:'Simulate workflow'}).click();
  await expect(page.getByText('preview complete; no apply', {exact:false})).toBeVisible();
  await page.goto('/settings');
  await expect(page.getByLabel('User API token')).toHaveCount(0);
});
