import React, { useEffect, useState } from 'react';
import JobsList from './JobsList';
import Sidebar from './Sidebar';

function HomePage() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedJobType, setSelectedJobType] = useState("");
  const [selectedLocation, setSelectedLocation] = useState("");
  const allLocations = [...new Set(jobs.map(job => job.location))].sort();

  useEffect(() => {
    fetch(`${process.env.REACT_APP_API_URL}/api/jobs/`)
      .then(res => res.json())
      .then(data => {
        setJobs(data);
        setLoading(false);
      });
  }, []);
  
  const filteredJobs = jobs.filter(job =>
    (job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.company_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.location.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.description.toLowerCase().includes(searchTerm.toLowerCase())) &&
    (selectedJobType ? job.job_type === selectedJobType : true) &&
    (selectedLocation ? job.location === selectedLocation : true)
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
      <div className="col-span-1">
      <Sidebar
        selectedJobType={selectedJobType}
        setSelectedJobType={setSelectedJobType}
        selectedLocation={selectedLocation}
        setSelectedLocation={setSelectedLocation}
        allLocations={allLocations}
      />
      </div>
      <div className="col-span-3">
        <input
          type="text"
          placeholder="Search jobs..."
          className="w-full mb-4 p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-800"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        <JobsList jobs={filteredJobs} loading={loading} />
      </div>
    </div>
  );
}

export default HomePage;
