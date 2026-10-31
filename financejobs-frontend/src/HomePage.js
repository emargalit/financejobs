import React, { useEffect, useState } from 'react';
import { Search, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import JobsList from './JobsList';
import Sidebar from './Sidebar';
import { api } from './api';

export default function HomePage() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [search, setSearch] = useState('');
  const [selectedJobType, setSelectedJobType] = useState('');
  const [selectedLocation, setSelectedLocation] = useState('');
  const [selectedCompany, setSelectedCompany] = useState('');
  const [filters, setFilters] = useState({ locations: [], companies: [] });
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [retry, setRetry] = useState(0);
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => { setSearch(searchTerm); setPage(1); }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  useEffect(() => {
    let active = true;
    api('jobs/filters/').then(data => { if (active) setFilters(data); }).catch(() => {});
    return () => { active = false; };
  }, [retry]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    const query = new URLSearchParams({ page, search, job_type: selectedJobType, location: selectedLocation, company: selectedCompany });
    api(`jobs/?${query}`, { signal: controller.signal })
      .then(data => { setJobs(data.results); setCount(data.count); })
      .catch(err => { if (err.name !== 'AbortError') setError('Unable to load jobs. Please try again.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page, search, selectedJobType, selectedLocation, selectedCompany, retry]);

  const choose = setter => value => { setter(value); setPage(1); };
  return (
    <div className="opportunities-page">
      <header className="opportunities-hero"><div><p className="section-eyebrow">SWISS FINANCE JOBS</p><h1>Your next chapter<br /><span>in Swiss finance.</span></h1><p className="hero-description">Explore opportunities at financial institutions across Switzerland. Find your role and apply directly with the employer.</p></div><Link to="/post-job" className="hero-employer-link">Hiring exceptional talent? <span>Post a job <ArrowUpRight size={15} /></span></Link></header>
      <div className="opportunities-body">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <button className="md:hidden text-left rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-semibold" aria-expanded={showFilters} aria-controls="job-filters" onClick={() => setShowFilters(!showFilters)}>{showFilters ? 'Hide filters' : 'Show filters'}</button>
          <aside id="job-filters" className={`col-span-1 ${showFilters ? 'block' : 'hidden'} md:block`}>
            <Sidebar selectedJobType={selectedJobType} setSelectedJobType={choose(setSelectedJobType)} selectedLocation={selectedLocation} setSelectedLocation={choose(setSelectedLocation)} selectedCompany={selectedCompany} setSelectedCompany={choose(setSelectedCompany)} allLocations={filters.locations} allCompanies={filters.companies} />
          </aside>
          <div className="md:col-span-3 min-w-0">
            <label htmlFor="job-search" className="sr-only">Search jobs</label>
            <div className="job-search-wrap"><Search size={20} aria-hidden="true" /><input id="job-search" type="search" placeholder="Search by role, institution or keyword" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} /></div>
            <div className="results-heading"><h2>Open opportunities {!loading && !error && <span>{count}</span>}</h2>{(selectedJobType || selectedLocation || selectedCompany || searchTerm) && <button onClick={() => { setSelectedJobType(''); setSelectedLocation(''); setSelectedCompany(''); setSearchTerm(''); setPage(1); }}>Clear filters</button>}</div>
            {error ? <div role="alert" className="p-5 bg-white rounded"><p>{error}</p><button onClick={() => setRetry(retry + 1)} className="text-blue-700 underline mt-2">Retry</button></div> : <JobsList jobs={jobs} loading={loading} />}
            {!loading && !error && count > 20 && <nav aria-label="Job pages" className="flex justify-between items-center bg-white p-4 mt-4 rounded">
              <button disabled={page === 1} onClick={() => setPage(page - 1)} className="disabled:opacity-40 text-blue-700">Previous</button>
              <span>Page {page} of {Math.ceil(count / 20)}</span>
              <button disabled={page * 20 >= count} onClick={() => setPage(page + 1)} className="disabled:opacity-40 text-blue-700">Next</button>
            </nav>}
          </div>
        </div>
      </div>
    </div>
  );
}
