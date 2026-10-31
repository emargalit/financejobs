import React, { useEffect, useState } from 'react';
import { api } from './api';
import { Link, useParams } from 'react-router-dom';

function JobDetail() {
  const { id } = useParams();
  const [job, setJob] = useState(null);

  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setJob(null); setError('');
    api(`jobs/${id}/`, { signal: controller.signal })
      .then(setJob)
      .catch(err => { if (err.name !== 'AbortError') setError(err.message); });
    return () => controller.abort();
  }, [id]);
  if (error) return <div role="alert"><p>This job could not be loaded. It may have expired.</p><p>{error}</p><Link to="/" className="underline text-blue-700">Browse current jobs</Link></div>;
  if (!job) return <p role="status">Loading job...</p>;

  return (
    <div
      className="min-h-screen bg-cover bg-center bg-no-repeat"
      style={{ backgroundImage: "url('/seanpollock.jpg')" }}
    >
      <div className="bg-white/50 backdrop-blur-xs min-h-screen py-8 px-4 md:px-10">
        <div className="p-6 max-w-3xl mx-auto bg-white rounded-md shadow-md mt-6">
          <h1 className="text-2xl font-bold mb-2">{job.title}</h1>
          <p className="text-gray-700 mb-2">{job.company?.name} — {job.location}</p>
          <p className="mb-4 text-sm text-gray-500">
            Posted on {new Date(job.posted_at).toLocaleDateString("de-CH", {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            })}
          </p>
          <div
            className="job-description max-w-none"
            dangerouslySetInnerHTML={{ __html: job.description }}
          />
          <a href={job.apply_link} target="_blank" rel="noreferrer">
            <button className="mt-6 bg-blue-700 text-white px-4 py-2 rounded hover:bg-blue-800">
              Apply Now
            </button>
          </a>
        </div>
      </div>
    </div>
  );
}

export default JobDetail;
