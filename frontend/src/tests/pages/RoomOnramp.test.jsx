import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { test, expect, vi } from 'vitest';
import { ImportReview } from '../../components/dealroom/DriveImport';
import RoomVisitor, { VisitorReader } from '../../components/dealroom/RoomVisitor';

const file = { id: 'model', name: 'Financial model.xlsx', page_count: 14, page_url: '/api/v1/links/demo/render-page/1/?dataroom_document_id=model', folder_id: 'finance', published_at: '2026-11-18T12:00:00Z', version_number: 2 };
const member = { name: 'Maya Chen', org: 'Northwind', email: 'maya@northwind.test' };

test('review shows matched, unsure, missing and confirms only on explicit action', () => {
  const confirm = vi.fn(); const change = vi.fn();
  const review = { template: 'series_a', roots: [{ name: 'Harbor Light' }], nodes: [{ id: 'model', type: 'file', name: 'Financial model', folder_path: 'Financials', mimeType: 'application/vnd.google-apps.spreadsheet' }, { id: 'notes', type: 'file', name: 'Notes for investors - draft', mimeType: 'application/vnd.google-apps.document' }], slot_definitions: { model: { id: 'model', name: 'Financial model' }, team: { id: 'team', name: 'Team bios' } } };
  render(<ImportReview review={review} choices={{ model: 'model' }} onChange={change} onConfirm={confirm} />);
  expect(screen.getByText('Matched · 1')).toBeInTheDocument();
  expect(screen.getByText('Unsure · 1')).toBeInTheDocument();
  expect(screen.getByText('Missing · 1')).toBeInTheDocument();
  expect(screen.getByText('Team bios')).toBeInTheDocument();
  expect(screen.getByText('Notes for investors - draft')).toBeInTheDocument();
  expect(confirm).not.toHaveBeenCalled();
  fireEvent.drop(screen.getByText('Team bios').parentElement, { dataTransfer: { getData: () => 'notes' } });
  expect(change).toHaveBeenCalledWith({ model: 'model', notes: 'team' });
  fireEvent.click(screen.getByRole('button', { name: 'Confirm and import 2 files' }));
  expect(confirm).toHaveBeenCalledOnce();
});

test('reader uses the protected page endpoint, preserves drafts, requests copies without downloads', async () => {
  const request = vi.fn().mockResolvedValue({ status: 'sent' });
  render(<VisitorReader file={file} files={[file, { ...file, id: 'deck', name: 'Pitch deck.pdf' }]} member={member} onBack={vi.fn()} onSelect={vi.fn()} onRequest={request} />);
  expect(screen.getByRole('img')).toHaveAttribute('src', file.page_url);
  fireEvent.click(screen.getByRole('button', { name: 'Next page' }));
  expect(screen.getByRole('img')).toHaveAttribute('src', file.page_url.replace('/1/', '/2/'));
  fireEvent.click(screen.getByRole('button', { name: 'Ask' }));
  fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'What drives the margin?' } });
  fireEvent.click(screen.getByRole('button', { name: 'Close' }));
  fireEvent.click(screen.getByRole('button', { name: 'Ask' }));
  expect(screen.getByLabelText('Your question')).toHaveValue('What drives the margin?');
  fireEvent.click(screen.getByRole('button', { name: 'Send question' }));
  await waitFor(() => expect(request).toHaveBeenCalledWith({ item_id: 'model', kind: 'question', page: 2, text: 'What drives the margin?' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Question sent');
  fireEvent.click(screen.getByRole('button', { name: 'Close' }));
  fireEvent.click(screen.getByRole('button', { name: 'Get a copy' }));
  expect(screen.getByText(/Downloads are off/)).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: /Download/ })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Request a copy' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Copy requested');
});

test('return visit opens updated files and follows sender start-here order', () => {
  localStorage.setItem('room-visit:r:maya@northwind.test', JSON.stringify({ at: '2026-11-17T12:00:00Z', file: 'model', page: 6 }));
  render(<RoomVisitor room={{ id: 'r', name: 'Harbor Light · Series A', member, files: [file], folders: [{ id: 'finance', name: '02 Financials' }], start_here: ['model'], note: 'Start with the model.', answers: [] }} brand={{ brandName: 'Dealroom', brandLogoUrl: '/logo.svg' }} onRequest={vi.fn()} />);
  expect(screen.getByText('Welcome back, Maya')).toBeInTheDocument();
  expect(screen.getByText('Updated')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Pick up where you stopped · page 6' }));
  expect(screen.getByRole('img')).toHaveAttribute('src', file.page_url.replace('/1/', '/6/'));
});
