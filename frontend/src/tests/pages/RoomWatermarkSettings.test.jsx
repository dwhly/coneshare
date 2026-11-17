import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { test, expect, vi } from 'vitest';
import WatermarkSettings from '../../components/dealroom/WatermarkSettings';
import api from '../../services/api';
vi.mock('../../services/api', () => ({ default: { get: vi.fn(), patch: vi.fn() } }));

test('workspace default uses the common style menu and persists Edge', async () => {
  api.get.mockResolvedValue({ data: { watermark_style: 'diagonal' } });
  api.patch.mockResolvedValue({ data: { watermark_style: 'edge' } });
  render(<WatermarkSettings />);
  await waitFor(() => expect(screen.getByRole('button', { name: 'Watermark style' })).toBeEnabled());
  fireEvent.keyDown(screen.getByRole('button', { name: 'Watermark style' }), { key: 'ArrowDown' });
  fireEvent.click(await screen.findByRole('menuitemradio', { name: 'Edge' }));
  await waitFor(() => expect(api.patch).toHaveBeenCalledWith('/dealroom/workspace-settings/', { watermark_style: 'edge' }));
});

test('room style can override and return to the workspace default', async () => {
  const save = vi.fn();
  render(<WatermarkSettings roomStyle="edge" onSave={save} />);
  fireEvent.keyDown(screen.getByRole('button', { name: 'Watermark style' }), { key: 'ArrowDown' });
  fireEvent.click(await screen.findByRole('menuitemradio', { name: 'Workspace default' }));
  expect(save).toHaveBeenCalledWith(null);
});
