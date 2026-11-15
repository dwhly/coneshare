// Run only against the fictional preview after the coordinated C1b deployment.
// Inputs live in a private JSON file: recipientUrl, nativeOrigin, credentialFile,
// envelopeId, recipientId, expectedIp, name, shots, mailpitOrigin, mailRecipient.
// No bearer, document content or personal URLs are written to stdout.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { sign } = require('./signature.cjs');
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const recipient = new URL(cfg.recipientUrl);
  assert.equal(recipient.port, '9445');
  assert.ok(recipient.pathname.startsWith('/s/'));
  const credential = fs.readFileSync(cfg.credentialFile, 'utf8').trim();
  const ua = 'Fleet-C1b-preview-audit/' + Date.now();
  const since = Date.now();
  const browser = await chromium.launch({headless: true});
  try {
    const context = await browser.newContext({userAgent: ua, extraHTTPHeaders: {
      'X-Forwarded-For': '192.0.2.9', 'X-Real-IP': '192.0.2.10',
      'X-Forwarded-Host': 'caller.test', 'X-Forwarded-Proto': 'http',
      'X-Fleet-Proxy-Key': 'caller-cannot-select-the-key',
    }});
    const page = await context.newPage();
    await page.goto(cfg.recipientUrl);
    await page.getByRole('button', {name: 'Continue', exact: true}).click();
    await page.getByRole('checkbox', {name: 'I agree to use electronic records and signatures for this document.'}).check();
    await page.getByRole('button', {name: 'Review and sign', exact: true}).click();
    await page.waitForURL('**/sign/**');
    await sign(page, cfg.name, cfg.shots);
    await page.waitForURL('**/s/return/**', {timeout: 60000});
    const audit = async () => {
      let rows = [];
      for (let p = 1; p <= 100; p++) {
        const response = await fetch(`${cfg.nativeOrigin}/api/v2/envelope/${encodeURIComponent(cfg.envelopeId)}/audit-log?page=${p}&perPage=100`, {
          headers: {Authorization: credential}, redirect: 'error',
        });
        assert.equal(response.status, 200);
        const body = await response.json(); rows.push(...body.data);
        if (rows.length >= body.count) return rows;
      }
      throw Error('Audit pagination did not finish');
    };
    let rows;
    for (let i = 0; i < 60; i++) {
      rows = await audit();
      if (rows.some(r => r.type === 'DOCUMENT_RECIPIENT_COMPLETED' && String(r.data?.recipientId) === String(cfg.recipientId))) break;
      await sleep(1000);
    }
    const completion = rows.find(r => r.type === 'DOCUMENT_RECIPIENT_COMPLETED' && String(r.data?.recipientId) === String(cfg.recipientId));
    assert.ok(completion, 'Native recipient-completed fact required');
    assert.equal(completion.ipAddress, cfg.expectedIp, 'Audit must contain browser tailnet IP, never supplied alternate IP/container IP');
    assert.equal(completion.userAgent, ua);
    assert.ok(!rows.some(r => r.type === 'EMAIL_SENT'), 'Native lifecycle mail is disabled');
    // Wait for local native jobs to settle, then inspect every delivery to this fictional recipient.
    await sleep(15000);
    rows = await audit();
    assert.ok(!rows.some(r => r.type === 'EMAIL_SENT'));
    const listing = await fetch(cfg.mailpitOrigin + '/api/v1/search?query=' + encodeURIComponent('to:' + cfg.mailRecipient)).then(r => r.json());
    const messages = [];
    for (const row of listing.messages || []) {
      if (Date.parse(row.Created) < since - 600000) continue;
      const message = await fetch(cfg.mailpitOrigin + '/api/v1/message/' + row.ID).then(r => r.json());
      messages.push(message);
      assert.match(message.From.Name, / via Fleet Dealroom$/);
      assert.ok(!/amforge|documenso|sslip\.io/i.test(JSON.stringify(message)));
    }
    assert.ok(messages.some(m => /sent you .* to sign/.test(m.Subject)), 'Send invitation required');
    assert.ok(messages.some(m => /fully signed/.test(m.Subject)), 'Send final email required (use a one-signer fixture)');
    const proof = {auditEventId: completion.id, ipMatches: true, userAgentMatches: true,
      nativeMailCount: 0, mailpitMessageIds: messages.map(m => m.ID)};
    fs.writeFileSync(cfg.shots + '/c1b-audit.json', JSON.stringify(proof, null, 2));
    console.log('PASS recipient audit IP/UA, header overwrite, native-mail negatives and Send mail presence');
  } finally { await browser.close(); }
})().catch(error => { console.error('FAIL C1b preview acceptance:', error.name); process.exitCode = 1; });
