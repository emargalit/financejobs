import React, { useEffect, useState } from 'react';
import { api } from './api';
import { Link, useParams } from 'react-router-dom';
import { ArrowUpRight, MapPin, Clock3, ArrowLeft } from 'lucide-react';
import CompanyBadge, { displayDate } from './CompanyBadge';

export default function JobDetail() {
  const { id } = useParams();
  const [job, setJob] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setJob(null); setError('');
    api(`jobs/${id}/`, { signal: controller.signal }).then(setJob).catch(err => { if (err.name !== 'AbortError') setError(err.message); });
    return () => controller.abort();
  }, [id]);
  if (error) return <div role="alert" className="jobs-empty"><h1>This job could not be loaded. It may have expired.</h1><p>{error}</p><Link to="/">Browse current jobs</Link></div>;
  if (!job) return <p role="status" className="jobs-loading">Loading job…</p>;
  return <div className="job-detail-page">
    <Link to="/" className="back-to-jobs"><ArrowLeft size={16} />All opportunities</Link>
    <header className="job-detail-header"><CompanyBadge name={job.company?.name} /><div><p className="job-employer">{job.company?.name}</p><h1>{job.title}</h1><div className="job-meta"><span><MapPin size={16} />{job.location}</span>{job.work_schedule && <span><Clock3 size={16} />{job.work_schedule}</span>}{job.job_type && !(job.job_type === 'Part-Time' && job.work_schedule === 'Part time') && <span className="job-type">{job.job_type}</span>}</div></div></header>
    <div className="job-detail-grid">
      <article className="job-description" dangerouslySetInnerHTML={{ __html: job.description }} />
      <aside className="job-apply-panel"><p className="section-eyebrow">YOUR NEXT STEP</p><h2>Make your move.</h2><p>{job.source ? 'Apply directly through the employer’s careers website.' : 'Visit the employer’s application page to apply.'}</p>
        <a className="apply-button" href={job.apply_link} target="_blank" rel="noopener noreferrer">Apply at {job.company?.name || 'employer'} <ArrowUpRight size={18} /></a>
        <dl><dt>{job.source_posted_at ? 'Posted by employer' : 'Added to our board'}</dt><dd>{displayDate(job.source_posted_at || job.posted_at)}</dd>{job.source && <><dt>Last checked</dt><dd>{displayDate(job.last_seen_at)}</dd><dt>Source</dt><dd><a href={job.source_url} target="_blank" rel="noopener noreferrer">{job.company?.name} careers ↗</a></dd></>}{job.salary && <><dt>Salary</dt><dd>{job.salary}</dd></>}</dl>
        {job.source && <p className="source-note">An independently listed opportunity. Availability and application details are confirmed on the employer’s website.</p>}
      </aside>
    </div>
  </div>;
}
