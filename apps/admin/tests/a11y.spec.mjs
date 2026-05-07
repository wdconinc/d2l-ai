import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('admin console fixture has no critical/serious axe violations', async ({ page }) => {
  const fixturePath = path.resolve(__dirname, '../fixtures/admin-console.html');
  const html = fs.readFileSync(fixturePath, 'utf8');

  await page.setContent(html);

  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();

  const blockingViolations = results.violations.filter((violation) =>
    ['critical', 'serious'].includes(violation.impact),
  );

  expect(blockingViolations).toEqual([]);
});
