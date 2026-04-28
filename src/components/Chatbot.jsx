import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, MapPin, Zap, Battery, Calendar, Home } from 'lucide-react';
import { calculateSolar, parseUserInput, getRegion, getProductionFactor } from '../utils/solarCalculations';

export function Chatbot({ onCalculationComplete }) {
  const [messages, setMessages] = useState([
    {
      type: 'bot',
      content: '¡Hola! Soy tu asistente SolarLife AI. 🌞\n\nPuedo ayudarte a calcular cuántos paneles solares necesitas. Solo dime:\n\n• ¿Dónde vives? (ciudad o comunidad autónoma)\n• ¿Cuál es tu consumo mensual en kWh?\n• ¿Tienes espacio limitado para paneles?\n• ¿Te interesa incluir batería?',
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [conversationState, setConversationState] = useState({
    location: null,
    consumption: null,
    maxPanels: null,
    wantsBattery: true,
    years: 25,
    step: 'initial',
  });
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const addMessage = (type, content) => {
    setMessages((prev) => [...prev, { type, content }]);
  };

  const simulateTyping = async (callback) => {
    setIsTyping(true);
    await new Promise((resolve) => setTimeout(resolve, 1000 + Math.random() * 1000));
    setIsTyping(false);
    callback();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    addMessage('user', userMessage);
    setInput('');

    // Parse user input
    const parsed = parseUserInput(userMessage);
    
    // Update conversation state with new info
    const newState = { ...conversationState };
    if (parsed.location) newState.location = parsed.location;
    if (parsed.consumption) newState.consumption = parsed.consumption;
    if (parsed.years) newState.years = parsed.years;
    if (parsed.wantsBattery !== undefined) newState.wantsBattery = parsed.wantsBattery;
    
    // Check for space limit
    const panelMatch = userMessage.match(/(\d+)\s*paneles?/i);
    if (panelMatch) {
      newState.maxPanels = parseInt(panelMatch[1]);
    }
    
    // Check for battery preference
    if (userMessage.includes('sin bateria') || userMessage.includes('no bateria')) {
      newState.wantsBattery = false;
    }

    setConversationState(newState);

    // Determine next step
    simulateTyping(() => {
      if (!newState.location) {
        addMessage('bot', '¿Podrías indicarme tu ciudad o comunidad autónoma? Por ejemplo: "Vivo en Sevilla" o "Estoy en Madrid". 🗺️');
      } else if (!newState.consumption) {
        addMessage('bot', `Perfecto, ${newState.location}. ¿Cuál es tu consumo mensual aproximado en kWh? Puedes encontrarlo en tu factura de la luz. ⚡`);
      } else {
        // We have enough info, calculate
        try {
          const result = calculateSolar({
            location: newState.location,
            monthlyConsumption: newState.consumption,
            maxPanels: newState.maxPanels,
            wantsBattery: newState.wantsBattery,
            years: newState.years,
          });

          // Format response
          const response = formatCalculationResponse(result);
          addMessage('bot', response);
          
          // Notify parent component
          if (onCalculationComplete) {
            onCalculationComplete(result);
          }
          
          // Reset for next conversation
          setConversationState({
            location: null,
            consumption: null,
            maxPanels: null,
            wantsBattery: true,
            years: 25,
            step: 'initial',
          });
        } catch (error) {
          addMessage('bot', 'Lo siento, ha ocurrido un error en el cálculo. ¿Podrías verificar los datos e intentarlo de nuevo?');
        }
      }
    });
  };

  const formatCalculationResponse = (result) => {
    return `🎉 ¡Cálculo completado para ${result.location}!

📊 **RESUMEN DE TU INSTALACIÓN:**

🏠 **Ubicación:** ${result.location} (${result.region})
⚡ **Consumo:** ${result.monthlyConsumption} kWh/mes (${result.annualConsumption} kWh/año)
🔋 **Paneles recomendados:** ${result.panels} paneles (${result.power} kWp)
${result.batterySize ? `🔋 **Batería recomendada:** ${result.batterySize}` : ''}
📈 **Cobertura:** ${result.coverage}% de tu consumo

☀️ **PRODUCCIÓN ESTIMADA:**
• Año 1: ${result.production[1].toLocaleString()} kWh
• Año 10: ${result.production[10].toLocaleString()} kWh
• Año 20: ${result.production[20].toLocaleString()} kWh
• Año 25: ${result.production[25].toLocaleString()} kWh
📉 Degradación anual: 0.5%

💰 **AHORRO ESTIMADO:**
• Ahorro anual: ~${result.annualSavings}€
• Ahorro total (25 años): ~${result.totalSavings}€

🌱 **IMPACTO AMBIENTAL:**
• CO₂ evitado: ${result.co2Saved} toneladas
• Equivalente a ${result.treesEquivalent} árboles plantados

💡 **RECOMENDACIÓN:**
${result.recommendation}

¿Te gustaría hacer otro cálculo o ver las gráficas de producción? 📊`;
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-solar-yellow to-solar-yellow-light p-4 flex items-center gap-3">
        <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center shadow-md">
          <Bot className="w-6 h-6 text-solar-yellow-dark" />
        </div>
        <div>
          <h3 className="font-bold text-dark">SolarLife AI Assistant</h3>
          <p className="text-sm text-dark/70">Tu experto en energía solar</p>
        </div>
        <div className="ml-auto flex items-center gap-1 text-xs font-medium text-dark/60 bg-white/50 px-2 py-1 rounded-full">
          <Sparkles className="w-3 h-3" />
          <span>AI Powered</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex gap-3 ${message.type === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                message.type === 'bot'
                  ? 'bg-solar-yellow/20'
                  : 'bg-eco-green/20'
              }`}
            >
              {message.type === 'bot' ? (
                <Bot className="w-4 h-4 text-solar-yellow-dark" />
              ) : (
                <User className="w-4 h-4 text-eco-green-dark" />
              )}
            </div>
            <div
              className={`max-w-[80%] p-4 rounded-2xl text-sm whitespace-pre-line ${
                message.type === 'bot'
                  ? 'bg-white shadow-sm border border-gray-100'
                  : 'bg-eco-green text-white'
              }`}
            >
              {message.content}
            </div>
          </div>
        ))}
        
        {isTyping && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-solar-yellow/20 flex items-center justify-center">
              <Bot className="w-4 h-4 text-solar-yellow-dark" />
            </div>
            <div className="bg-white shadow-sm border border-gray-100 p-4 rounded-2xl">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-solar-yellow rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-solar-yellow rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-solar-yellow rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Suggestions */}
      <div className="px-4 py-2 bg-white border-t border-gray-100">
        <p className="text-xs text-gray-500 mb-2">Ejemplos de preguntas:</p>
        <div className="flex flex-wrap gap-2">
          {[
            'Vivo en Sevilla, consumo 450 kWh',
            '¿Cuántos paneles necesito en Madrid?',
            'Cálculo para Barcelona, 300 kWh/mes',
          ].map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => setInput(suggestion)}
              className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-solar-yellow/20 text-gray-600 hover:text-dark rounded-full transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-gray-200">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Escribe tu mensaje..."
            className="flex-1 px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-solar-yellow/50 focus:border-transparent"
          />
          <button
            type="submit"
            disabled={!input.trim() || isTyping}
            className="px-4 py-3 bg-solar-yellow hover:bg-solar-yellow-dark text-dark font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </form>
    </div>
  );
}

export default Chatbot;
