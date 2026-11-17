import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { beforeEach, test, expect, vi } from 'vitest';
import EntryNda from '../../components/dealroom/EntryNda';
import api from '../../services/api';
vi.mock('../../services/api', () => ({ default: { get: vi.fn(), put: vi.fn(), post: vi.fn() } }));
vi.mock('../../hooks/usePdfDocument', () => ({ usePdfDocument: () => ({ pdfDoc: {}, numPages: 1, pageDimensions: [{ width: 612, height: 792 }], loading: false }) }));
vi.mock('../../components/documents/PdfPage', () => ({ PdfPage: () => <div>Rendered PDF page</div> }));
const fields = ['SIGNATURE', 'NAME', 'TEXT', 'DATE'].map((type, n) => ({ type, page: 1, positionX: 20, positionY: 60 + n * 7, width: 50, height: 3, identifier: 0 }));
beforeEach(() => {
  vi.clearAllMocks();
  api.get.mockResolvedValue({ data: { enabled: true, confirmed: false, revision: 'rev', source_version_id: 'v', name: 'Investor NDA (fictional).pdf', fields: [], suggestions: fields, pdf_url: '/api/v1/source.pdf' } });
  api.put.mockImplementation(async (path, data) => ({ data: { ...data, source_version_id: data.version_id, confirmed: true, name: 'Investor NDA (fictional).pdf' } }));
});
test('drag and resize persist exact adjusted percentages only after sender confirmation', async () => {
  render(<EntryNda roomId="r" documents={[]} onRefresh={vi.fn()} />);
  const field = await screen.findByRole('button', { name: 'Move Signature field 1' });
  const page = screen.getByTestId('nda-page');
  page.getBoundingClientRect = () => ({ left: 0, top: 0, width: 600, height: 800 });
  window.PointerEvent = MouseEvent;
  fireEvent.pointerDown(field, { clientX: 120, clientY: 480, pointerId: 1 });
  fireEvent.pointerMove(field, { clientX: 150, clientY: 496, pointerId: 1 });
  fireEvent.pointerUp(field);
  const resize = screen.getByRole('button', { name: 'Resize Signature field 1' });
  fireEvent.pointerDown(resize, { clientX: 450, clientY: 520, pointerId: 2 });
  fireEvent.pointerMove(resize, { clientX: 480, clientY: 528, pointerId: 2 });
  fireEvent.pointerUp(resize);
  expect(api.put).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Use these positions' }));
  await waitFor(() => expect(api.put).toHaveBeenCalled());
  const saved = api.put.mock.calls[0][1];
  expect(saved).toMatchObject({ version_id: 'v', revision: 'rev', confirm: true });
  expect(saved.fields[0]).toEqual({ ...fields[0], positionX: 25, positionY: 62, width: 55, height: 4 });
  expect(await screen.findByText('Positions confirmed')).toBeInTheDocument();
});
test('palette adds and deletes fields; no signature cannot be confirmed', async () => {
  render(<EntryNda roomId="r" documents={[]} onRefresh={vi.fn()} />);
  await screen.findByRole('button', { name: 'Move Signature field 1' });
  fireEvent.click(screen.getByRole('button', { name: 'Add Initials' }));
  expect(screen.getByRole('button', { name: 'Move Initials field 5' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Delete Signature field 1' }));
  expect(screen.getByRole('button', { name: 'Use these positions' })).toBeDisabled();
});
test('uploading a replacement clears confirmed state and starts a fresh review', async () => {
  api.get.mockResolvedValue({ data: { confirmed: true, source_version_id: 'old', fields, name: 'Old.pdf' } });
  api.post.mockResolvedValue({ data: { confirmed: false, source_version_id: 'new', revision: 'next', fields: [], suggestions: fields, pdf_url: '/api/new.pdf', name: 'New.pdf' } });
  render(<EntryNda roomId="r" documents={[]} onRefresh={vi.fn()} />);
  await screen.findByText('Positions confirmed');
  fireEvent.change(screen.getByLabelText('Upload entry NDA PDF'), { target: { files: [new File(['pdf'], 'New.pdf', { type: 'application/pdf' })] } });
  await screen.findByRole('button', { name: 'Use these positions' });
  expect(screen.queryByText('Positions confirmed')).not.toBeInTheDocument();
  expect(api.post.mock.calls[0][1]).toBeInstanceOf(FormData);
  expect(api.put).not.toHaveBeenCalled();
});

test('blocked sharing offers placement and disables personal invitations', async () => {
  const { MemoryRouter, Routes, Route } = await import('react-router-dom');
  const { default: RoomDetailPage } = await import('../../pages/dealroom/RoomDetailPage');
  const outline = { share_blocked: true, nda_configured: false, require_nda: true, documents: [], groups: [], slots: {}, start_here: [], not_needed: [], needs_you: [], policy: {} };
  api.get.mockImplementation(async path => ({ data: path.endsWith('/outline/') ? outline : path === '/dealroom/rooms/r/' ? { id: 'r', name: 'Room', entry_url: '/view/private' } : path === '/datarooms/r/' ? { items: [] } : path.endsWith('/entry-nda/') ? { confirmed: false, fields: [] } : [] }));
  render(<MemoryRouter initialEntries={['/datarooms/r']}><Routes><Route path="/datarooms/:dataroomId" element={<RoomDetailPage />} /></Routes></MemoryRouter>);
  const callToAction = await screen.findByRole('button', { name: 'Place the NDA fields' });
  expect(screen.getByText('Visitor link')).not.toHaveAttribute('href');
  fireEvent.click(screen.getByRole('button', { name: 'Invite investors' }));
  fireEvent.change(screen.getByLabelText('Email addresses'), { target: { value: 'maya@northwind.test' } });
  expect(screen.getByRole('button', { name: 'Send personal invitations' })).toBeDisabled();
  fireEvent.click(callToAction);
  expect(await screen.findByText('Entry NDA')).toBeInTheDocument();
});
