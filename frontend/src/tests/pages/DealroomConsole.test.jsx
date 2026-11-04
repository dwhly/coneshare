import { render, screen, fireEvent } from '@testing-library/react';
import { test, expect, vi } from 'vitest';
import DealroomConsole from '../../pages/DealroomConsole';
vi.mock('../../services/api', () => ({default: {get: vi.fn(async path => ({data: path.includes('approvals') ? [{id:'a', status:'pending_approval', operation_id:'restore grant', method:'PATCH', path:'/grants/jane/', current_state:{revoked_at:'2026-01-01'}, payload:{revoked_at:null}}] : []})), post:vi.fn()}}));
vi.mock('../../lib/layoutMode', () => ({hydrateLayoutMode:vi.fn()}));
test('r2 06 approval identifies target and current versus proposed state and domain A-label', async () => {
  render(<DealroomConsole/>);
  expect(await screen.findByText('Target: PATCH /grants/jane/')).toBeInTheDocument();
  expect(screen.getByText(/2026-01-01/)).toBeInTheDocument();
  expect(screen.getByText(/"revoked_at": null/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Organization domain'), {target:{value:'bücher.test'}});
  expect(screen.getByText(/Unicode: bücher.test · A-label: xn--bcher-kva.test/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.change(screen.getByLabelText('Organization domain'), {target:{value:'acme.test'}});
  expect(screen.getByRole('checkbox')).not.toBeChecked();
});
