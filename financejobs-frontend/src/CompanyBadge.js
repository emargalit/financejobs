import React from 'react';

const brands = {
  LGT: ['LGT', '#8b2635', '#fff1f2'],
  'Julius Bär': ['JB', '#183e5b', '#edf4f9'],
  Pictet: ['P', '#8a3435', '#f7efec'],
  Vontobel: ['V', '#17675e', '#eaf5f1'],
  'Lombard Odier': ['LO', '#263f70', '#eef1f8'],
};
export default function CompanyBadge({ name = 'Employer' }) {
  const [letters, color, background] = brands[name] || [name.split(' ').map(w => w[0]).slice(0, 2).join(''), '#334155', '#f1f5f9'];
  return <span aria-hidden="true" className="company-badge" style={{ color, background }}>{letters}</span>;
}
export function displayDate(value) {
  if (!value) return '';
  const date = new Date(value.length === 10 ? `${value}T12:00:00` : value);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}
