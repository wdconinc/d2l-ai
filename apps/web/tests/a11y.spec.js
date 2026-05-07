const fs = require('node:fs');
const path = require('node:path');
const AxeBuilder = require('@axe-core/playwright').default;
const { test, expect } = require('@playwright/test');

test('web use-case picker and preview fixture has no critical/serious axe violations', async ({ page }) => {
  const fixturePath = path.resolve(__dirname, '../fixtures/use-case-preview.html');
  const html = fs.readFileSync(fixturePath, 'utf8');

  await page.setContent(html);

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();

  const blockingViolations = results.violations.filter((violation) =>
    ['critical', 'serious'].includes(violation.impact),
  );

  expect(blockingViolations).toEqual([]);
});
