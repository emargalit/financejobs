import React from 'react';
import { Link } from 'react-router-dom';
import { MapPin, ArrowUpRight, Clock3 } from 'lucide-react';
import CompanyBadge, { displayDate } from './CompanyBadge';

export default function JobsList({ jobs, loading }) {
  if (loading) return <div role="status" className="jobs-loading">Finding your next opportunity…<div className="job-skeleton" /><div className="job-skeleton" /><div className="job-skeleton" /></div>;
  if (!jobs.length) return <div className="jobs-empty"><h2>No matching opportunities</h2><p>Try a different keyword or clear a filter to explore more roles.</p></div>;
  return <ul className="job-cards">
    {jobs.map(job => <li key={job.id} className="job-card">
      <div className="job-card-top"><CompanyBadge name={job.company?.name} /><div className="min-w-0 flex-1">
        <p className="job-employer">{job.company?.name}</p>
        <h2><Link to={`/jobs/${job.id}`}>{job.title}</Link></h2>
      </div><ArrowUpRight className="job-card-arrow" size={20} aria-hidden="true" /></div>
      <div className="job-meta"><span><MapPin size={14} aria-hidden="true" />{job.location}</span>{job.work_schedule && <span><Clock3 size={14} aria-hidden="true" />{job.work_schedule}</span>}{job.job_type && !(job.job_type === 'Part-Time' && job.work_schedule === 'Part time') && <span className="job-type">{job.job_type}</span>}</div>
      <div className="job-card-footer"><span>{job.source_posted_at ? `Posted ${displayDate(job.source_posted_at)}` : `Added ${displayDate(job.posted_at)}`}{job.source && <span className="source-label"> · Employer careers site</span>}</span><Link to={`/jobs/${job.id}`} aria-label={`View role: ${job.title}`}>View role <span aria-hidden="true">→</span></Link></div>
    </li>)}
  </ul>;
}
