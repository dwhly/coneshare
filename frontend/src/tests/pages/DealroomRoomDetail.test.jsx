import { render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { test, expect, vi } from 'vitest';
import RoomDetailPage from '../../pages/dealroom/RoomDetailPage';
import { withFolderPaths } from '../../pages/dealroom/data';

// The datarooms API returns only root-level items unless ?content=full (DataroomDetailSerializer.get_items).
const executed = { type: 'folder', id: 'f1', name: 'Executed', parent: null, ancestors: [] };
const agreements = { type: 'folder', id: 'f2', name: 'Agreements', parent: 'f1', ancestors: [{ id: 'f1', name: 'Executed' }] };
const rootDoc = { type: 'document', id: 'd1', document_id: 'doc1', name: 'Teaser.pdf', folder: null, file_size: 1000, created_at: '2026-11-01T00:00:00Z' };
const signed = { type: 'document', id: 'd2', document_id: 'doc2', name: 'SPA_signed.pdf', folder: 'f2', file_size: 2000, created_at: '2026-11-02T00:00:00Z' };

vi.mock('../../services/api', () => ({
  default: {
    get: vi.fn(async (path, config) => {
      if (path === '/dealroom/rooms/r1/') return { data: { id: 'r1', name: 'Project Atlas', entry_url: '/signing/room/abc' } };
      if (path === '/datarooms/r1/') {
        const full = config?.params?.content === 'full';
        return { data: { created_at: '2026-11-01T00:00:00Z', items: full ? [executed, agreements, rootDoc, signed] : [executed, rootDoc] } };
      }
      return { data: [] };
    }),
    delete: vi.fn(),
    post: vi.fn(),
  },
}));

test('room Documents card lists documents inside folders (signed copies), with their folder path (review r1 [2])', async () => {
  render(
    <MemoryRouter initialEntries={['/datarooms/r1']}>
      <Routes>
        <Route path="/datarooms/:dataroomId" element={<RoomDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
  const cell = await screen.findByText('SPA_signed.pdf');
  expect(within(cell.parentElement).getByText('Executed / Agreements')).toBeInTheDocument();
  expect(screen.getByText('Teaser.pdf')).toBeInTheDocument();
});

test('withFolderPaths puts root documents first and keeps the server order within a folder', () => {
  const docs = withFolderPaths([signed, rootDoc, { ...signed, id: 'd3', name: 'NDA_signed.pdf' }], [executed, agreements]);
  expect(docs.map((d) => [d.name, d.folder_path])).toEqual([
    ['Teaser.pdf', ''],
    ['SPA_signed.pdf', 'Executed / Agreements'],
    ['NDA_signed.pdf', 'Executed / Agreements'],
  ]);
});
