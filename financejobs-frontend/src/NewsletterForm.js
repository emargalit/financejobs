import React, { useState } from 'react';
import { toast } from 'react-toastify';

function NewsletterForm() {
  const [email, setEmail] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!email.includes("@")) {
      toast.error("Please enter a valid email address.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/api/newsletter/subscribe/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email }),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (response.ok) {
        toast.success("You've been subscribed!");
        setEmail("");
        setSuccess(true);
      } else {
        toast.error(data.detail || "Subscription failed.");
      }
    } catch (error) {
      console.error("Newsletter subscription error:", error);
      toast.error("An error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white p-8 rounded-2xl shadow-xl max-w-lg mx-auto mt-10">
      <h2 className="text-2xl font-bold text-center text-gray-800 mb-6 leading-relaxed">
        Subscribe to our weekly newsletter: <br />
        <span className="text-blue-800">
          Get the best finance jobs straight to your inbox!
        </span>
      </h2>

      {/* ✅ Inline success message */}
      {success && (
        <div className="bg-green-100 text-green-800 p-3 rounded-lg mb-4 text-center">
          ✅ Successfully subscribed! Check your inbox soon.
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Enter your email address"
          className="w-full p-3 border border-gray-300 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-600"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={success}
        />

        <button
          type="submit"
          disabled={success || loading}
          className={`w-full py-3 rounded-lg font-semibold transition duration-200 ${
            success
              ? "bg-green-500 text-white cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-700 hover:shadow-md"
          }`}
        >
          {loading
            ? "Subscribing..."
            : success
            ? "Subscribed ✓"
            : "Subscribe"}
        </button>
      </form>
    </div>
  );
}

export default NewsletterForm;