import React from "react";
import { Link } from "react-router-dom";
import JupiterBrainsLogo from "@/components/JupiterBrainsLogo";

const Footer = () => {
  return (
    // Changed background to a neutral light color
    <footer className="bg-white text-gray-600 border-t border-gray-200 py-12 px-4 animate-fade-in">
      <div className="container mx-auto max-w-6xl">
        <div className="grid md:grid-cols-4 gap-8">
          <div className="animate-fade-in-up animation-delay-200">
            <JupiterBrainsLogo size="md" variant="color" className="mb-4" />
            <p className="text-gray-600">
              Professional AI analytics and usage tracking for modern
              businesses.
            </p>
          </div>
          <div className="animate-fade-in-up animation-delay-400">
            <h4 className="font-semibold mb-4 text-gray-900">Product</h4>
            <ul className="space-y-2 text-gray-600">
              <li>
                <Link
                  to="#"
                  className="hover:text-blue-600 transition-colors duration-200"
                >
                  Analytics
                </Link>
              </li>
              <li>
                <Link
                  to="#"
                  className="hover:text-blue-600 transition-colors duration-200"
                >
                  Billing
                </Link>
              </li>
              <li>
                <Link
                  to="#"
                  className="hover:text-blue-600 transition-colors duration-200"
                >
                  API Management
                </Link>
              </li>
              <li>
                <Link
                  to="#"
                  className="hover:text-blue-600 transition-colors duration-200"
                >
                  Security
                </Link>
              </li>
            </ul>
          </div>
          <div className="animate-fade-in-up animation-delay-600">
            <h4 className="font-semibold mb-4 text-gray-900">Company</h4>
            <ul className="space-y-2 text-gray-600">
              <li>
                <Link
                  to="#"
                  className="hover:text-blue-600 transition-colors duration-200"
                >
                  About
                </Link>
              </li>
              <li>
                <Link
                  to="#"
                  className="hover:text-blue-600 transition-colors duration-200"
                >
                  Blog
                </Link>
              </li>
              <li>
                <Link
                  to="#"
                  className="hover:text-blue-600 transition-colors duration-200"
                >
                  Careers
                </Link>
              </li>
              <li>
                <Link
                  to="#"
                  className="hover:text-blue-600 transition-colors duration-200"
                >
                  Contact
                </Link>
              </li>
            </ul>
          </div>
          <div className="animate-fade-in-up animation-delay-800">
            <h4 className="font-semibold mb-4 text-gray-900">Support</h4>
            <ul className="space-y-2 text-gray-600">
              <li>
                <Link
                  to="#"
                  className="hover:text-blue-600 transition-colors duration-200"
                >
                  Documentation
                </Link>
              </li>
              <li>
                <Link
                  to="#"
                  className="hover:text-blue-600 transition-colors duration-200"
                >
                  Help Center
                </Link>
              </li>
              <li>
                <Link
                  to="#"
                  className="hover:text-blue-600 transition-colors duration-200"
                >
                  Status
                </Link>
              </li>
              <li>
                <Link
                  to="#"
                  className="hover:text-blue-600 transition-colors duration-200"
                >
                  Security
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-gray-200 mt-8 pt-8 text-center text-gray-500 animate-fade-in-up animation-delay-1000">
          <p>&copy; 2024 JupiterBrains. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;