import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, afterEach, test, expect, vi } from 'vitest';
import DealroomRecipient from '../../pages/DealroomRecipient';

const response = (data, ok=true) => Promise.resolve({ok,json:async()=>data});
beforeEach(()=>{
  window.history.replaceState({},'', '/view/atlas');
  vi.stubGlobal('fetch',vi.fn(url=>url.endsWith('/challenge/')?response({csrf_token:'csrf'}):response({},false)));
});
afterEach(()=>vi.unstubAllGlobals());
function mount(){render(<MemoryRouter initialEntries={['/view/atlas']}><Routes><Route path="/view/:slug" element={<DealroomRecipient/>}/></Routes></MemoryRouter>)}
test('scanner GET never redeems a link without explicit confirmation',async()=>{
  window.history.replaceState({},'', '/view/atlas#challenge=123&token=secret');
  mount();await screen.findByRole('button',{name:'Confirm access'});
  expect(window.location.hash).toBe('');
  expect(window.location.search).toBe('');
  expect(fetch.mock.calls.every(([,options])=>!options?.method||options.method==='GET')).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Confirm access'}));
  await waitFor(()=>expect(fetch.mock.calls.some(([url,options])=>url.endsWith('/confirm/')&&options.method==='POST'&&JSON.parse(options.body).token==='secret')).toBe(true));
});
test('verification refusal does not render the room or filenames',async()=>{
  fetch.mockImplementation(url=>url.endsWith('/challenge/')?response({csrf_token:'csrf',challenge_id:'challenge'}):url.endsWith('/confirm/')?response({status:'refused',message:'Access refused'}):response({},false));
  mount();fireEvent.change(screen.getByLabelText('Your name'),{target:{value:'Bob'}});fireEvent.change(screen.getByLabelText('Email address'),{target:{value:'bob@other.test'}});
  fireEvent.click(screen.getByRole('button',{name:'Send verification code'}));await screen.findByLabelText('Verification code');
  fireEvent.change(screen.getByLabelText('Verification code'),{target:{value:'123456'}});fireEvent.click(screen.getByRole('button',{name:'Confirm access'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Access refused');expect(screen.queryByText('Documents')).not.toBeInTheDocument();
});

test('a personal invitation cannot silently reuse another visitor identity', async () => {
  window.history.replaceState({}, '', '/view/atlas#personal=personal-token');
  mount();
  const button = await screen.findByRole('button', { name: 'Review the NDA' });
  await waitFor(() => expect(button).not.toBeDisabled());
  expect(fetch.mock.calls.some(([url]) => url.endsWith('/room/'))).toBe(false);
  expect(fetch.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(false);
  fireEvent.click(button);
  await waitFor(() => expect(fetch.mock.calls.some(([url, options]) => url.endsWith('/personal/') && JSON.parse(options.body).token === 'personal-token')).toBe(true));
});


test('personal invitation shows tenant identity and sender before the NDA without room details', async () => {
  window.history.replaceState({}, '', '/view/atlas#personal=personal-token');
  fetch.mockImplementation(url => url.endsWith('/challenge/') ? response({ csrf_token: 'csrf', brand: { name: 'AmForge', logo: '/amforge.svg' }, sender_name: 'Dan Whaley' }) : url.endsWith('/personal/') ? response({ status: 'verified' }) : response({ code: 'nda_required', room_id: 'r' }, false));
  mount();
  expect(await screen.findByText('Dan Whaley invited you')).toBeInTheDocument();
  expect(screen.getByText('AmForge')).toBeInTheDocument();
  expect(document.querySelector('img')).toHaveAttribute('src', '/amforge.svg');
  expect(screen.queryByText('Project Atlas')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Review the NDA' }));
  expect(await screen.findByText('Before you enter')).toBeInTheDocument();
  expect(screen.getByText('AmForge')).toBeInTheDocument();
  expect(screen.queryByText('Project Atlas')).not.toBeInTheDocument();
});
