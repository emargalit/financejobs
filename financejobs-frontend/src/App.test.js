import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import HomePage from './HomePage';
import JobForm from './JobForm';
import PaymentResult from './PaymentResult';
import JobDetail from './JobDetail';
import { Routes, Route } from 'react-router-dom';

function response(data, ok = true) { return Promise.resolve({ ok, status: ok ? 200 : 500, json: () => Promise.resolve(data) }); }
beforeEach(() => { global.fetch = jest.fn(); sessionStorage.clear(); });
afterEach(() => { jest.restoreAllMocks(); });

test('jobs list handles server pagination and displays job details', async () => {
  fetch.mockImplementation(url => url.includes('filters') ? response({ locations: ['Zürich'], companies: ['Bank'] }) : response({ count: 21, results: [{ id: 1, title: 'Finance Analyst', company: { name: 'Bank' }, location: 'Zürich', posted_at: '2026-10-31' }] }));
  render(<MemoryRouter><HomePage /></MemoryRouter>);
  expect(await screen.findByText('Finance Analyst')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Next' }));
  await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('page=2'), expect.anything()));
});

test('jobs list reports a failed request and allows retry', async () => {
  fetch.mockImplementation(url => url.includes('filters') ? response({ locations: [], companies: [] }) : Promise.reject(new Error('Offline')));
  render(<MemoryRouter><HomePage /></MemoryRouter>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load jobs');
  expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
});

test('payment failure keeps the advertisement draft and shows an error', async () => {
  fetch.mockImplementation(url => url.includes('config') ? response({ amount: 19000, currency: 'chf', available: true, contact_email: 'owner@example.com' }) : response({ detail: 'Payment service unavailable' }, false));
  render(<MemoryRouter><JobForm /></MemoryRouter>);
  await screen.findByText('190 CHF');
  for (const [label, value] of [['Job title', 'Analyst'], ['Company name', 'Bank'], ['Contact email', 'person@example.com'], ['Location', 'Zürich'], ['Application link', 'https://example.com'], ['Job description', 'An excellent role']]) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  Object.defineProperty(global, 'crypto', { configurable: true, value: { randomUUID: () => '11111111-1111-4111-8111-111111111111' } });
  fireEvent.click(screen.getByRole('button', { name: 'Continue to payment' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Payment service unavailable');
  expect(screen.getByLabelText('Job title')).toHaveValue('Analyst');
  const sent = JSON.parse(fetch.mock.calls.find(([url]) => url.endsWith('/checkout/'))[1].body);
  expect(sent.request_id).toBe('11111111-1111-4111-8111-111111111111');
  expect(sent.amount).toBeUndefined();
});

test('success page requires backend payment confirmation', async () => {
  fetch.mockImplementation(() => response({ status: 'paid' }));
  render(<MemoryRouter initialEntries={['/payment-result?session_id=cs_test_example']}><PaymentResult /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Payment received — thank you' })).toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('manual review');
});

test('expired job shows an error instead of a broken detail page', async () => {
  fetch.mockImplementation(() => response({ detail: 'Not found.' }, false));
  render(<MemoryRouter initialEntries={['/jobs/1']}><Routes><Route path="/jobs/:id" element={<JobDetail />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole('alert')).toHaveTextContent('It may have expired');
});

test('imported job displays employer attribution and applies on the original site', async () => {
  fetch.mockImplementation(() => response({ id: 42, title: 'Portfolio Analyst', company: { name: 'LGT' }, location: 'Zürich', source: 'lgt', source_posted_at: '2026-10-25', last_seen_at: '2026-10-31T12:00:00Z', work_schedule: 'Full time', description: '<h2>Your role</h2><ul><li>Analyse portfolios</li></ul>', apply_link: 'https://lgt.wd3.myworkdayjobs.com/lgtcurrentvacancies/job/Zurich/analyst', source_url: 'https://lgt.wd3.myworkdayjobs.com/lgtcurrentvacancies/job/Zurich/analyst' }));
  render(<MemoryRouter initialEntries={['/jobs/42']}><Routes><Route path="/jobs/:id" element={<JobDetail />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Portfolio Analyst' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /Apply at LGT/ })).toHaveAttribute('href', 'https://lgt.wd3.myworkdayjobs.com/lgtcurrentvacancies/job/Zurich/analyst');
  expect(screen.getByText('25 Oct 2026')).toBeInTheDocument();
  expect(screen.getByText('31 Oct 2026')).toBeInTheDocument();
  expect(screen.getByRole('listitem')).toHaveTextContent('Analyse portfolios');
});

test('invoice option collects billing details and confirms a private request without Stripe', async () => {
  fetch.mockImplementation(url => url.includes('config') ? response({ amount: 19000, currency: 'chf', available: false, contact_email: 'owner@example.com' }) : response({ status: 'requested', reference: 'invoice-reference' }));
  render(<MemoryRouter><JobForm /></MemoryRouter>);
  await screen.findByText('190 CHF');
  expect(screen.getByRole('button', { name: 'Continue to payment' })).toBeDisabled();
  fireEvent.click(screen.getByLabelText('Request an invoice'));
  for (const [label, value] of [['Job title', 'Analyst'], ['Company name', 'Bank'], ['Contact email', 'person@example.com'], ['Location', 'Zürich'], ['Application link', 'https://example.com'], ['Job description', 'An excellent role'], ['Billing company / legal name', 'Bank AG'], ['Billing address (including postal code and country)', 'Zurich, Switzerland'], ['Invoice email', 'accounts@example.com']]) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByRole('button', { name: 'Submit invoice request' }));
  expect(await screen.findByRole('heading', { name: 'Invoice requested' })).toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('accounts@example.com');
  expect(screen.getByText(/Your ad is not published yet/)).toBeInTheDocument();
  const sent = JSON.parse(fetch.mock.calls.find(([url]) => url.endsWith('/invoice-requests/'))[1].body);
  expect(sent.billing_name).toBe('Bank AG');
  expect(sent.amount).toBeUndefined();
  expect(fetch.mock.calls.some(([url]) => url.endsWith('/checkout/'))).toBe(false);
  expect(sessionStorage.getItem('swiss-finance-job-draft')).toBeNull();
});

test('failed invoice notification preserves the draft and request ID for retry', async () => {
  fetch.mockImplementation(url => url.includes('config') ? response({ amount: 19000, currency: 'chf', available: true }) : response({ detail: 'Request saved. Please retry.' }, false));
  render(<MemoryRouter><JobForm /></MemoryRouter>);
  await screen.findByText('190 CHF');
  fireEvent.click(screen.getByLabelText('Request an invoice'));
  fireEvent.submit(screen.getByRole('button', { name: 'Submit invoice request' }).closest('form'));
  expect(await screen.findByRole('alert')).toHaveTextContent('Request saved');
  const firstId = JSON.parse(sessionStorage.getItem('swiss-finance-job-draft')).requestId;
  fireEvent.submit(screen.getByRole('button', { name: 'Submit invoice request' }).closest('form'));
  await waitFor(() => expect(fetch.mock.calls.filter(([url]) => url.endsWith('/invoice-requests/'))).toHaveLength(2));
  expect(JSON.parse(sessionStorage.getItem('swiss-finance-job-draft')).requestId).toBe(firstId);
});
