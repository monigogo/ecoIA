import React from 'react';
import solarBot from '../assets/SolarBot.png';

export function SolarBotAvatar({ size = 32, className = '' }) {
  return (
    <img
      src={solarBot}
      alt="SolarBot"
      width={size}
      height={size}
      className={`object-contain ${className}`}
    />
  );
}

export default SolarBotAvatar;
