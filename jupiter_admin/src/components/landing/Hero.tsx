import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import JupiterBrainsLogo from "@/components/JupiterBrainsLogo";

const Hero = () => {
  return (
    // Section background will be handled by LandingPage's light background
    <section className="py-20 px-4">
      <div className="container mx-auto text-center max-w-4xl">
        <div className="flex justify-center mb-8 animate-scale-in">
          <JupiterBrainsLogo size="xl" variant="color" showText={false} />
        </div>
        {/* Changed text colors for light theme */}
        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6 animate-fade-in-up animation-delay-200">
          Professional AI Analytics Platform
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto animate-fade-in-up animation-delay-400">
          Track, analyze, and optimize your AI usage with enterprise-grade
          analytics, real-time monitoring, and comprehensive billing management.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center animate-fade-in-up animation-delay-600">
          <Link to="/signup">
            {/* Adjusted button colors */}
            <Button
              size="lg"
              className="bg-blue-600 text-white text-lg px-8 py-3 hover:bg-blue-700 hover:scale-105 transition-all duration-200"
            >
              Get Started Today
            </Button>
          </Link>
          <Button
            size="lg"
            variant="outline"
            className="border-gray-300 text-gray-700 hover:bg-gray-100 hover:text-gray-900 text-lg px-8 py-3 hover:scale-105 transition-all duration-200"
          >
            Watch Demo
          </Button>
        </div>
      </div>
    </section>
  );
};

export default Hero;