import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

function JobDetail() {
  const { id } = useParams();
  const [job, setJob] = useState(null);

  useEffect(() => {
    fetch(`${process.env.REACT_APP_API_URL}/api/jobs/${id}/`)
      .then(res => res.json())
      .then(data => setJob(data));
  }, [id]);

  if (!job) return <p>Loading job...</p>;

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
            className="prose max-w-none"
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
