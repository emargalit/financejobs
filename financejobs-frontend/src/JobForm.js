import React, { useState, useRef } from 'react';
import { toast } from 'react-toastify';
import { Link } from 'react-router-dom';

function Spinner() {
  return (
    <svg
      className="animate-spin h-5 w-5 mr-2 text-white inline"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v8z"
      />
    </svg>
  );
}

function JobForm({ onJobPosted }) {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    company_name: '',
    contact_email: '',
    location: '',
    salary: '',
    apply_link: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const formRef = useRef(null);

  const handleChange = (e) => {
    setFormData((prevState) => ({
      ...prevState,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    const loadingToastId = toast.loading('Sending your request...');

    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/api/job-inquiries/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(formData),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (response.ok) {
        toast.success('Your job advertisement request has been sent!', {
          id: loadingToastId,
        });

        formRef.current?.scrollIntoView({ behavior: 'smooth' });

        setFormData({
          title: '',
          description: '',
          company_name: '',
          contact_email: '',
          location: '',
          salary: '',
          apply_link: '',
        });

        onJobPosted?.();
      } else {
        toast.error(data.detail || 'Failed to send request.', {
          id: loadingToastId,
        });
      }
    } catch (error) {
      console.error('Error sending request:', error);
      toast.error('An error occurred.', { id: loadingToastId });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4 bg-white shadow rounded">
      <Link to="/" className="text-blue-600 hover:underline mb-4 block">
        ← Back to Jobs
      </Link>

      <div ref={formRef} className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-2xl font-semibold mb-4">Post a New Job</h2>

        <div className="bg-white border border-gray-200 p-5 rounded-lg shadow-sm mb-6">
          <h3 className="text-xl font-semibold mb-2">
            Job Advertisement Pricing
          </h3>

          <div className="flex items-center justify-between">
            <span className="text-gray-700">
              Standard Listing (valid for 30 days)
            </span>
            <span className="text-2xl font-bold text-blue-600">390 CHF</span>
          </div>

          <p className="text-sm text-gray-500 mt-2">
            Contact us at{" "}
            <a
              href="mailto:elene.margalit@gmail.com"
              className="text-blue-600 hover:underline"
            >
              elene.margalit@gmail.com
            </a>{" "}
            for package deals and premium placements.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            name="title"
            value={formData.title}
            onChange={handleChange}
            placeholder="Job Title"
            required
            className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400"
          />

          <input
            name="company_name"
            value={formData.company_name}
            onChange={handleChange}
            placeholder="Company Name"
            required
            className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400"
          />

          <input
            type="email"
            name="contact_email"
            value={formData.contact_email}
            onChange={handleChange}
            placeholder="Your Email Address"
            required
            className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400"
          />

          <input
            name="location"
            value={formData.location}
            onChange={handleChange}
            placeholder="Location"
            required
            className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          
          <input
            name="salary"
            value={formData.salary}
            onChange={handleChange}
            placeholder="Salary (optional)"
            className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400"
          />

          <input
            name="apply_link"
            value={formData.apply_link}
            onChange={handleChange}
            placeholder="Apply Link"
            required
            className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400"
          />

          <textarea
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Job Description"
            required
            className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400"
          />

          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold p-3 rounded-md flex justify-center items-center transition duration-300 disabled:opacity-50"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Spinner />
                Sending...
              </>
            ) : (
              'Send Request'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default JobForm;