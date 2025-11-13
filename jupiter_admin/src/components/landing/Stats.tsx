import React from "react";

const Stats = () => {
  return (
    // Changed section background to white
    <section className="py-20 px-4 bg-white">
      <div className="container mx-auto max-w-4xl text-center">
        {/* Changed text colors */}
        <h2 className="text-3xl font-bold text-gray-900 mb-12 animate-fade-in-up">
          Trusted by leading companies
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div className="animate-fade-in-up animation-delay-200 hover:scale-105 transition-transform duration-200">
            <div className="text-3xl font-bold text-blue-600 mb-2 animate-counter">
              99.9%
            </div>
            <div className="text-gray-600">Uptime</div>
          </div>
          <div className="animate-fade-in-up animation-delay-400 hover:scale-105 transition-transform duration-200">
            <div className="text-3xl font-bold text-blue-600 mb-2 animate-counter">
              500K+
            </div>
            <div className="text-gray-600">API Calls/Day</div>
          </div>
          <div className="animate-fade-in-up animation-delay-600 hover:scale-105 transition-transform duration-200">
            <div className="text-3xl font-bold text-blue-600 mb-2 animate-counter">
              1000+
            </div>
            <div className="text-gray-600">Companies</div>
          </div>
          <div className="animate-fade-in-up animation-delay-800 hover:scale-105 transition-transform duration-200">
            <div className="text-3xl font-bold text-blue-600 mb-2 animate-counter">
              24/7
            </div>
            <div className="text-gray-600">Support</div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Stats;