/**
 * SolarLife AI - Solar Calculations Engine
 * Simulates solar panel calculations for Spain
 */

// Production factors by region (kWh/kWp/year)
const REGION_FACTORS = {
  // High production (South)
  'andalucia': 1700,
  'murcia': 1700,
  'comunidad valenciana': 1650,
  'canarias': 1750,
  'extremadura': 1650,
  
  // Medium-high production (Center)
  'madrid': 1500,
  'castilla-la mancha': 1550,
  'aragon': 1500,
  'castilla y leon': 1450,
  'la rioja': 1450,
  'navarra': 1450,
  
  // Medium production (East/Northeast)
  'cataluna': 1400,
  'cataluña': 1400,
  'baleares': 1550,
  
  // Lower production (North)
  'galicia': 1250,
  'asturias': 1200,
  'cantabria': 1200,
  'pais vasco': 1150,
  'euskadi': 1150,
};

// City to region mapping
const CITY_TO_REGION = {
  'sevilla': 'andalucia',
  'malaga': 'andalucia',
  'granada': 'andalucia',
  'cordoba': 'andalucia',
  'almeria': 'andalucia',
  'cadiz': 'andalucia',
  'huelva': 'andalucia',
  'jaen': 'andalucia',
  'murcia': 'murcia',
  'cartagena': 'murcia',
  'valencia': 'comunidad valenciana',
  'alicante': 'comunidad valenciana',
  'castellon': 'comunidad valenciana',
  'las palmas': 'canarias',
  'tenerife': 'canarias',
  'madrid': 'madrid',
  'toledo': 'castilla-la mancha',
  'guadalajara': 'castilla-la mancha',
  'ciudad real': 'castilla-la mancha',
  'albacete': 'castilla-la mancha',
  'cuenca': 'castilla-la mancha',
  'zaragoza': 'aragon',
  'huesca': 'aragon',
  'teruel': 'aragon',
  'valladolid': 'castilla y leon',
  'leon': 'castilla y leon',
  'burgos': 'castilla y leon',
  'salamanca': 'castilla y leon',
  'barcelona': 'cataluna',
  'tarragona': 'cataluna',
  'lleida': 'cataluna',
  'girona': 'cataluna',
  'palma': 'baleares',
  'santiago': 'galicia',
  'coruna': 'galicia',
  'vigo': 'galicia',
  'ourense': 'galicia',
  'lugo': 'galicia',
  'pontevedra': 'galicia',
  'oviedo': 'asturias',
  'gijon': 'asturias',
  'santander': 'cantabria',
  'bilbao': 'pais vasco',
  'san sebastian': 'pais vasco',
  'vitoria': 'pais vasco',
};

const PANEL_POWER = 450; // Watts per panel
const DEGRADATION_RATE = 0.005; // 0.5% per year

/**
 * Get region from city or region name
 */
export function getRegion(location) {
  const normalized = location.toLowerCase().trim();
  
  // Direct region match
  if (REGION_FACTORS[normalized]) {
    return normalized;
  }
  
  // City match
  if (CITY_TO_REGION[normalized]) {
    return CITY_TO_REGION[normalized];
  }
  
  // Partial match for regions
  for (const region of Object.keys(REGION_FACTORS)) {
    if (normalized.includes(region) || region.includes(normalized)) {
      return region;
    }
  }
  
  // Partial match for cities
  for (const [city, region] of Object.entries(CITY_TO_REGION)) {
    if (normalized.includes(city) || city.includes(normalized)) {
      return region;
    }
  }
  
  // Default to medium production
  return 'madrid';
}

/**
 * Get production factor for a region
 */
export function getProductionFactor(region) {
  return REGION_FACTORS[region] || 1500;
}

/**
 * Calculate solar installation
 */
export function calculateSolar({
  location,
  monthlyConsumption,
  maxPanels = null,
  wantsBattery = true,
  years = 25
}) {
  const region = getRegion(location);
  const productionFactor = getProductionFactor(region);
  const annualConsumption = monthlyConsumption * 12;
  
  // Calculate required panels
  // Formula: (annual consumption / production factor) * 1.2 (safety margin)
  const requiredPower = (annualConsumption / productionFactor) * 1.2;
  const requiredPanels = Math.ceil((requiredPower * 1000) / PANEL_POWER);
  
  // Apply panel limit if specified
  const finalPanels = maxPanels ? Math.min(requiredPanels, maxPanels) : requiredPanels;
  const finalPower = (finalPanels * PANEL_POWER) / 1000; // kWp
  
  // Calculate production over years
  const production = {};
  for (let year = 1; year <= years; year++) {
    const degradation = Math.pow(1 - DEGRADATION_RATE, year - 1);
    production[year] = Math.round(finalPower * productionFactor * degradation);
  }
  
  // Coverage percentage
  const year1Production = production[1];
  const coverage = Math.min(100, Math.round((year1Production / annualConsumption) * 100));
  
  // Battery recommendation
  let batterySize = null;
  if (wantsBattery) {
    if (monthlyConsumption < 200) {
      batterySize = '3-5 kWh';
    } else if (monthlyConsumption < 400) {
      batterySize = '5-7 kWh';
    } else {
      batterySize = '8-12 kWh';
    }
  }
  
  // Savings estimation (approximate)
  const electricityPrice = 0.18; // €/kWh average
  const annualSavings = Math.min(year1Production, annualConsumption) * electricityPrice;
  const totalSavings = annualSavings * years * 0.85; // Accounting for degradation
  
  // Environmental impact
  const co2Saved = (year1Production * years * 0.4) / 1000; // tons of CO2
  const treesEquivalent = Math.round(co2Saved * 50); // approximate
  
  return {
    location,
    region,
    monthlyConsumption,
    annualConsumption,
    panels: finalPanels,
    power: finalPower.toFixed(2),
    production,
    coverage,
    batterySize,
    annualSavings: annualSavings.toFixed(0),
    totalSavings: totalSavings.toFixed(0),
    co2Saved: co2Saved.toFixed(1),
    treesEquivalent,
    recommendation: generateRecommendation(coverage, finalPanels, batterySize)
  };
}

/**
 * Generate recommendation text
 */
function generateRecommendation(coverage, panels, batterySize) {
  if (coverage >= 90) {
    return `Instalación óptima con ${panels} paneles. ${batterySize ? `Batería de ${batterySize} recomendada para maximizar autoconsumo.` : ''}`;
  } else if (coverage >= 70) {
    return `Buena cobertura del ${coverage}% con ${panels} paneles. Considera aumentar el número de paneles si tienes espacio.`;
  } else {
    return `Cobertura del ${coverage}% con ${panels} paneles. Te recomendamos evaluar si puedes instalar más paneles o reducir consumo.`;
  }
}

/**
 * Get subsidies info by region
 */
export function getSubsidies(region) {
  const regionKey = region.toLowerCase();
  
  const subsidies = {
    'andalucia': {
      name: 'Andalucía',
      aids: [
        'Programa Andalucía Solar: hasta 40% de subvención para autoconsumo',
        'Bonificación IBI del 50% durante 4 años',
        'Deducción del 20% en IRPF para instalaciones domésticas'
      ],
      links: ['https://www.juntadeandalucia.es/']
    },
    'madrid': {
      name: 'Comunidad de Madrid',
      aids: [
        'Ayudas Plan Renove: hasta 3.000€ para autoconsumo residencial',
        'Bonificación IBI del 50% durante 5 años',
        'ICIO bonificado al 95%'
      ],
      links: ['https://www.madrid.org/']
    },
    'cataluna': {
      name: 'Cataluña',
      aids: [
        'Programa ICAEN: subvenciones para autoconsumo',
        'Bonificación IBI del 50% durante 10 años',
        'Deducción del 15% en IRPF'
      ],
      links: ['https://icaen.gencat.cat/']
    },
    'comunidad valenciana': {
      name: 'Comunidad Valenciana',
      aids: [
        'IVACE+: ayudas para autoconsumo industrial y residencial',
        'Bonificación IBI del 50%',
        'Ayudas específicas por municipio'
      ],
      links: ['https://www.ivace.es/']
    },
    'galicia': {
      name: 'Galicia',
      aids: [
        'Programa de incentivos a proyectos de energías renovables',
        'Bonificación IBI variable según municipio',
        'Ayudas del IGVS para comunidades'
      ],
      links: ['https://www.igvs.es/']
    },
    'pais vasco': {
      name: 'País Vasco',
      aids: [
        'Programa EVE: asesoramiento y ayudas para autoconsumo',
        'Bonificación IBI del 50% en Bizkaia y Gipuzkoa',
        'Subvenciones específicas por territorio'
      ],
      links: ['https://www.eve.eus/']
    }
  };
  
  // Return specific region or default
  return subsidies[regionKey] || {
    name: region,
    aids: [
      'Consulta las ayudas específicas de tu comunidad autónoma',
      'Bonificación del IBI habitualmente disponible',
      'Deducciones fiscales en IRPF según normativa vigente'
    ],
    links: ['https://www.miteco.gob.es/']
  };
}

/**
 * Parse natural language input
 */
export function parseUserInput(text) {
  const normalized = text.toLowerCase();
  
  // Extract location
  const locationPatterns = [
    /vivo en ([\w\s]+?)(?:,|\s+y\s+|\s+consumo|\s+mi\s+consumo|$)/i,
    /en ([\w\s]+?)(?:,|\s+y\s+|\s+consumo|\s+mi\s+consumo|$)/i,
    /ubicacion(?:\s+en)?\s+([\w\s]+?)(?:,|\s+y\s+|$)/i,
  ];
  
  let location = null;
  for (const pattern of locationPatterns) {
    const match = normalized.match(pattern);
    if (match) {
      location = match[1].trim();
      break;
    }
  }
  
  // Extract consumption
  const consumptionPatterns = [
    /consumo (\d+)\s*kwh/i,
    /(\d+)\s*kwh(?:\s+al?\s*mes)?/i,
    /(\d+)\s*kwh\s+mensual/i,
  ];
  
  let consumption = null;
  for (const pattern of consumptionPatterns) {
    const match = normalized.match(pattern);
    if (match) {
      consumption = parseInt(match[1]);
      break;
    }
  }
  
  // Extract years
  const yearsMatch = normalized.match(/(\d+)\s*años?/);
  const years = yearsMatch ? parseInt(yearsMatch[1]) : 25;
  
  // Check for battery preference
  const wantsBattery = !normalized.includes('sin bateria') && 
                       !normalized.includes('no bateria') &&
                       !normalized.includes('sin batería');
  
  return { location, consumption, years, wantsBattery };
}
