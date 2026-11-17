import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import DealroomRecipient from '../../pages/DealroomRecipient';
import RoomVisitor from '../../components/dealroom/RoomVisitor';

vi.mock('../../contexts/BrandingProvider', () => ({ useBranding: () => ({ brandName: 'Fictional Workspace', brandLogoUrl: '/brand.svg' }) }));
const answer = (data, ok = true) => ({ ok, json: async () => data });
let assign;
let statusReads;
function mount() { render(<MemoryRouter initialEntries={['/view/demo']}><Routes><Route path="/view/:slug" element={<DealroomRecipient />} /></Routes></MemoryRouter>); }
beforeEach(() => {
  localStorage.clear();
  window.history.replaceState({}, '', '/view/demo#personal=fictional');
  assign = vi.fn(); statusReads = 0;
  const original = window;
  vi.stubGlobal('window', new Proxy(original, { get(target, key) {
    if (key === 'location') return { origin: original.location.origin, pathname: original.location.pathname, hash: original.location.hash, search: original.location.search, assign };
    return Reflect.get(target, key);
  } }));
  vi.stubGlobal('fetch', vi.fn(async (url, options) => {
    if (url.endsWith('/challenge/')) return answer({ csrf_token: 'csrf', sender_name: 'Dan Whaley' });
    if (url.endsWith('/personal/')) return answer({ status: 'verified' });
    if (url.endsWith('/room/')) return answer({ code: 'nda_required', room_id: 'r' }, false);
    if (url.endsWith('/enter/')) return answer({ signing_url: 'https://signer.test/s/nda/one-time' });
    if (options?.method === 'POST') return answer({ state: 'queued' });
    statusReads += 1;
    return answer({ state: statusReads < 3 ? 'queued' : 'awaiting_signature', can_enter: statusReads >= 3, email_sent: false });
  }));
});
afterEach(() => vi.unstubAllGlobals());

test('Review the NDA creates the visitor request and waits for same-tab signing without email', async () => {
  mount();
  fireEvent.click(await screen.findByRole('button', { name: 'Review the NDA' }));
  await waitFor(() => expect(assign).toHaveBeenCalledWith('https://signer.test/s/nda/one-time'), { timeout: 5000 });
  expect(fetch.mock.calls.filter(([url, opts]) => url === '/api/v1/dealroom-sign/nda/r/' && opts?.method === 'POST')).toHaveLength(1);
  expect(screen.queryByText(/I’ve signed/)).not.toBeInTheDocument();
});

test('returning unsigned offers Continue signing and automatically checks server state', async () => {
  window.history.replaceState({}, '', '/view/demo');
  statusReads = 3;
  mount();
  fireEvent.click(await screen.findByRole('button', { name: 'Continue signing' }));
  await waitFor(() => expect(assign).toHaveBeenCalled());
  expect(screen.queryByText(/I’ve signed/)).not.toBeInTheDocument();
});

test('backup email copy is explicit after delivery, without claiming delivery before it', async () => {
  window.history.replaceState({}, '', '/view/demo');
  const original = fetch.getMockImplementation();
  fetch.mockImplementation((url, options) => url.endsWith('/nda/r/') && !options?.method
    ? Promise.resolve(answer({ state: 'awaiting_signature', can_enter: true, email_sent: true })) : original(url, options));
  mount();
  expect(await screen.findByText("We’ve also emailed you this link.")).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Continue signing' })).toBeInTheDocument();
});

test('room groups unfiled files, preserves sender order and suppresses spreadsheet page counts', () => {
  const room = { id: 'r', name: 'Fictional room', member: { name: 'Maya Chen', email: 'maya@northwind.test' }, nda_signed: true,
    folders: [{ id: 'f', name: 'Financials' }], start_here: ['m'], files: [
      { id: 'm', name: 'Model.xlsx', folder_id: 'f', page_count: 1 },
      { id: 'o', name: 'Overview.pdf', page_count: 2 },
      { id: 'c', name: 'Customers.xlsx', page_count: 1, sheet_count: 3 }], answers: [] };
  render(<RoomVisitor room={room} brand={{ brandName: 'Fictional Workspace' }} onRequest={vi.fn()} />);
  const other = screen.getByRole('region', { name: 'Other documents' });
  expect(within(other).getAllByRole('button').map(b => b.textContent)).toEqual(['Overview.pdf2 pages', 'Customers.xlsx3 sheets']);
  expect(screen.queryByText('1 page')).not.toBeInTheDocument();
  expect(screen.queryByText('01')).not.toBeInTheDocument();
  expect(screen.getByText('Documents you open are watermarked with your company and individual details. Your signed NDA is yours, unwatermarked.')).toBeInTheDocument();
});
