import { useState } from 'react';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, test, expect, vi } from 'vitest';
import RoomDetailPage from '../../pages/dealroom/RoomDetailPage';
import DriveImport, { ImportReview } from '../../components/dealroom/DriveImport';
import api from '../../services/api';

vi.mock('../../services/api', () => ({ default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));
const definitions = { team: { id: 'team', name: 'Team bios', folder: 'team' }, ip: { id: 'ip', name: 'IP assignment agreements', folder: 'legal' } };
const doc = { id: 'doc', document_id: 'd', name: 'Deck.pdf', source: { modifiedTime: '2026-11-17T10:00:00Z' } };
let outline;
beforeEach(() => {
  vi.clearAllMocks();
  outline = { template: 'series_a', documents: [doc], groups: [{ id: 'team', name: 'Team', slots: [['team', 'Team bios']] }, { id: 'legal', name: 'Legal', slots: [['ip', 'IP assignment agreements']] }], slot_definitions: definitions, slots: {}, start_here: ['doc'], not_needed: [], needs_you: [{ id: 'q', kind: 'question', text: 'When?', email: 'maya@example.test' }], drive_roots: ['root'], drive_checked_at: '2026-11-17T12:00:00Z' };
  api.get.mockImplementation(async path => ({ data: path.endsWith('/outline/') ? outline : path === '/dealroom/rooms/r/' ? { id: 'r', name: 'Private room' } : path === '/datarooms/r/' ? { items: [] } : [] }));
  api.patch.mockResolvedValue({ data: {} });
});
function mountRoom(path = '/datarooms/r') {
  render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/datarooms/:dataroomId" element={<RoomDetailPage />} /></Routes></MemoryRouter>);
}
test('sender sees named missing slots with Add file and a waiting count badge', async () => {
  mountRoom();
  const add = await screen.findByRole('button', { name: 'Add file for Team bios' });
  expect(within(add.parentElement).getByText('Team bios')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Add file for IP assignment agreements' })).toBeInTheDocument();
  const nav = screen.getByRole('navigation', { name: 'Room sections' });
  expect(within(nav).getByText('1')).toHaveClass('fds-pill');
  expect(screen.getByText(/Last checked/)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Check Drive for updates' })).toBeEnabled();
  expect(screen.getByRole('button', { name: 'Move Deck.pdf down' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Unpin Deck.pdf' })).toHaveAttribute('title', 'Unpin Deck.pdf');
});
test('Drive review keeps Documents selected and invitation secondary', async () => {
  mountRoom('/datarooms/r?drive=1');
  await screen.findByText('Read folders');
  const nav = screen.getByRole('navigation', { name: 'Room sections' });
  expect(within(nav).getByText('Documents')).toHaveAttribute('aria-current', 'page');
  expect(screen.getByRole('button', { name: 'Invite investors' })).not.toHaveClass('dr-btn--primary');
});
test('empty room invitation is secondary and ready room invitation is primary', async () => {
  outline.documents = [];
  const { unmount } = render(<MemoryRouter initialEntries={['/datarooms/r']}><Routes><Route path="/datarooms/:dataroomId" element={<RoomDetailPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole('button', { name: 'Invite investors' })).not.toHaveClass('dr-btn--primary');
  unmount(); outline.documents = [doc]; mountRoom();
  await waitFor(() => expect(screen.getByRole('button', { name: 'Invite investors' })).toHaveClass('dr-btn--primary'));
});
const review = { template: '', ticket: 'signed', roots: [{ id: 'root', name: 'Harbor Light' }], matched: [], nodes: [
  { id: 'finance', parent_id: 'root', type: 'folder', name: 'Finance' },
  { id: 'nested', parent_id: 'finance', type: 'folder', name: 'Forecasts' },
  { id: 'deck', parent_id: 'finance', type: 'file', name: 'Deck.pdf', mimeType: 'application/pdf', final_type: 'pdf', import_description: 'PDF, added as is' },
  { id: 'notes', parent_id: 'nested', type: 'file', name: 'Notes', mimeType: 'application/vnd.google-apps.document', final_name: 'Notes.pdf', final_type: 'pdf', import_description: 'Google Doc, saved as a PDF copy' },
], skipped: [{ id: 'form', name: 'Investor form', skip_reason: 'Google Forms cannot be imported.' }] };
function ReviewHarness() {
  const [excluded, setExcluded] = useState([]);
  const [destinations, setDestinations] = useState({});
  return <ImportReview review={review} choices={{}} onChange={vi.fn()} excluded={excluded} onExcludedChange={setExcluded} destinations={destinations} onDestinationsChange={setDestinations} onConfirm={vi.fn()} />;
}
test('nested review shows final types, skipped reasons and exclusion updates confirmation count', () => {
  render(<ReviewHarness />);
  expect(screen.getByText('Google Doc, saved as a PDF copy')).toBeInTheDocument();
  expect(screen.getByText('PDF, added as is')).toBeInTheDocument();
  expect(screen.getAllByTestId('file-type-icon-pdf')).toHaveLength(2);
  expect(screen.getByText('Google Forms cannot be imported.')).toBeInTheDocument();
  expect(screen.getByRole('group', { name: 'Finance' })).toContainElement(screen.getByRole('group', { name: 'Forecasts' }));
  expect(within(screen.getByRole('group', { name: 'Forecasts' })).getByText('Notes.pdf')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Exclude Notes' }));
  expect(screen.getByRole('button', { name: 'Confirm and import 1 file' })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Exclude Deck.pdf' }));
  expect(screen.getByRole('button', { name: 'Confirm and import 0 files' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Include Notes' }));
  expect(screen.getByRole('button', { name: 'Confirm and import 1 file' })).toBeEnabled();
});
test('review can switch from Drive folders to matched, unsure and missing and submit exclusions', async () => {
  api.post.mockImplementation(async path => ({ data: path.endsWith('/drive-review/') ? { ...review, template: api.post.mock.calls.at(-1)[1].template, matched: [] } : { imported: ['deck'] } }));
  render(<DriveImport roomId="r" definitions={definitions} onImported={vi.fn()} onClose={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('Drive folder links · one per line'), { target: { value: 'https://drive.google.com/drive/folders/root' } });
  fireEvent.click(screen.getByRole('button', { name: 'Read folders' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Match to a Series A checklist instead' }));
  expect(await screen.findByText('Matched · 0')).toBeInTheDocument();
  expect(screen.getByText('Unsure · 2')).toBeInTheDocument();
  expect(screen.getByText('Missing · 2')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Exclude Notes' }));
  fireEvent.click(screen.getByRole('button', { name: 'Confirm and import 1 file' }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith('/dealroom/rooms/r/drive-import/', expect.objectContaining({ excluded: ['notes'] })));
});


test('moving a reviewed file changes its folder and keeps the selected count', () => {
  render(<ReviewHarness />);
  fireEvent.keyDown(screen.getByRole('button', { name: 'Move Notes to' }), { key: 'Enter' });
  fireEvent.click(screen.getByRole('menuitemradio', { name: 'Finance' }));
  expect(within(screen.getByRole('group', { name: 'Forecasts' })).queryByText('Notes.pdf')).not.toBeInTheDocument();
  expect(within(screen.getByRole('group', { name: 'Finance' })).getByText('Notes.pdf')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Confirm and import 2 files' })).toBeEnabled();
});

test('Needs you badge disappears when no requests are waiting', async () => {
  outline.needs_you = [];
  mountRoom();
  await screen.findByRole('button', { name: 'Invite investors' });
  expect(within(screen.getByRole('navigation', { name: 'Room sections' })).queryByText('1')).not.toBeInTheDocument();
});

test('start-here down arrow saves the changed document order', async () => {
  outline.documents.push({ id: 'other', document_id: 'other-doc', name: 'Model.xlsx' });
  outline.start_here.push('other');
  mountRoom();
  fireEvent.click(await screen.findByRole('button', { name: 'Move Deck.pdf down' }));
  await waitFor(() => expect(api.patch).toHaveBeenCalledWith('/dealroom/rooms/r/outline/', { start_here: ['other', 'doc'] }));
});
