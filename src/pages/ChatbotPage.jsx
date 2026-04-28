import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles } from 'lucide-react';
import Navbar from '../components/Navbar';
import Chatbot from '../components/Chatbot';

export function ChatbotPage() {
  const navigate = useNavigate();
  const [lastCalculation, setLastCalculation] = useState(null);

  const handleCalculationComplete = (result) => {
    setLastCalculation(result);
  };

  return (
    <div className="min-h-screen bg-light">
      <Navbar />
      
      <main className="pt-20 pb-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 text-gray-600 hover:text-dark transition-colors mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              Volver al dashboard
            </button>
            
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h1 className="text-3xl font-bold text-dark flex items-center gap-3">
                  Asistente SolarLife AI
                  <span className="inline-flex items-center gap-1 px-3 py-1 bg-solar-yellow/20 text-solar-yellow-dark text-sm font-medium rounded-full">
                    <Sparkles className="w-4 h-4" />
                    AI Powered
                  </span>
                </h1>
                <p className="text-gray-600 mt-1">
                  Cuéntanos sobre tu hogar y consumo, y te calcularemos la instalación solar ideal.
                </p>
              </div>
            </div>
          </div>

          {/* Chatbot */}
          <div className="h-[calc(100vh-280px)] min-h-[500px]">
            <Chatbot onCalculationComplete={handleCalculationComplete} />
          </div>

          {/* Tips */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl p-4 border border-gray-200">
              <h3 className="font-semibold text-dark mb-2">📍 Ubicación</h3>
              <p className="text-sm text-gray-600">
                Indica tu ciudad o comunidad autónoma. La producción solar varía según la zona.
              </p>
            </div>
            
            <div className="bg-white rounded-xl p-4 border border-gray-200">
              <h3 className="font-semibold text-dark mb-2">⚡ Consumo</h3>
              <p className="text-sm text-gray-600">
                Mira tu factura de la luz. El consumo mensual suele estar entre 200-600 kWh.
              </p>
            </div>
            
            <div className="bg-white rounded-xl p-4 border border-gray-200">
              <h3 className="font-semibold text-dark mb-2">🔋 Batería</h3>
              <p className="text-sm text-gray-600">
                La batería te permite almacenar excedentes y usar energía solar por la noche.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default ChatbotPage;
