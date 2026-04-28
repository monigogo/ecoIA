import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, RefreshCw } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { calculateSolar } from '../utils/solarCalculations';
import Navbar from '../components/Navbar';
import ProductionChart from '../components/ProductionChart';

export function ChartsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [calculation, setCalculation] = useState(null);
  const [activeTab, setActiveTab] = useState('production');

  useEffect(() => {
    if (user) {
      const result = calculateSolar({
        location: user.location || 'Madrid',
        monthlyConsumption: user.monthlyConsumption || 350,
        wantsBattery: true,
        years: 25,
      });
      setCalculation(result);
    }
  }, [user]);

  if (!calculation) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-solar-yellow/30 border-t-solar-yellow rounded-full animate-spin" />
      </div>
    );
  }

  const tabs = [
    { id: 'production', label: 'Producción 25 años' },
    { id: 'coverage', label: 'Cobertura vs Consumo' },
    { id: 'comparison', label: 'Comparativa' },
  ];

  return (
    <div className="min-h-screen bg-light">
      <Navbar />
      
      <main className="pt-20 pb-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 text-gray-600 hover:text-dark transition-colors mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              Volver al dashboard
            </button>
            
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h1 className="text-3xl font-bold text-dark">Gráficas y análisis</h1>
                <p className="text-gray-600 mt-1">
                  Visualiza la evolución de tu instalación solar a lo largo del tiempo
                </p>
              </div>
              
              <div className="flex items-center gap-3">
                <button
                  onClick={() => window.location.reload()}
                  className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span className="hidden sm:inline">Actualizar</span>
                </button>
                
                <button
                  onClick={() => alert('Función de exportación en desarrollo')}
                  className="flex items-center gap-2 px-4 py-2 bg-solar-yellow hover:bg-solar-yellow-dark text-dark font-medium rounded-lg transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span className="hidden sm:inline">Exportar</span>
                </button>
              </div>
            </div>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-xl p-4 border border-gray-200">
              <div className="text-sm text-gray-600 mb-1">Ubicación</div>
              <div className="text-lg font-bold text-dark">{calculation.location}</div>
            </div>
            
            <div className="bg-white rounded-xl p-4 border border-gray-200">
              <div className="text-sm text-gray-600 mb-1">Potencia</div>
              <div className="text-lg font-bold text-dark">{calculation.power} kWp</div>
            </div>
            
            <div className="bg-white rounded-xl p-4 border border-gray-200">
              <div className="text-sm text-gray-600 mb-1">Producción Año 1</div>
              <div className="text-lg font-bold text-eco-green">
                {calculation.production[1].toLocaleString()} kWh
              </div>
            </div>
            
            <div className="bg-white rounded-xl p-4 border border-gray-200">
              <div className="text-sm text-gray-600 mb-1">Cobertura</div>
              <div className="text-lg font-bold text-solar-yellow-dark">
                {calculation.coverage}%
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex flex-wrap gap-2 mb-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-3 rounded-xl font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-solar-yellow text-dark shadow-md'
                    : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Chart */}
          <div className="animate-fade-in">
            <ProductionChart data={calculation} type={activeTab} />
          </div>

          {/* Data Table */}
          <div className="mt-8 bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-bold text-dark">Datos detallados por año</h3>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-600">Año</th>
                    <th className="px-6 py-4 text-right text-sm font-semibold text-gray-600">Producción (kWh)</th>
                    <th className="px-6 py-4 text-right text-sm font-semibold text-gray-600">Degradación</th>
                    <th className="px-6 py-4 text-right text-sm font-semibold text-gray-600">vs Año 1</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {[1, 5, 10, 15, 20, 25].map((year) => {
                    const production = calculation.production[year];
                    const initialProduction = calculation.production[1];
                    const degradation = ((initialProduction - production) / initialProduction * 100).toFixed(1);
                    const vsInitial = Math.round((production / initialProduction) * 100);
                    
                    return (
                      <tr key={year} className="hover:bg-gray-50">
                        <td className="px-6 py-4 text-sm font-medium text-dark">Año {year}</td>
                        <td className="px-6 py-4 text-sm text-right text-dark">
                          {production.toLocaleString()}
                        </td>
                        <td className="px-6 py-4 text-sm text-right text-gray-600">
                          -{degradation}%
                        </td>
                        <td className="px-6 py-4 text-sm text-right">
                          <span className={`font-medium ${
                            vsInitial > 90 ? 'text-eco-green' : 
                            vsInitial > 85 ? 'text-solar-yellow-dark' : 'text-orange-500'
                          }`}>
                            {vsInitial}%
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Info Box */}
          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-xl p-6">
            <h4 className="font-semibold text-blue-900 mb-2">ℹ️ Sobre los cálculos</h4>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Los cálculos se basan en datos de irradiación solar de España.</li>
              <li>• La degradación del panel se estima en 0.5% anual (estándar de la industria).</li>
              <li>• La producción real puede variar según orientación, inclinación y sombras.</li>
              <li>• Se recomienda una visita técnica para una evaluación precisa.</li>
            </ul>
          </div>
        </div>
      </main>
    </div>
  );
}

export default ChartsPage;
