import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Sun, 
  MapPin, 
  Zap, 
  Battery, 
  TrendingUp, 
  Leaf, 
  Euro,
  MessageSquare,
  ChevronRight,
  Calculator,
  CheckCircle,
  Clock,
  Lightbulb,
  Shield,
  Award,
  BarChart3,
  Wallet,
  Home,
  Users,
  Store,
  Trees
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { calculateSolar } from '../utils/solarCalculations';
import Navbar from '../components/Navbar';
import StatCard from '../components/StatCard';
import LiveMonitor from '../components/LiveMonitor';

export function Dashboard() {
  const { user, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const [calculation, setCalculation] = useState(null);

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, loading, navigate]);

  useEffect(() => {
    if (user) {
      // Calculate with default values
      const result = calculateSolar({
        location: user.location || 'Madrid',
        monthlyConsumption: user.monthlyConsumption || 350,
        wantsBattery: true,
        years: 25,
      });
      setCalculation(result);
    }
  }, [user]);

  if (loading || !calculation) {
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
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8 animate-fade-in">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h1 className="text-3xl font-bold text-dark">
                  ¡Hola, {user?.name}! 👋
                </h1>
                <p className="text-gray-600 mt-1">
                  Aquí tienes el resumen de tu instalación solar estimada
                </p>
              </div>
              
              <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-xl shadow-sm border border-gray-200">
                <MapPin className="w-5 h-5 text-eco-green" />
                <span className="font-medium text-dark">{calculation.location}</span>
                <span className="text-gray-400">|</span>
                <span className="text-sm text-gray-600">{calculation.region}</span>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            <button
              onClick={() => navigate('/chatbot')}
              className="flex items-center gap-4 p-6 bg-gradient-to-r from-solar-yellow/20 to-solar-yellow/5 rounded-2xl border border-solar-yellow/30 hover:border-solar-yellow transition-all group"
            >
              <div className="w-14 h-14 bg-solar-yellow rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <MessageSquare className="w-7 h-7 text-dark" />
              </div>
              <div className="flex-1 text-left">
                <h3 className="font-bold text-dark">Hablar con el asistente AI</h3>
                <p className="text-sm text-gray-600">Calcula una instalación personalizada</p>
              </div>
              <ChevronRight className="w-6 h-6 text-solar-yellow-dark" />
            </button>

            <button
              onClick={() => navigate('/graficas')}
              className="flex items-center gap-4 p-6 bg-gradient-to-r from-eco-green/20 to-eco-green/5 rounded-2xl border border-eco-green/30 hover:border-eco-green transition-all group"
            >
              <div className="w-14 h-14 bg-eco-green rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <Calculator className="w-7 h-7 text-white" />
              </div>
              <div className="flex-1 text-left">
                <h3 className="font-bold text-dark">Ver gráficas detalladas</h3>
                <p className="text-sm text-gray-600">Analiza la producción a 25 años</p>
              </div>
              <ChevronRight className="w-6 h-6 text-eco-green-dark" />
            </button>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatCard
              title="Consumo mensual"
              value={calculation.monthlyConsumption}
              unit="kWh"
              subtitle={`${calculation.annualConsumption.toLocaleString()} kWh/año`}
              icon={Zap}
              color="yellow"
            />
            
            <StatCard
              title="Paneles necesarios"
              value={calculation.panels}
              unit=""
              subtitle={`${calculation.power} kWp de potencia`}
              icon={Sun}
              color="green"
            />
            
            <StatCard
              title="Producción año 1"
              value={calculation.production[1].toLocaleString()}
              unit="kWh"
              subtitle={`Cobertura del ${calculation.coverage}%`}
              icon={TrendingUp}
              color="yellow"
              trend="up"
              trendValue={`vs ${calculation.annualConsumption.toLocaleString()} kWh consumo`}
            />
            
            <StatCard
              title="Batería recomendada"
              value={calculation.batterySize}
              unit=""
              subtitle="Para maximizar autoconsumo"
              icon={Battery}
              color="green"
            />
          </div>

          {/* Production Overview */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-dark mb-6">Producción estimada a 25 años</h2>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { year: 1, label: 'Año 1', highlight: true },
                  { year: 10, label: 'Año 10', highlight: false },
                  { year: 20, label: 'Año 20', highlight: false },
                  { year: 25, label: 'Año 25', highlight: false },
                ].map(({ year, label, highlight }) => (
                  <div
                    key={year}
                    className={`p-4 rounded-xl text-center ${
                      highlight 
                        ? 'bg-solar-yellow/20 border-2 border-solar-yellow' 
                        : 'bg-gray-50 border border-gray-200'
                    }`}
                  >
                    <div className="text-sm text-gray-600 mb-1">{label}</div>
                    <div className="text-2xl font-bold text-dark">
                      {calculation.production[year].toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">kWh</div>
                  </div>
                ))}
              </div>
              
              <div className="mt-6 p-4 bg-gray-50 rounded-xl">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <TrendingUp className="w-4 h-4 text-eco-green" />
                  <span>
                    Degradación estimada del <strong>0.5%</strong> anual. 
                    Año 25: {Math.round(calculation.production[25] / calculation.production[1] * 100)}% de la producción inicial.
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-6">
              {/* Savings Card */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-eco-green/20 rounded-lg flex items-center justify-center">
                    <Euro className="w-5 h-5 text-eco-green-dark" />
                  </div>
                  <h3 className="font-bold text-dark">Ahorro estimado</h3>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <div className="text-sm text-gray-600 mb-1">Ahorro anual</div>
                    <div className="text-3xl font-bold text-eco-green">
                      {calculation.annualSavings}€
                    </div>
                  </div>
                  
                  <div className="pt-4 border-t border-gray-200">
                    <div className="text-sm text-gray-600 mb-1">Ahorro total (25 años)</div>
                    <div className="text-2xl font-bold text-dark">
                      ~{calculation.totalSavings}€
                    </div>
                  </div>
                </div>
              </div>

              {/* Environmental Impact */}
              <div className="bg-gradient-to-br from-eco-green/10 to-eco-green/5 rounded-2xl border border-eco-green/30 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-eco-green rounded-lg flex items-center justify-center">
                    <Leaf className="w-5 h-5 text-white" />
                  </div>
                  <h3 className="font-bold text-dark">Impacto ambiental</h3>
                </div>
                
                <div className="space-y-3">
                  <div>
                    <div className="text-sm text-gray-600">CO₂ evitado</div>
                    <div className="text-2xl font-bold text-eco-green-dark">
                      {calculation.co2Saved} toneladas
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-sm text-gray-600">Equivalente a</div>
                    <div className="text-lg font-semibold text-dark">
                      {calculation.treesEquivalent} árboles 🌳
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Recommendation */}
          <div className="bg-gradient-to-r from-solar-yellow/20 via-solar-yellow/10 to-eco-green/10 rounded-2xl border border-solar-yellow/30 p-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-solar-yellow rounded-xl flex items-center justify-center flex-shrink-0">
                <Sun className="w-6 h-6 text-dark" />
              </div>
              <div>
                <h3 className="font-bold text-dark text-lg mb-2">Nuestra recomendación</h3>
                <p className="text-gray-700">{calculation.recommendation}</p>
                <button
                  onClick={() => navigate('/subvenciones')}
                  className="mt-4 text-eco-green font-medium hover:text-eco-green-dark inline-flex items-center gap-1"
                >
                  Ver subvenciones disponibles
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Why Choose SolarLife AI */}
          <section className="mt-16">
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-dark mb-3">¿Por qué elegir SolarLife AI?</h2>
              <p className="text-gray-600 max-w-2xl mx-auto">
                Tu asistente inteligente para tomar la mejor decisión sobre energía solar
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 card-hover">
                <div className="w-12 h-12 bg-solar-yellow/20 rounded-xl flex items-center justify-center mb-4">
                  <Lightbulb className="w-6 h-6 text-solar-yellow-dark" />
                </div>
                <h3 className="font-bold text-dark text-lg mb-2">Decisiones informadas</h3>
                <p className="text-gray-600 text-sm">
                  Te ayudamos a tomar decisiones basadas en datos reales sobre tu instalación de energía solar.
                </p>
              </div>

              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 card-hover">
                <div className="w-12 h-12 bg-eco-green/20 rounded-xl flex items-center justify-center mb-4">
                  <Calculator className="w-6 h-6 text-eco-green-dark" />
                </div>
                <h3 className="font-bold text-dark text-lg mb-2">Cálculo personalizado</h3>
                <p className="text-gray-600 text-sm">
                  Calcula los paneles recomendados según tu consumo eléctrico y ubicación exacta.
                </p>
              </div>

              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 card-hover">
                <div className="w-12 h-12 bg-solar-yellow/20 rounded-xl flex items-center justify-center mb-4">
                  <BarChart3 className="w-6 h-6 text-solar-yellow-dark" />
                </div>
                <h3 className="font-bold text-dark text-lg mb-2">Proyección a 25 años</h3>
                <p className="text-gray-600 text-sm">
                  Estima la producción de tu instalación durante toda su vida útil con datos precisos.
                </p>
              </div>

              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 card-hover">
                <div className="w-12 h-12 bg-eco-green/20 rounded-xl flex items-center justify-center mb-4">
                  <TrendingUp className="w-6 h-6 text-eco-green-dark" />
                </div>
                <h3 className="font-bold text-dark text-lg mb-2">Degradación realista</h3>
                <p className="text-gray-600 text-sm">
                  Tenemos en cuenta la degradación anual del 0.5% para darte estimaciones realistas.
                </p>
              </div>

              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 card-hover">
                <div className="w-12 h-12 bg-solar-yellow/20 rounded-xl flex items-center justify-center mb-4">
                  <Battery className="w-6 h-6 text-solar-yellow-dark" />
                </div>
                <h3 className="font-bold text-dark text-lg mb-2">Batería recomendada</h3>
                <p className="text-gray-600 text-sm">
                  Te orientamos sobre el tamaño de batería ideal para maximizar tu autoconsumo.
                </p>
              </div>

              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 card-hover">
                <div className="w-12 h-12 bg-eco-green/20 rounded-xl flex items-center justify-center mb-4">
                  <Award className="w-6 h-6 text-eco-green-dark" />
                </div>
                <h3 className="font-bold text-dark text-lg mb-2">Subvenciones locales</h3>
                <p className="text-gray-600 text-sm">
                  Te ayudamos a encontrar ayudas y subvenciones disponibles en tu comunidad autónoma.
                </p>
              </div>
            </div>

            <div className="mt-8 bg-gradient-to-r from-eco-green/10 to-solar-yellow/10 rounded-2xl p-8 border border-eco-green/20">
              <div className="flex flex-col md:flex-row items-center gap-6">
                <div className="w-16 h-16 bg-eco-green rounded-2xl flex items-center justify-center flex-shrink-0">
                  <Leaf className="w-8 h-8 text-white" />
                </div>
                <div className="text-center md:text-left">
                  <h3 className="font-bold text-dark text-xl mb-2">Energía limpia, asequible y sostenible</h3>
                  <p className="text-gray-600">
                    Con SolarLife AI, dar el paso hacia el autoconsumo solar nunca ha sido tan fácil. 
                    Reduce tu factura de la luz, aumenta el valor de tu hogar y contribuye a un planeta más limpio.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Live Monitor */}
          <section className="mt-16">
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-dark mb-3">Monitor en tiempo real</h2>
              <p className="text-gray-600 max-w-2xl mx-auto">
                Simulación de monitorización para usuarios con instalación solar activa
              </p>
            </div>
            <LiveMonitor />
          </section>

          {/* Target Audience */}
          <section className="mt-16">
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-dark mb-3">¿Para quién es SolarLife AI?</h2>
              <p className="text-gray-600 max-w-2xl mx-auto">
                Nuestra plataforma se adapta a diferentes necesidades y perfiles de usuario
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 card-hover text-center">
                <div className="w-14 h-14 bg-solar-yellow/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <Home className="w-7 h-7 text-solar-yellow-dark" />
                </div>
                <h3 className="font-bold text-dark text-lg mb-2">Hogares</h3>
                <p className="text-sm text-gray-600">
                  Reduce tu factura de la luz y aumenta la independencia energética de tu familia.
                </p>
              </div>

              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 card-hover text-center">
                <div className="w-14 h-14 bg-eco-green/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <Users className="w-7 h-7 text-eco-green-dark" />
                </div>
                <h3 className="font-bold text-dark text-lg mb-2">Comunidades de vecinos</h3>
                <p className="text-sm text-gray-600">
                  Optimiza el consumo compartido y distribuye el ahorro entre todos los vecinos.
                </p>
              </div>

              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 card-hover text-center">
                <div className="w-14 h-14 bg-solar-yellow/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <Store className="w-7 h-7 text-solar-yellow-dark" />
                </div>
                <h3 className="font-bold text-dark text-lg mb-2">Pequeños negocios</h3>
                <p className="text-sm text-gray-600">
                  Reduce costes operativos y mejora la imagen de sostenibilidad de tu empresa.
                </p>
              </div>

              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 card-hover text-center">
                <div className="w-14 h-14 bg-eco-green/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <Trees className="w-7 h-7 text-eco-green-dark" />
                </div>
                <h3 className="font-bold text-dark text-lg mb-2">Zonas rurales</h3>
                <p className="text-sm text-gray-600">
                  Aprovecha el espacio disponible y genera tu propia energía independiente.
                </p>
              </div>
            </div>
          </section>

          {/* Real-time Usage */}
          <section className="mt-16">
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-dark mb-3">Uso en tiempo real</h2>
              <p className="text-gray-600 max-w-2xl mx-auto">
                Introduce tus datos y obtén estimaciones inmediatas para tu instalación solar
              </p>
            </div>

            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
              <div className="bg-gradient-to-r from-solar-yellow to-solar-yellow-light p-6">
                <div className="flex items-center gap-3">
                  <Clock className="w-6 h-6 text-dark" />
                  <h3 className="font-bold text-dark text-lg">Calcula tu instalación al instante</h3>
                </div>
              </div>

              <div className="p-6 md:p-8">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 bg-solar-yellow/20 rounded-lg flex items-center justify-center flex-shrink-0">
                      <MapPin className="w-5 h-5 text-solar-yellow-dark" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-dark mb-1">Ubicación</h4>
                      <p className="text-sm text-gray-600">Introduce tu ciudad o comunidad autónoma para calcular la irradiación solar.</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 bg-eco-green/20 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Zap className="w-5 h-5 text-eco-green-dark" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-dark mb-1">Consumo mensual</h4>
                      <p className="text-sm text-gray-600">Indica tus kWh mensuales para dimensionar la instalación ideal.</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 bg-solar-yellow/20 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Sun className="w-5 h-5 text-solar-yellow-dark" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-dark mb-1">Número de paneles</h4>
                      <p className="text-sm text-gray-600">Te recomendamos cuántos paneles necesitas según tu consumo.</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 bg-eco-green/20 rounded-lg flex items-center justify-center flex-shrink-0">
                      <BarChart3 className="w-5 h-5 text-eco-green-dark" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-dark mb-1">Producción estimada</h4>
                      <p className="text-sm text-gray-600">Obtén la producción anual estimada para los próximos 25 años.</p>
                    </div>
                  </div>
                </div>

                <div className="mt-8 pt-8 border-t border-gray-200">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                      <Wallet className="w-8 h-8 text-eco-green" />
                      <div>
                        <div className="text-sm text-gray-600">Ahorro aproximado</div>
                        <div className="font-bold text-dark">Calculado al instante</div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                      <Shield className="w-8 h-8 text-solar-yellow-dark" />
                      <div>
                        <div className="text-sm text-gray-600">Subvenciones</div>
                        <div className="font-bold text-dark">Orientativas por CCAA</div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                      <CheckCircle className="w-8 h-8 text-eco-green" />
                      <div>
                        <div className="text-sm text-gray-600">Resultados</div>
                        <div className="font-bold text-dark">Inmediatos y precisos</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-8 text-center">
                  <button
                    onClick={() => navigate('/chatbot')}
                    className="inline-flex items-center gap-2 px-8 py-4 bg-solar-yellow hover:bg-solar-yellow-dark text-dark font-bold rounded-xl transition-all shadow-lg hover:shadow-xl"
                  >
                    <MessageSquare className="w-5 h-5" />
                    Probar el asistente AI ahora
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
