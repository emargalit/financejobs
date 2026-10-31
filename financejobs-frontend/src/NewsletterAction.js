import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { post } from './api';

export default function NewsletterAction({ action }) {
  const [params] = useSearchParams();
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  async function submit() {
    setBusy(true);
    try { const data = await post(`newsletter/${action}/`, { token: params.get('token') }); setMessage(data.detail); setDone(true); }
    catch (err) { setMessage(err.message); }
    finally { setBusy(false); }
  }
  return <div className="bg-white rounded-xl p-8 max-w-lg mx-auto">
    <h1 className="text-2xl font-bold mb-4">{action === 'confirm' ? 'Confirm your newsletter subscription' : 'Unsubscribe from the newsletter'}</h1>
    {message && <p role="status" className="mb-4">{message}</p>}
    {!done && <button disabled={busy} onClick={submit} className="bg-blue-700 text-white p-3 rounded">{busy ? 'Please wait…' : action === 'confirm' ? 'Confirm subscription' : 'Unsubscribe'}</button>}
  </div>;
}
