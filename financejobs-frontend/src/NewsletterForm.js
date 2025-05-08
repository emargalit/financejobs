import React, { useState } from 'react';
import { toast } from 'react-toastify';

function NewsletterForm() {
  const [email, setEmail] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!email.includes("@")) {
      toast.error("Please enter a valid email address.");
      return;
    }

    toast.success("You've been subscribed!");
    setEmail("");
  };

  return (
    <div className="bg-white p-8 rounded-2xl shadow-xl max-w-lg mx-auto mt-10">
      <h2 className="text-2xl font-bold text-center text-gray-800 mb-6 leading-relaxed">
        Subscribe to our weekly newsletter: <br />
        <span className="text-blue-800">
          Get the best finance jobs straight to your inbox!
        </span>
      </h2>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Enter your email address"
          className="w-full p-3 border border-gray-300 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-600"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold transition duration-200 hover:bg-blue-700 hover:shadow-md"
        >
          Subscribe
        </button>
      </form>
    </div>
  );
}

export default NewsletterForm;
