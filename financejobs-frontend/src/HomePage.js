import React, { useEffect, useState } from 'react';
import JobsList from './JobsList';
import 'react-toastify/dist/ReactToastify.css';

function HomePage() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  const fetchJobs = () => {
    fetch(`${process.env.REACT_APP_API_URL}/api/jobs/`)
      .then(response => response.json())
      .then(data => {
        setJobs(data);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching jobs:', error);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const filteredJobs = jobs.filter(job =>
    job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    job.company_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    job.location.toLowerCase().includes(searchTerm.toLowerCase()) ||
    job.description.toLowerCase().includes(searchTerm.toLowerCase()) 
  );

  return (
    <div>
        <input
        type="text"
        placeholder="Search jobs..."
        className="w-full mb-4 p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-800"
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        />
        <JobsList jobs={filteredJobs} loading={loading} />
    </div>
  );
}

export default HomePage;