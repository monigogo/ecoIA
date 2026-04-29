import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sun, Mail, Lock, ArrowRight, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Logo from '../components/Logo';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 1000));

    if (!email || !password) {
      setError('Por favor, introduce email y contraseña');
      setIsLoading(false);
      return;
    }

    const result = login(email, password);
    
    if (result.success) {
      navigate('/dashboard');
    } else {
      setError('Error al iniciar sesión');
    }
    
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen flex">
      {/* Left Side - Form */}
      <div className="flex-1 flex flex-col justify-center px-4 sm:px-6 lg:px-8 xl:px-12 bg-white">
        <div className="max-w-md w-full mx-auto">
          {/* Logo */}
          <div className="mb-8">
            <Logo size="large" />
          </div>

          {/* Heading */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-dark mb-2">
              Planifica tu energía solar de forma inteligente
            </h1>
            <p className="text-gray-600">
              Accede a tu panel personalizado y descubre cuánto puedes ahorrar con energía solar.
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-dark mb-2">
                Correo electrónico
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full pl-10 pr-3 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-solar-yellow/50 focus:border-transparent transition-all"
                  placeholder="tu@email.com"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-dark mb-2">
                Contraseña
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-10 pr-3 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-solar-yellow/50 focus:border-transparent transition-all"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  type="checkbox"
                  className="h-4 w-4 text-solar-yellow focus:ring-solar-yellow border-gray-300 rounded"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-600">
                  Recordarme
                </label>
              </div>
              <a href="#" className="text-sm font-medium text-eco-green hover:text-eco-green-dark">
                ¿Olvidaste tu contraseña?
              </a>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 px-8 py-4 bg-solar-yellow hover:bg-solar-yellow-dark text-dark font-bold rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-solar-yellow/30"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-dark/30 border-t-dark rounded-full animate-spin" />
              ) : (
                <>
                  Iniciar sesión
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </form>

          {/* Demo credentials */}
          <div className="mt-8 p-4 bg-gray-50 rounded-xl border border-gray-200">
            <p className="text-sm text-gray-600 mb-2">
              <Sparkles className="w-4 h-4 inline mr-1 text-solar-yellow" />
              <strong>Demo:</strong> Usa cualquier email y contraseña
            </p>
            <p className="text-xs text-gray-500">
              Ejemplo: demo@solarlife.ai / password
            </p>
          </div>
        </div>
      </div>

      {/* Right Side - Image/Gradient */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-solar-yellow via-solar-yellow-light to-eco-green" />
        
        {/* Pattern overlay */}
        <div className="absolute inset-0 opacity-10">
          <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
                <circle cx="1" cy="1" r="1" fill="currentColor" />
              </pattern>
            </defs>
            <rect width="100" height="100" fill="url(#grid)" />
          </svg>
        </div>

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center px-12 text-dark">
          <div className="mb-8">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/20 backdrop-blur rounded-full text-sm font-medium mb-6">
              <Sun className="w-4 h-4" />
              Energía 100% renovable
            </div>
            <h2 className="text-4xl font-bold mb-4">
              Transforma tu hogar con energía solar
            </h2>
            <p className="text-lg opacity-80">
              Calcula tu instalación ideal, descubre tu ahorro potencial y da el paso hacia un futuro sostenible.
            </p>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-6">
            <div className="bg-white/20 backdrop-blur rounded-2xl p-6">
              <div className="text-3xl font-bold mb-1">70%</div>
              <div className="text-sm opacity-80">Ahorro en factura</div>
            </div>
            <div className="bg-white/20 backdrop-blur rounded-2xl p-6">
              <div className="text-3xl font-bold mb-1">25 años</div>
              <div className="text-sm opacity-80">Vida útil garantizada</div>
            </div>
            <div className="bg-white/20 backdrop-blur rounded-2xl p-6">
              <div className="text-3xl font-bold mb-1">5-7 años</div>
              <div className="text-sm opacity-80">Retorno de inversión</div>
            </div>
            <div className="bg-white/20 backdrop-blur rounded-2xl p-6">
              <div className="text-3xl font-bold mb-1">0.5%</div>
              <div className="text-sm opacity-80">Degradación anual</div>
            </div>
          </div>
        </div>

        {/* Decorative elements */}
        <div className="absolute bottom-0 right-0 w-96 h-96 bg-white/10 rounded-full blur-3xl -mr-48 -mb-48" />
        <div className="absolute top-0 left-0 w-64 h-64 bg-eco-green/20 rounded-full blur-3xl -ml-32 -mt-32" />
      </div>
    </div>
  );
}

export default Login;
