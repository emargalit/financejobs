import React from 'react';
import { Link } from 'react-router-dom';

function JobsList({ jobs, loading }) {
  if (loading) return <p>Loading jobs...</p>;

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-semibold mb-4">Finance Jobs in Switzerland</h2>
      <ul className="space-y-6">
        {[...jobs].sort((a, b) => new Date(b.posted_at) - new Date(a.posted_at)).map(job => (
          <li key={job.id} className="bg-white p-5 rounded-lg shadow hover:shadow-md transition">
            <Link
              to={`/jobs/${job.id}`}
              className="text-xl font-bold text-blue-700 hover:underline"
            >
              {job.title}
            </Link>
            <p className="text-sm text-gray-600">{job.company?.name}</p>
            {job.job_type && (
              <span className="inline-block mt-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                {job.job_type}
              </span>
            )}
            <p className="text-gray-400 text-sm mt-2">
              Posted on {new Date(job.posted_at).toLocaleDateString("de-CH", {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
              })}
            </p>
            <Link
              to={`/jobs/${job.id}`}
              className="inline-block mt-3 text-sm text-blue-600 hover:underline"
            >
              Apply
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );  
}

export default JobsList;
