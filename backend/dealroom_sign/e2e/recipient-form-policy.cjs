/* Real iPhone Chromium requests to disposable HTTPS Django; native Sign is stubbed. */
const assert = require('node:assert/strict');
const {chromium, devices} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const origin = new URL(process.env.RECIPIENT_ENTRY_URL).origin;
  const browser = await chromium.launch({headless: true,
    args: ['--no-sandbox', '--no-proxy-server', '--host-resolver-rules=MAP recipient.test 127.0.0.1']});
  try {
    const context = await browser.newContext({...devices['iPhone 13'], ignoreHTTPSErrors: true});
    const observed = [];
    const page = await context.newPage();
    page.on('response', response => {
      const request = response.request(), headers = request.headers();
      observed.push({path: new URL(request.url()).pathname, method: request.method(),
        origin: headers.origin, referer: headers.referer, status: response.status()});
    });
    await page.goto(process.env.RECIPIENT_ENTRY_URL);
    await page.getByRole('button', {name: 'Continue', exact: true}).click();
    await page.waitForURL('**/s/session/context');
    await page.getByRole('heading', {name: 'Harbor Light Mutual NDA', exact: true}).waitFor();
    if (process.env.RECIPIENT_SCREENSHOT) {
      await page.screenshot({path: process.env.RECIPIENT_SCREENSHOT, fullPage: true});
    }
    await page.getByRole('checkbox').check();
    await page.getByRole('button', {name: 'Review and sign', exact: true}).click();
    const entry = observed.find(row => row.path.endsWith('/enter') && row.method === 'POST');
    const consent = observed.find(row => row.path === '/s/session/consent' && row.method === 'POST');
    console.log(JSON.stringify({entry: {...entry, path: '/s/[personal-capability]/enter',
      referer: entry.referer ? origin + '/s/[personal-capability]' : undefined}, consent}, null, 2));
    assert.equal(entry.status, 200);
    assert.equal(consent.status, 303);
    assert.equal(consent.origin, origin);
    assert.equal(consent.referer, origin + '/s/session/context');
    await page.getByRole('heading', {name: 'Native signing fixture'}).waitFor();
    const assets = observed.filter(row => row.path.startsWith('/s/assets/'));
    assert(assets.some(row => row.path.endsWith('.css')));
    assert(assets.some(row => row.path.endsWith('.js')));
    assert(assets.every(row => row.status === 200), JSON.stringify(assets));
    console.log(JSON.stringify({assetRequests: assets.length, allAssetsOK: true, nativeFixtureReached: true}));
    await context.close();
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
