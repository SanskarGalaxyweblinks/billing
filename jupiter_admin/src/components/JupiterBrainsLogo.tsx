
import React from 'react';

interface JupiterBrainsLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'light' | 'dark' | 'color';
  showText?: boolean;
  className?: string;
}

const JupiterBrainsLogo: React.FC<JupiterBrainsLogoProps> = ({ 
  size = 'md', 
  variant = 'color',
  showText = true,
  className = '' 
}) => {
  const sizeClasses = {
    sm: { logo: 'w-8 h-8', text: 'text-lg' },
    md: { logo: 'w-10 h-10', text: 'text-xl' },
    lg: { logo: 'w-12 h-12', text: 'text-2xl' },
    xl: { logo: 'w-16 h-16', text: 'text-3xl' }
  };

  const variantStyles = {
    light: { 
      text: 'text-white', 
      accent: 'text-blue-300',
      primaryColor: '#93C5FD',
      secondaryColor: '#DBEAFE'
    },
    dark: { 
      text: 'text-gray-900', 
      accent: 'text-blue-600',
      primaryColor: '#2563EB',
      secondaryColor: '#1E40AF'
    },
    color: { 
      text: 'text-gray-900', 
      accent: 'text-blue-600',
      primaryColor: '#2563EB',
      secondaryColor: '#1E40AF'
    }
  };

  const currentStyle = variantStyles[variant];

  return (
    <div className={`flex items-center space-x-3 ${className}`}>
      {/* Clean Professional Logo */}
      <div className={`${sizeClasses[size].logo} relative flex-shrink-0`}>
        <svg
          viewBox="0 0 40 40"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full"
        >
          {/* Main Planet Circle */}
          <circle
            cx="20"
            cy="20"
            r="16"
            fill="url(#planetGradient)"
            className="drop-shadow-md"
          />
          
          {/* Planet Rings */}
          <ellipse
            cx="20"
            cy="20"
            rx="22"
            ry="8"
            stroke={currentStyle.primaryColor}
            strokeWidth="1.5"
            fill="none"
            opacity="0.7"
          />
          
          {/* Neural Network Nodes */}
          <circle cx="12" cy="12" r="2" fill={currentStyle.primaryColor} opacity="0.8" />
          <circle cx="28" cy="12" r="2" fill={currentStyle.primaryColor} opacity="0.8" />
          <circle cx="12" cy="28" r="2" fill={currentStyle.primaryColor} opacity="0.8" />
          <circle cx="28" cy="28" r="2" fill={currentStyle.primaryColor} opacity="0.8" />
          
          {/* Connection Lines */}
          <path
            d="M12 12 L20 20 L28 12 M12 28 L20 20 L28 28"
            stroke={currentStyle.primaryColor}
            strokeWidth="1"
            opacity="0.6"
          />
          
          {/* Center Brain Symbol */}
          <circle cx="20" cy="20" r="3" fill="white" />
          <circle cx="20" cy="20" r="2" fill={currentStyle.primaryColor} />
          
          {/* Gradients */}
          <defs>
            <linearGradient id="planetGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={currentStyle.secondaryColor} />
              <stop offset="100%" stopColor={currentStyle.primaryColor} />
            </linearGradient>
          </defs>
        </svg>
      </div>
      
      {/* Improved Company Name Typography */}
      {showText && (
        <div className={`font-bold ${sizeClasses[size].text} ${currentStyle.text} tracking-tight`}>
          <span className="font-extrabold">Jupiter</span>
          <span className={`${currentStyle.accent} font-extrabold ml-0.5`}>Brains</span>
        </div>
      )}
    </div>
  );
};

export default JupiterBrainsLogo;