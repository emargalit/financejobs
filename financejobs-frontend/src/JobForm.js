import React, { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api, post } from './api';

const emptyForm = { title: '', company_name: '', contact_email: '', location: '', salary: '', apply_link: '', job_type: '', description: '' };
const jobTypes = ['Permanent', 'Internships / Graduate Programs', 'Fixed-Term / Contract', 'Part-Time'];
const storageKey = 'swiss-finance-job-draft';
function readDraft() {
  try { return JSON.parse(sessionStorage.getItem(storageKey)) || {}; } catch { return {}; }
}

export default function JobForm() {
  const [formData, setFormData] = useState(() => ({ ...emptyForm, ...readDraft().formData }));
  const [config, setConfig] = useState(null);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [params] = useSearchParams();
  const requestId = useRef(readDraft().requestId || null);

  useEffect(() => { api('checkout/config/').then(setConfig).catch(() => setError('Unable to load payment information. Please reload the page.')); }, []);

  function change(e) {
    const next = { ...formData, [e.target.name]: e.target.value };
    setFormData(next); requestId.current = null;
    try { sessionStorage.setItem(storageKey, JSON.stringify({ formData: next })); } catch {}
  }

  async function submit(e) {
    e.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true); setError('');
    try {
      if (!requestId.current) requestId.current = crypto.randomUUID();
      try { sessionStorage.setItem(storageKey, JSON.stringify({ formData, requestId: requestId.current })); } catch {}
      const data = await post('checkout/', { ...formData, request_id: requestId.current });
      const checkout = new URL(data.url);
      if (checkout.protocol !== 'https:' || checkout.hostname !== 'checkout.stripe.com') throw new Error('Invalid checkout destination. Please contact support.');
      window.location.assign(checkout.href);
    } catch (err) {
      if (err.status === 410) {
        requestId.current = null;
        try { sessionStorage.setItem(storageKey, JSON.stringify({ formData })); } catch {}
      }
      setError(err.message); setIsSubmitting(false);
    }
  }

  return <div className="max-w-2xl mx-auto p-6 bg-white shadow rounded-xl">
    <Link to="/" className="text-blue-700 underline">← Back to jobs</Link>
    <h1 className="text-2xl font-bold my-5">Post a job</h1>
    <div className="bg-blue-50 border border-blue-100 p-5 rounded-lg mb-6">
      <h2 className="font-semibold">Standard listing · 30 days</h2>
      <p className="text-3xl font-bold text-blue-800 mt-2">{config ? `${(config.amount / 100).toLocaleString('en-CH')} ${config.currency.toUpperCase()}` : 'Loading price…'}</p>
      <p className="mt-3">Submit your job ad and pay securely with Stripe. We’ll publish it within 2 hours of payment. Your ad will stay live for 30 days from publication.</p>
      {config && <p className="mt-2 text-sm">Questions or a refund request? <a className="underline" href={`mailto:${config.contact_email}`}>{config.contact_email}</a></p>}
    </div>
    {params.has('cancelled') && <p role="status" className="bg-amber-50 p-3 mb-4">Checkout was cancelled. Your draft is saved in this tab; you can return to payment below.</p>}
    {error && <p role="alert" className="bg-red-50 text-red-800 p-3 mb-4">{error}</p>}
    {config && !config.available && <p role="status" className="p-3 mb-4 bg-amber-50">Online payments are temporarily unavailable. Please contact us or try again later.</p>}
    <form onSubmit={submit} className="space-y-4">
      {[
        ['title', 'Job title', 'text', true], ['company_name', 'Company name', 'text', true],
        ['contact_email', 'Contact email', 'email', true], ['location', 'Location', 'text', true],
        ['salary', 'Salary (optional)', 'text', false], ['apply_link', 'Application link', 'url', true],
      ].map(([name, label, type, required]) => <div key={name}>
        <label htmlFor={name} className="block font-medium mb-1">{label}</label>
        <input id={name} name={name} type={type} required={required} maxLength={name === 'apply_link' ? 500 : name === 'contact_email' ? 254 : 255} value={formData[name]} onChange={change} disabled={isSubmitting} className="w-full p-3 border rounded-md" />
      </div>)}
      <div><label htmlFor="job_type" className="block font-medium mb-1">Job type (optional)</label>
        <select id="job_type" name="job_type" value={formData.job_type} onChange={change} disabled={isSubmitting} className="w-full p-3 border rounded-md"><option value="">Select a job type</option>{jobTypes.map(type => <option key={type}>{type}</option>)}</select></div>
      <div><label htmlFor="description" className="block font-medium mb-1">Job description</label>
        <textarea id="description" name="description" required rows={10} maxLength={20000} value={formData.description} onChange={change} disabled={isSubmitting} className="w-full p-3 border rounded-md" /></div>
      <p className="text-sm text-gray-600">Your contact email and draft are used to process this advertisement. Card details are handled by Stripe. Payment does not publish the advertisement automatically.</p>
      <button disabled={isSubmitting || !config?.available} className="w-full bg-blue-700 text-white font-semibold p-3 rounded-md disabled:opacity-50">{isSubmitting ? 'Opening secure checkout…' : 'Continue to payment'}</button>
    </form>
  </div>;
}
