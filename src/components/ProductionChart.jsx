import React from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

export function ProductionChart({ data, type = 'production' }) {
  if (!data || !data.production) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 rounded-xl">
        <p className="text-gray-500">No hay datos disponibles</p>
      </div>
    );
  }

  // Prepare data for charts
  const productionData = Object.entries(data.production).map(([year, value]) => ({
    year: `Año ${year}`,
    produccion: value,
    consumo: data.annualConsumption,
  }));

  // Calculate coverage data
  const coverageData = productionData.map((item) => ({
    ...item,
    cubierto: Math.min(item.produccion, item.consumo),
    red: Math.max(0, item.consumo - item.produccion),
    excedente: Math.max(0, item.produccion - item.consumo),
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold text-dark mb-2">{label}</p>
          {payload.map((entry, index) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {entry.value.toLocaleString()} kWh
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (type === 'production') {
    return (
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h3 className="text-lg font-bold text-dark mb-2">Producción Solar Estimada (25 años)</h3>
        <p className="text-sm text-gray-500 mb-6">
          Evolución de la producción considerando una degradación del 0.5% anual
        </p>
        
        <ResponsiveContainer width="100%" height={350}>
          <AreaChart data={productionData}>
            <defs>
              <linearGradient id="colorProduction" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#E5B84C" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#E5B84C" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis 
              dataKey="year" 
              tick={{ fontSize: 12 }}
              interval={4}
              stroke="#6B7280"
            />
            <YAxis 
              tick={{ fontSize: 12 }}
              stroke="#6B7280"
              tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine 
              y={data.annualConsumption} 
              stroke="#5A7A5A" 
              strokeDasharray="5 5"
              label={{ value: 'Tu consumo', fill: '#5A7A5A', fontSize: 12 }}
            />
            <Area
              type="monotone"
              dataKey="produccion"
              name="Producción solar"
              stroke="#E5B84C"
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#colorProduction)"
            />
          </AreaChart>
        </ResponsiveContainer>
        
        <div className="mt-4 flex items-center justify-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-solar-yellow rounded" />
            <span className="text-gray-600">Producción solar</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-1 bg-eco-green border-dashed" />
            <span className="text-gray-600">Tu consumo anual</span>
          </div>
        </div>
      </div>
    );
  }

  if (type === 'coverage') {
    return (
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h3 className="text-lg font-bold text-dark mb-2">Cobertura vs Consumo</h3>
        <p className="text-sm text-gray-500 mb-6">
          Comparación entre tu consumo y la energía solar producida
        </p>
        
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={coverageData.slice(0, 10)}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis 
              dataKey="year" 
              tick={{ fontSize: 12 }}
              stroke="#6B7280"
            />
            <YAxis 
              tick={{ fontSize: 12 }}
              stroke="#6B7280"
              tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Bar dataKey="cubierto" name="Energía solar cubierta" stackId="a" fill="#E5B84C" />
            <Bar dataKey="red" name="Energía de la red" stackId="a" fill="#E5E7EB" />
            <Bar dataKey="excedente" name="Excedente (vertido)" fill="#5A7A5A" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (type === 'comparison') {
    return (
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h3 className="text-lg font-bold text-dark mb-2">Comparativa Anual</h3>
        <p className="text-sm text-gray-500 mb-6">
          Producción solar vs consumo a lo largo del tiempo
        </p>
        
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={productionData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis 
              dataKey="year" 
              tick={{ fontSize: 12 }}
              interval={4}
              stroke="#6B7280"
            />
            <YAxis 
              tick={{ fontSize: 12 }}
              stroke="#6B7280"
              tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Line
              type="monotone"
              dataKey="produccion"
              name="Producción solar"
              stroke="#E5B84C"
              strokeWidth={3}
              dot={{ fill: '#E5B84C', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line
              type="monotone"
              dataKey="consumo"
              name="Tu consumo"
              stroke="#5A7A5A"
              strokeWidth={3}
              strokeDasharray="5 5"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return null;
}

export default ProductionChart;
