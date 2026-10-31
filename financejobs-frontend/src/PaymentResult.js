import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from './api';

export default function PaymentResult() {
  const [params] = useSearchParams();
  const session = params.get('session_id');
  const [status, setStatus] = useState('pending');
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let stopped = false, timer, attempts = 0;
    setError('');
    async function check() {
      if (!session) { setError('No payment reference was provided.'); return; }
      try {
        const data = await api(`checkout/status/?session_id=${encodeURIComponent(session)}`);
        if (stopped) return;
        setStatus(data.status);
        if (data.status === 'paid' || data.status === 'published') {
          try { sessionStorage.removeItem('swiss-finance-job-draft'); } catch {}
        } else if (++attempts < 15) timer = setTimeout(check, 2000);
        else setError('Payment confirmation is taking longer than expected. Check again shortly; please do not pay again.');
      } catch (err) { if (!stopped) setError(err.message); }
    }
    check();
    return () => { stopped = true; clearTimeout(timer); };
  }, [session, retry]);
  return <div className="max-w-xl mx-auto p-8 bg-white rounded-xl shadow">
    <h1 className="text-2xl font-bold mb-4">{status === 'published' ? 'Your advertisement is published' : status === 'paid' ? 'Payment received — thank you' : 'Confirming your payment'}</h1>
    <p role="status">{status === 'paid' ? 'Your advertisement is saved for manual review. Its 30-day listing period starts when it is published.' : status === 'published' ? 'Your job listing is now available on Swiss Finance Jobs.' : 'We’re waiting for secure confirmation from Stripe. You do not need to submit another payment.'}</p>
    {error && <div role="alert" className="mt-4"><p>{error}</p><button onClick={() => setRetry(retry + 1)} className="text-blue-700 underline mt-2">Check again</button></div>}
    <Link to="/" className="block text-blue-700 underline mt-6">Back to jobs</Link>
  </div>;
}
