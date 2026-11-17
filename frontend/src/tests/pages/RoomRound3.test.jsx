import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import DealroomRecipient from '../../pages/DealroomRecipient';
import RoomVisitor from '../../components/dealroom/RoomVisitor';

vi.mock('../../contexts/BrandingProvider', () => ({ useBranding: () => ({ brandName: 'Fictional Workspace', brandLogoUrl: '/brand.svg' }) }));
const member = { name: 'Maya Chen', email: 'maya@northwind.test', org: 'Northwind Ventures' };
const signed = { signed: true, signed_at: '2026-11-17T12:00:00Z', email: member.email, can_enter: true, download_url: '/api/v1/dealroom/recipient/demo/signed-nda/download/' };
const room = { id: 'r', name: 'Harbor Light Analytics · Series A', member, note: 'Start with the model. — Dan', start_here: [],
  files: [{ id: 'model', name: 'Model.pdf', folder_id: 'finance', page_count: 1, page_url: '/api/v1/links/demo/render-page/1/' }, { id: 'nda', name: 'Host NDA.pdf', folder_id: 'legal', page_count: 2 }],
  folders: [{ id: 'finance', name: '02 Financials', parent_id: '' }, { id: 'legal', name: '03 Legal', parent_id: '' }], signed_nda: signed };
beforeEach(() => { localStorage.clear(); window.history.replaceState({}, '', '/view/demo?nda=complete'); });
afterEach(() => { vi.unstubAllGlobals(); });

test('signed return shows confirmation, downloads the copy, and enters the room explicitly', async () => {
  vi.stubGlobal('fetch', vi.fn(async url => ({ ok: true, json: async () => url.endsWith('/signed-nda/') ? signed : url.endsWith('/room/') ? room : { csrf_token: 'test' } })));
  render(<MemoryRouter initialEntries={['/view/demo?nda=complete']}><Routes><Route path="/view/:slug" element={<DealroomRecipient />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole('button', { name: 'Enter the data room' })).toBeEnabled();
  expect(screen.getByRole('link', { name: 'Download your signed NDA' })).toHaveAttribute('href', signed.download_url);
  expect(screen.getByText(`A copy is also on its way to ${member.email}.`)).toBeInTheDocument();
  expect(screen.queryByText(room.note)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Enter the data room' }));
  expect(await screen.findByText(room.note)).toBeInTheDocument();
});

test('preparing signed copy polls until a real download is ready', async () => {
  let reads = 0;
  vi.stubGlobal('fetch', vi.fn(async url => ({ ok: true, json: async () => url.endsWith('/signed-nda/') ? (++reads < 2 ? { ...signed, download_url: null, can_enter: false } : signed) : url.endsWith('/room/') ? room : { csrf_token: 'test' } })));
  render(<MemoryRouter initialEntries={['/view/demo?nda=complete']}><Routes><Route path="/view/:slug" element={<DealroomRecipient />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole('button', { name: 'Preparing your copy…' })).toBeDisabled();
  expect(screen.queryByRole('link', { name: 'Download your signed NDA' })).not.toBeInTheDocument();
  expect(await screen.findByRole('link', { name: 'Download your signed NDA' }, { timeout: 5000 })).toHaveAttribute('href', signed.download_url);
});

test('visitor shows collapsible folders in sender order, note first, and a separate personal NDA last', () => {
  render(<RoomVisitor room={room} brand={{ brandName: 'Fictional Workspace' }} onRequest={vi.fn()} />);
  const groups = screen.getAllByRole('group').filter(g => g.tagName === 'DETAILS');
  expect(groups.map(g => g.getAttribute('aria-label'))).toEqual(['02 Financials', '03 Legal']);
  expect(within(groups[0]).getByText('Model.pdf')).toBeInTheDocument();
  expect(groups[0]).toHaveAttribute('open');
  fireEvent.click(within(groups[0]).getByText('02 Financials'));
  expect(groups[0]).not.toHaveAttribute('open');
  expect(screen.getByText(room.note).compareDocumentPosition(groups[0]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getByText('Your signed NDA')).toBeInTheDocument();
  expect(screen.getByText(/Signed /)).toHaveTextContent('2026');
  expect(screen.getByRole('link', { name: 'Download your signed NDA' })).toHaveAttribute('href', signed.download_url);
  expect(screen.getByText('Every copy you open is watermarked with your company and individual details.')).toBeInTheDocument();
});
