# Accessibility (WCAG 2.1 AA) for UI Changes

This project targets **WCAG 2.1 AA** for all instructor-facing UI in `apps/web` and `apps/admin`.

## Automated checks (axe-core in CI)

Accessibility checks run in GitHub Actions via `.github/workflows/a11y-ci.yml`.

Local run:

```bash
npm ci
npx playwright install --with-deps chromium
npm run test:a11y
```

These tests fail CI if **critical** or **serious** axe violations are found.

## Manual keyboard-only checklist

For UI PRs, verify at minimum:

- [ ] Tab order follows visible reading order.
- [ ] Every interactive control is reachable by keyboard alone.
- [ ] Focus indicators are visible and high contrast.
- [ ] Use-case picker can be opened, changed, and submitted with keyboard only.
- [ ] Preview flow can be started and reviewed without mouse interaction.
- [ ] Dialogs (if present) trap focus and restore focus on close.

## Screen-reader smoke-test checklist

Test with VoiceOver, NVDA, or JAWS:

- [ ] Exactly one `<h1>` per page and headings are hierarchical.
- [ ] Form controls have accessible labels.
- [ ] Landmarks (`header`, `nav`, `main`) are present and meaningful.
- [ ] Status/preview updates are announced via appropriate live regions.
- [ ] No hidden LTI claims, OAuth tokens, or sensitive values appear in accessible names/descriptions.

## Colour contrast checks

- [ ] Body text contrast ratio is at least **4.5:1**.
- [ ] Large text (18pt+ or 14pt bold+) is at least **3:1**.
- [ ] UI controls/icons and focus outlines are at least **3:1** against adjacent colors.
- [ ] Information is not conveyed by color alone.

## PR expectation for UI changes

If your PR touches `apps/web` or `apps/admin` UI:

1. Run `npm run test:a11y` locally.
2. Complete the manual keyboard and screen-reader smoke checks above.
3. Note any exceptions and mitigation in the PR description.
