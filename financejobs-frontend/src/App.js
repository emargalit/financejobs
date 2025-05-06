import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import HomePage from './HomePage';
import JobForm from './JobForm';
import 'react-toastify/dist/ReactToastify.css';

function App() {
  return (
    <Router>
      <div className="flex flex-col h-screen">
        <nav className="bg-white shadow sticky top-0 z-50">
          <div className="max-w-6xl mx-auto px-4 py-3 flex justify-between items-center">
            <h1 className="text-2xl font-bold text-blue-800">Swiss Finance Jobs</h1>
            <div className="space-x-4">
              <Link to="/" className="text-gray-700 hover:text-blue-600 hover:underline">Home</Link>
              <Link to="/post-job" className="text-gray-700 hover:text-blue-600 hover:underline">Post a Job</Link>
            </div>
          </div>
        </nav>

        <div className="flex-1 overflow-y-auto bg-gray-100 px-4 py-6">
          <div className="max-w-6xl mx-auto space-y-8">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/post-job" element={<JobForm />} />
            </Routes>
          </div>
        </div>
      </div>
    </Router>
  );
}

export default App;
