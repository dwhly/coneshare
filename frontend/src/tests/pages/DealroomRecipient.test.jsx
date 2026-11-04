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
