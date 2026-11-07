import { render, screen, fireEvent, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { test, expect, vi } from 'vitest';
import ApprovalsPage, { requestTitle, approvalState } from '../../pages/dealroom/ApprovalsPage';
import { AddOrganisationDialog, domainCheck } from '../../pages/dealroom/dialogs';

const future = new Date(Date.now() + 3 * 864e5).toISOString();
vi.mock('../../services/api', () => ({
  default: {
    get: vi.fn(async (path) => ({
      data: path.includes('approvals')
        ? [{ id: 'a', status: 'pending_approval', operation_id: 'restore grant', method: 'PATCH', path: '/grants/jane/', current_state: { revoked_at: '2026-01-01' }, payload: { revoked_at: null }, created_at: new Date().toISOString(), expires_at: future }]
        : [],
    })),
    post: vi.fn(),
  },
}));

test('approval keeps target and current versus proposed state, behind a Details disclosure', async () => {
  render(<MemoryRouter><ApprovalsPage /></MemoryRouter>);
  expect(await screen.findByText('Restore grant')).toBeInTheDocument();
  expect(screen.getByText('Pending')).toBeInTheDocument();
  expect(screen.getByText('Details')).toBeInTheDocument();
  expect(screen.getByText('Target: PATCH /grants/jane/')).toBeInTheDocument();
  expect(screen.getByText(/2026-01-01/)).toBeInTheDocument();
  expect(screen.getByText(/"revoked_at": null/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument();
});

test('request titles and states are plain words', () => {
  expect(requestTitle({ operation_id: 'dealroom_sign_SigningEnvelopeViewSet_create_post' })).toBe('Send for signature');
  expect(requestTitle({ operation_id: 'dealroom_GrantViewSet_partial_update_patch' })).toBe('Change grant');
  expect(approvalState({ status: 'pending_approval', expires_at: '2020-01-01T00:00:00Z' })[1]).toBe('Expired');
  expect(approvalState({ status: 'rejected' })[0]).toBe('danger');
});

test('international domains need an explicit confirmation of their A-label; ASCII domains do not', () => {
  expect(domainCheck('bücher.test')).toMatchObject({ international: true, alabel: 'xn--bcher-kva.test' });
  expect(domainCheck('acme.test')).toMatchObject({ international: false, valid: true });
  render(<AddOrganisationDialog open onOpenChange={() => {}} />);
  const dialog = screen.getByRole('dialog');
  fireEvent.change(within(dialog).getByLabelText('Organisation name'), { target: { value: 'Bücher' } });
  fireEvent.change(within(dialog).getByLabelText('Email domain'), { target: { value: 'bücher.test' } });
  expect(within(dialog).getByText('xn--bcher-kva.test')).toBeInTheDocument();
  const submit = within(dialog).getByRole('button', { name: 'Add organisation' });
  expect(submit).toBeDisabled();
  fireEvent.click(within(dialog).getByRole('checkbox'));
  expect(submit).not.toBeDisabled();
  fireEvent.change(within(dialog).getByLabelText('Email domain'), { target: { value: 'acme.test' } });
  expect(within(dialog).queryByRole('checkbox')).toBeNull();
  expect(submit).not.toBeDisabled();
});
