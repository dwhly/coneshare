// The Django glue pages' styled select (public/dealroom/shell.js drSelect) must expose its value and the keyboard-active
// option to assistive technology (review r1 [3]): select-only combobox + listbox (WAI-ARIA APG).
import fs from 'node:fs';
import path from 'node:path';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

const SHELL = path.resolve(__dirname, '../../../../public/dealroom/shell.js');

describe('glue drSelect (shell.js)', () => {
  let sel, trigger, list, onChange;
  const key = (k) => trigger.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }));
  const option = (i) => list.querySelectorAll('[role="option"]')[i];

  beforeAll(() => {
    // eslint-disable-next-line no-new-func
    new Function(fs.readFileSync(SHELL, 'utf8'))();
  });
  beforeEach(() => {
    document.body.innerHTML = '<div id="c" data-id="version"></div>';
    onChange = vi.fn();
    sel = window.drShell.drSelect(document.getElementById('c'), { label: 'Document', onChange });
    sel.set([{ value: 'a', label: 'NDA v1' }, { value: 'b', label: 'NDA v2' }, { value: 'c', label: 'SPA' }], 'a');
    trigger = sel.trigger;
    list = document.querySelector('[role="listbox"]');
    trigger.focus();
  });

  it('is a labelled combobox that controls its listbox and shows its value', () => {
    expect(trigger.getAttribute('role')).toBe('combobox');
    expect(trigger.getAttribute('aria-label')).toBe('Document');
    expect(trigger.getAttribute('aria-haspopup')).toBe('listbox');
    expect(trigger.getAttribute('aria-controls')).toBe(list.id);
    expect(list.id).toBeTruthy();
    expect(trigger.textContent).toBe('NDA v1');
    expect(trigger.hasAttribute('aria-activedescendant')).toBe(false);
  });

  it('ArrowDown opens on the current value, then moves the active option for AT (aria-activedescendant + aria-selected)', () => {
    key('ArrowDown');
    expect(trigger.getAttribute('aria-expanded')).toBe('true');
    expect(list.hidden).toBe(false);
    expect(trigger.getAttribute('aria-activedescendant')).toBe(option(0).id);
    key('ArrowDown');
    expect(document.activeElement).toBe(trigger); // DOM focus stays on the combobox; the active option is referenced
    expect(trigger.getAttribute('aria-activedescendant')).toBe(option(1).id);
    expect(option(1).getAttribute('aria-selected')).toBe('true');
    expect(option(0).getAttribute('aria-selected')).toBe('false');
    expect(onChange).not.toHaveBeenCalled();
    key('End');
    expect(trigger.getAttribute('aria-activedescendant')).toBe(option(2).id);
    key('Home');
    expect(trigger.getAttribute('aria-activedescendant')).toBe(option(0).id);
    key('ArrowDown');
    key('Enter');
    expect(onChange).toHaveBeenCalledWith('b');
    expect(sel.value).toBe('b');
    expect(trigger.textContent).toBe('NDA v2');
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
    expect(trigger.hasAttribute('aria-activedescendant')).toBe(false);
  });

  it('Escape closes without changing the value and restores the selected state', () => {
    key('ArrowDown');
    key('ArrowDown');
    key('Escape');
    expect(list.hidden).toBe(true);
    expect(sel.value).toBe('a');
    expect(onChange).not.toHaveBeenCalled();
    expect(option(0).getAttribute('aria-selected')).toBe('true');
    expect(option(1).getAttribute('aria-selected')).toBe('false');
    expect(trigger.hasAttribute('aria-activedescendant')).toBe(false);
  });
});
