import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const CTA = () => {
  return (
    // Changed background to a light gray
    <section className="py-20 px-4 bg-gray-50 animate-fade-in-up">
      <div className="container mx-auto max-w-4xl text-center">
        {/* Changed text colors */}
        <h2 className="text-3xl font-bold text-gray-900 mb-4 animate-fade-in-up animation-delay-200">
          Ready to optimize your AI usage?
        </h2>
        <p className="text-gray-600 mb-8 text-lg animate-fade-in-up animation-delay-400">
          Join thousands of companies using JupiterBrains to track and optimize
          their AI investments.
        </p>
        <div className="animate-fade-in-up animation-delay-600">
          <Link to="/signup">
            {/* Adjusted button colors */}
            <Button
              size="lg"
              className="bg-blue-600 text-white hover:bg-blue-700 text-lg px-8 py-3 hover:scale-105 transition-all duration-200"
            >
              Start Using JupiterBrains
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
};

export default CTA;