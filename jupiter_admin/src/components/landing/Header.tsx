import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import JupiterBrainsLogo from "@/components/JupiterBrainsLogo";

const Header = () => {
  return (
    // Changed to light theme: white background with a subtle shadow
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white/80 backdrop-blur-sm animate-fade-in">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div className="animate-slide-in-left">
          <JupiterBrainsLogo size="lg" variant="color" />
        </div>
        <div className="flex items-center space-x-4 animate-slide-in-right">
          <Link to="/login">
            {/* Adjusted button for light theme */}
            <Button
              variant="ghost"
              className="text-gray-600 hover:bg-gray-100 hover:text-gray-900 hover:scale-105 transition-all duration-200"
            >
              Sign In
            </Button>
          </Link>
          <Link to="/signup">
            {/* Adjusted button for light theme */}
            <Button className="bg-blue-600 text-white hover:bg-blue-700 hover:scale-105 transition-all duration-200">
              Get Started
            </Button>
          </Link>
        </div>
      </div>
    </header>
  );
};

export default Header;