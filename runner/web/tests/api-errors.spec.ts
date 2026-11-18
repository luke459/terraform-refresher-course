import {expect, test} from '@playwright/test';

for (const response of [
  {status: 500, contentType: 'text/plain', body: 'Internal Server Error: private-detail-canary', expected: 'HTTP 500'},
  {status: 502, contentType: 'text/html', body: '<html>private-detail-canary</html>', expected: 'HTTP 502'},
  {status: 200, contentType: 'application/json', body: 'not-json-private-detail-canary', expected: 'unreadable response'},
  {status: 409, contentType: 'application/json', body: JSON.stringify({detail: 'Sign in to AWS SSO again, then reconnect.'}), expected: 'Sign in to AWS SSO again'},
]) {
  test(`starting a lab handles ${response.status} ${response.contentType} responses clearly`, async ({page}) => {
    await page.route('**/api/connection', route => route.fulfill({json: {
      connected: true, account: '123456789012', region: 'eu-west-1', mode: 'profile', profile: 'course-sandbox',
    }}));
    await page.route('**/api/progress', route => route.fulfill({json: {domains: [], exams: []}}));
    const {expected, ...payload} = response;
    await page.route('**/api/attempts', route => route.fulfill(payload));
    await page.goto('/lab/02');
    await page.getByRole('button', {name: 'Start lab attempt', exact: true}).click();
    await expect(page.getByRole('alert')).toContainText(expected);
    await expect(page.getByRole('alert')).not.toContainText('JSON.parse');
    await expect(page.getByRole('alert')).not.toContainText('private-detail-canary');
    await expect(page.getByRole('button', {name: 'Start lab attempt', exact: true})).toBeEnabled();
  });
}
