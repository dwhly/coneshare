import { render } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { ThemeToggle } from '../../../components/layout/FleetChrome';

// fds v0.10 (owner decision 2026-11-15): the Theme control is the package icon. theme.js draws sun / moon / sun-moon into
// an EMPTY [data-fds-theme-toggle] and sets title + aria-label; components.css sizes it (32px box, 44px tap area).
// Words inside the button, or a product rule that re-boxes it, bring back the old labelled box.
describe('ThemeToggle', () => {
  it('renders an empty package toggle with an accessible name before theme.js runs', () => {
    const { container } = render(<ThemeToggle />);
    const button = container.querySelector('button[data-fds-theme-toggle]');
    expect(button).not.toBeNull();
    expect(button.textContent).toBe('');
    expect(button.getAttribute('aria-label')).toBe('Theme');
    expect(button.getAttribute('title')).toBe('Theme');
    expect(button.getAttribute('type')).toBe('button');
  });

  it('has no product CSS that re-boxes the toggle (the dealroom shell sheet and the app stylesheet)', () => {
    for (const rel of ['public/dealroom/shell.css', 'src/index.css']) {
      const css = readFileSync(resolve(__dirname, '../../../..', rel), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
      expect(css, rel).not.toMatch(/data-fds-theme-toggle/);
    }
  });
});
