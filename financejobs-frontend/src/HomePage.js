import React, { useEffect, useState } from 'react';
import JobsList from './JobsList';
import Sidebar from './Sidebar';

function HomePage() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedJobType, setSelectedJobType] = useState("");
  const [selectedLocation, setSelectedLocation] = useState("");
  const [selectedCompany, setSelectedCompany] = useState("");
  const allLocations = [...new Set(jobs.map(job => job.location))].sort();
  const allCompanies = [...new Set(jobs.map(job => job.company?.name).filter(Boolean))].sort();

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
      job.company?.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.location.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.description.toLowerCase().includes(searchTerm.toLowerCase())) &&
    (selectedJobType ? job.job_type === selectedJobType : true) &&
    (selectedLocation ? job.location === selectedLocation : true) &&
    (selectedCompany ? job.company?.name === selectedCompany : true)
  );

  return (
    <div
      className="min-h-screen w-full bg-cover bg-center bg-no-repeat bg-fixed"
      style={{ backgroundImage: `url(${process.env.PUBLIC_URL}/seanpollock.jpg)` }}
    >
      <div className="bg-white/50 backdrop-blur-xs min-h-screen py-8 px-4 md:px-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="col-span-1">
          <Sidebar
            selectedJobType={selectedJobType}
            setSelectedJobType={setSelectedJobType}
            selectedLocation={selectedLocation}
            setSelectedLocation={setSelectedLocation}
            selectedCompany={selectedCompany}
            setSelectedCompany={setSelectedCompany}
            allLocations={allLocations}
            allCompanies={allCompanies}
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
      </div>
    </div>
  );
}

export default HomePage;
