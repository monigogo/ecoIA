import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export function StatCard({ 
  title, 
  value, 
  unit = '', 
  subtitle = '', 
  icon: Icon,
  trend = null,
  trendValue = '',
  color = 'yellow',
  large = false 
}) {
  const colorClasses = {
    yellow: 'bg-solar-yellow/10 border-solar-yellow/30 text-solar-yellow-dark',
    green: 'bg-eco-green/10 border-eco-green/30 text-eco-green-dark',
    blue: 'bg-blue-100 border-blue-300 text-blue-700',
    gray: 'bg-gray-100 border-gray-300 text-gray-700',
  };

  const iconBgClasses = {
    yellow: 'bg-solar-yellow/20 text-solar-yellow-dark',
    green: 'bg-eco-green/20 text-eco-green-dark',
    blue: 'bg-blue-200 text-blue-700',
    gray: 'bg-gray-200 text-gray-700',
  };

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;

  return (
    <div className={`
      relative overflow-hidden rounded-2xl border p-6 card-hover
      ${colorClasses[color] || colorClasses.gray}
      ${large ? 'col-span-2 row-span-2' : ''}
    `}>
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-white/20 rounded-full -mr-16 -mt-16 blur-2xl" />
      
      <div className="relative">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className={`
            p-3 rounded-xl
            ${iconBgClasses[color] || iconBgClasses.gray}
          `}>
            {Icon && <Icon className="w-6 h-6" />}
          </div>
          
          {trend && (
            <div className={`flex items-center gap-1 text-sm font-medium ${
              trend === 'up' ? 'text-eco-green' : trend === 'down' ? 'text-red-500' : 'text-gray-500'
            }`}>
              <TrendIcon className="w-4 h-4" />
              <span>{trendValue}</span>
            </div>
          )}
        </div>

        {/* Value */}
        <div className={`font-bold text-dark mb-1 ${large ? 'text-5xl' : 'text-3xl'}`}>
          {value}
          {unit && <span className="text-lg font-medium ml-1">{unit}</span>}
        </div>

        {/* Title */}
        <div className={`font-medium text-dark/80 mb-1 ${large ? 'text-lg' : 'text-base'}`}>
          {title}
        </div>

        {/* Subtitle */}
        {subtitle && (
          <div className="text-sm text-dark/60">
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
}

export default StatCard;
