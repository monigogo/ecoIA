import React, { useState, useEffect } from 'react';
import { Sun, Home, Battery, Upload, Download, Activity } from 'lucide-react';

export function LiveMonitor() {
  const [data, setData] = useState({
    solarProduction: 3.2,
    homeConsumption: 2.1,
    batteryLevel: 78,
    gridExport: 1.1,
    gridImport: 0.0,
    systemStatus: 'óptimo'
  });

  const [history, setHistory] = useState(Array(20).fill(0).map((_, i) => ({
    time: i,
    solar: 2.5 + Math.random() * 2,
    consumption: 1.5 + Math.random() * 1.5
  })));

  useEffect(() => {
    const interval = setInterval(() => {
      setData(prev => {
        const newSolar = Math.max(0, 2.5 + Math.random() * 2.5 + (Math.sin(Date.now() / 10000) * 1.5));
        const newConsumption = Math.max(0.5, 1.2 + Math.random() * 1.8);
        const batteryDelta = (newSolar - newConsumption) * 0.1;
        const newBattery = Math.min(100, Math.max(0, prev.batteryLevel + batteryDelta));
        
        let newGridExport = 0;
        let newGridImport = 0;
        
        if (newSolar > newConsumption && newBattery >= 95) {
          newGridExport = newSolar - newConsumption;
        } else if (newSolar < newConsumption && newBattery <= 20) {
          newGridImport = newConsumption - newSolar;
        }
        
        let status = 'óptimo';
        if (newBattery < 15 || newSolar < 0.5) status = 'alerta';
        else if (newSolar < 1.5) status = 'bajo rendimiento';
        
        return {
          solarProduction: parseFloat(newSolar.toFixed(2)),
          homeConsumption: parseFloat(newConsumption.toFixed(2)),
          batteryLevel: Math.round(newBattery),
          gridExport: parseFloat(newGridExport.toFixed(2)),
          gridImport: parseFloat(newGridImport.toFixed(2)),
          systemStatus: status
        };
      });

      setHistory(prev => {
        const newPoint = {
          time: prev[prev.length - 1].time + 1,
          solar: data.solarProduction,
          consumption: data.homeConsumption
        };
        return [...prev.slice(1), newPoint];
      });
    }, 2000);

    return () => clearInterval(interval);
  }, [data.solarProduction, data.homeConsumption, data.batteryLevel]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'óptimo': return 'text-eco-green bg-eco-green/10';
      case 'alerta': return 'text-red-500 bg-red-50';
      case 'bajo rendimiento': return 'text-solar-yellow-dark bg-solar-yellow/10';
      default: return 'text-gray-500 bg-gray-100';
    }
  };

  const maxValue = Math.max(...history.map(h => Math.max(h.solar, h.consumption)), 5);

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
      <div className="bg-gradient-to-r from-eco-green to-eco-green-light p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-white" />
            <h3 className="font-bold text-white text-lg">Monitor en tiempo real</h3>
          </div>
          <div className={`px-3 py-1 rounded-full text-sm font-semibold ${getStatusColor(data.systemStatus)}`}>
            {data.systemStatus.toUpperCase()}
          </div>
        </div>
      </div>

      <div className="p-6">
        <p className="text-sm text-gray-600 mb-6">
          Esta vista está pensada para usuarios que ya tienen una instalación solar y quieren ver cómo se está usando la energía en tiempo real.
        </p>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
          <div className="bg-solar-yellow/10 rounded-xl p-4 text-center">
            <div className="w-10 h-10 bg-solar-yellow/20 rounded-lg flex items-center justify-center mx-auto mb-2">
              <Sun className="w-5 h-5 text-solar-yellow-dark" />
            </div>
            <div className="text-2xl font-bold text-dark">{data.solarProduction}</div>
            <div className="text-xs text-gray-600">kW producción solar</div>
          </div>

          <div className="bg-blue-50 rounded-xl p-4 text-center">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-2">
              <Home className="w-5 h-5 text-blue-600" />
            </div>
            <div className="text-2xl font-bold text-dark">{data.homeConsumption}</div>
            <div className="text-xs text-gray-600">kW consumo hogar</div>
          </div>

          <div className="bg-eco-green/10 rounded-xl p-4 text-center">
            <div className="w-10 h-10 bg-eco-green/20 rounded-lg flex items-center justify-center mx-auto mb-2">
              <Battery className="w-5 h-5 text-eco-green-dark" />
            </div>
            <div className="text-2xl font-bold text-dark">{data.batteryLevel}%</div>
            <div className="text-xs text-gray-600">batería</div>
          </div>

          <div className="bg-green-50 rounded-xl p-4 text-center">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-2">
              <Upload className="w-5 h-5 text-green-600" />
            </div>
            <div className="text-2xl font-bold text-dark">{data.gridExport}</div>
            <div className="text-xs text-gray-600">kW a la red</div>
          </div>

          <div className="bg-orange-50 rounded-xl p-4 text-center">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center mx-auto mb-2">
              <Download className="w-5 h-5 text-orange-600" />
            </div>
            <div className="text-2xl font-bold text-dark">{data.gridImport}</div>
            <div className="text-xs text-gray-600">kW de la red</div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-xl p-4">
          <h4 className="text-sm font-semibold text-dark mb-3">Actividad últimos minutos</h4>
          <div className="h-32 flex items-end gap-1">
            {history.map((point, i) => (
              <div key={i} className="flex-1 flex flex-col justify-end gap-1">
                <div 
                  className="w-full bg-solar-yellow rounded-t"
                  style={{ height: `${(point.solar / maxValue) * 100}%` }}
                />
                <div 
                  className="w-full bg-blue-400 rounded-t"
                  style={{ height: `${(point.consumption / maxValue) * 100}%` }}
                />
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-2 text-xs text-gray-500">
            <span>-20s</span>
            <span>-10s</span>
            <span>Ahora</span>
          </div>
          <div className="flex gap-4 mt-3 justify-center">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-solar-yellow rounded" />
              <span className="text-xs text-gray-600">Producción</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-400 rounded" />
              <span className="text-xs text-gray-600">Consumo</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LiveMonitor;
