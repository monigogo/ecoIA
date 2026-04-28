import React from 'react';
import logo from '../assets/imagen.png';

export function Logo({ size = 'large', className = '' }) {
  const isLarge = size === 'large';
  
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Logo Image */}
      <img 
        src={logo} 
        alt="SolarLife AI Logo" 
        className={isLarge ? 'h-20 w-20 object-contain mx-auto' : 'h-10 w-10 object-contain'} 
      />
      
      {/* Text */}
      <div className="flex flex-col">
        <span className={`font-bold tracking-tight ${isLarge ? 'text-3xl' : 'text-xl'}`}>
          <span className="text-dark">Solar</span>
          <span className="text-eco-green">Life</span>
          <span className="text-dark"> AI</span>
        </span>
        {isLarge && (
          <span className="text-sm text-gray-500 tracking-wider uppercase">
            Planifica tu energía. Transforma tu futuro.
          </span>
        )}
      </div>
    </div>
  );
}

export default Logo;
