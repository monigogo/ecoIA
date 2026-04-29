import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ExternalLink, AlertCircle, CheckCircle, MapPin, Euro, FileText, Home } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getSubsidies, getRegion } from '../utils/solarCalculations';
import Navbar from '../components/Navbar';

export function SubsidiesPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [region, setRegion] = useState('');
  const [subsidies, setSubsidies] = useState(null);

  useEffect(() => {
    if (user?.location) {
      const detectedRegion = getRegion(user.location);
      setRegion(detectedRegion);
      setSubsidies(getSubsidies(detectedRegion));
    } else {
      setRegion('madrid');
      setSubsidies(getSubsidies('madrid'));
    }
  }, [user]);

  const commonSubsidies = [
    {
      title: 'Deducción en IRPF',
      description: 'Deducción del 20% en la cuota íntegra del IRPF para instalaciones de autoconsumo residencial.',
      amount: 'Hasta 20%',
      icon: Euro,
      color: 'green',
    },
    {
      title: 'Bonificación IBI',
      description: 'Reducción del Impuesto de Bienes Inmuebles durante varios años por instalar placas solares.',
      amount: '50% durante 4-10 años',
      icon: Home,
      color: 'yellow',
    },
    {
      title: 'ICIO Bonificado',
      description: 'Bonificación en el Impuesto sobre Construcciones, Instalaciones y Obras.',
      amount: 'Hasta 95%',
      icon: FileText,
      color: 'blue',
    },
  ];

  const colorClasses = {
    green: 'bg-eco-green/10 border-eco-green/30 text-eco-green-dark',
    yellow: 'bg-solar-yellow/10 border-solar-yellow/30 text-solar-yellow-dark',
    blue: 'bg-blue-100 border-blue-300 text-blue-700',
  };

  if (!subsidies) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-solar-yellow/30 border-t-solar-yellow rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-light">
      <Navbar />
      
      <main className="pt-20 pb-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto">
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
                <h1 className="text-3xl font-bold text-dark">Subvenciones disponibles</h1>
                <p className="text-gray-600 mt-1">
                  Ayudas y beneficios fiscales para instalaciones de autoconsumo solar
                </p>
              </div>
              
              <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-xl shadow-sm border border-gray-200">
                <MapPin className="w-5 h-5 text-eco-green" />
                <span className="font-medium text-dark">{subsidies.name}</span>
              </div>
            </div>
          </div>

          {/* Warning */}
          <div className="mb-8 bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-amber-900 mb-1">Información orientativa</h3>
              <p className="text-sm text-amber-800">
                Las subvenciones y ayudas pueden cambiar. Te recomendamos verificar siempre la información 
                vigente en la web oficial de tu comunidad autónoma o ayuntamiento antes de tomar decisiones.
              </p>
            </div>
          </div>

          {/* Regional Subsidies */}
          <div className="mb-8">
            <h2 className="text-xl font-bold text-dark mb-4">
              Ayudas en {subsidies.name}
            </h2>
            
            <div className="space-y-4">
              {subsidies.aids.map((aid, index) => (
                <div
                  key={index}
                  className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm flex items-start gap-4"
                >
                  <div className="w-12 h-12 bg-solar-yellow/20 rounded-xl flex items-center justify-center flex-shrink-0">
                    <CheckCircle className="w-6 h-6 text-solar-yellow-dark" />
                  </div>
                  <div className="flex-1">
                    <p className="text-dark font-medium">{aid}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Links */}
            {subsidies.links && subsidies.links.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-3">
                {subsidies.links.map((link, index) => (
                  <a
                    key={index}
                    href={link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-eco-green/10 text-eco-green-dark rounded-lg hover:bg-eco-green/20 transition-colors"
                  >
                    <span className="text-sm font-medium">Más información oficial</span>
                    <ExternalLink className="w-4 h-4" />
                  </a>
                ))}
              </div>
            )}
          </div>

          {/* Common Subsidies */}
          <div className="mb-8">
            <h2 className="text-xl font-bold text-dark mb-4">
              Beneficios fiscales generales (España)
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {commonSubsidies.map((subsidy) => {
                const Icon = subsidy.icon;
                return (
                  <div
                    key={subsidy.title}
                    className={`rounded-xl p-6 border ${colorClasses[subsidy.color]}`}
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 bg-white/50 rounded-lg flex items-center justify-center">
                        <Icon className="w-5 h-5" />
                      </div>
                      <h3 className="font-bold">{subsidy.title}</h3>
                    </div>
                    
                    <div className="text-2xl font-bold mb-2">{subsidy.amount}</div>
                    <p className="text-sm opacity-80">{subsidy.description}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* CTA */}
          <div className="bg-gradient-to-r from-solar-yellow/20 to-eco-green/20 rounded-2xl border border-solar-yellow/30 p-8 text-center">
            <h3 className="text-xl font-bold text-dark mb-3">
              ¿Quieres saber cuánto puedes ahorrar?
            </h3>
            <p className="text-gray-700 mb-6 max-w-2xl mx-auto">
              Calcula tu instalación solar personalizada y descubre tu ahorro estimado 
              teniendo en cuenta las subvenciones disponibles en tu zona.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => navigate('/chatbot')}
                className="px-8 py-4 bg-solar-yellow hover:bg-solar-yellow-dark text-dark font-bold rounded-xl transition-colors shadow-lg shadow-solar-yellow/30"
              >
                Calcular mi instalación
              </button>
              <button
                onClick={() => navigate('/graficas')}
                className="px-8 py-4 bg-white hover:bg-gray-50 text-dark font-bold rounded-xl border-2 border-gray-200 transition-colors"
              >
                Ver gráficas
              </button>
            </div>
          </div>

          {/* Additional Resources */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
            <a
              href="https://www.miteco.gob.es/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-eco-green transition-colors"
            >
              <div className="w-12 h-12 bg-eco-green/20 rounded-lg flex items-center justify-center">
                <ExternalLink className="w-6 h-6 text-eco-green-dark" />
              </div>
              <div>
                <h4 className="font-semibold text-dark">MITECO</h4>
                <p className="text-sm text-gray-600">Ministerio para la Transición Ecológica</p>
              </div>
            </a>
            
            <a
              href="https://www.idae.es/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-eco-green transition-colors"
            >
              <div className="w-12 h-12 bg-solar-yellow/20 rounded-lg flex items-center justify-center">
                <ExternalLink className="w-6 h-6 text-solar-yellow-dark" />
              </div>
              <div>
                <h4 className="font-semibold text-dark">IDAE</h4>
                <p className="text-sm text-gray-600">Instituto para la Diversificación y Ahorro de la Energía</p>
              </div>
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}

export default SubsidiesPage;
