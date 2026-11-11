export type Clima = {
  texto: string;
  icono: string; // clase de bootstrap-icons
  tempMax: number;
  tempMin: number;
  lluvia: number;
  viento: number;
};

const DIAS_PREVISION = 14;

const interpretarClima = (code: number) => {
  if (code === 0) return { texto: 'Despejado', icono: 'bi-sun' };
  if (code === 1) return { texto: 'Poco nuboso', icono: 'bi-cloud-sun' };
  if (code === 2) return { texto: 'Intervalos nubosos', icono: 'bi-cloud-sun' };
  if (code === 3) return { texto: 'Nublado', icono: 'bi-clouds' };
  if (code === 45 || code === 48) return { texto: 'Niebla', icono: 'bi-cloud-fog' };
  if ([51, 53, 55, 56, 57].includes(code)) return { texto: 'Llovizna', icono: 'bi-cloud-drizzle' };
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return { texto: 'Lluvia', icono: 'bi-cloud-rain' };
  if ([71, 73, 75, 77, 85, 86].includes(code)) return { texto: 'Nieve', icono: 'bi-snow' };
  if ([95, 96, 99].includes(code)) return { texto: 'Tormenta', icono: 'bi-cloud-lightning-rain' };
  return { texto: 'Variable', icono: 'bi-cloud' };
};

export const tienePrevision = (fecha: string, ahora = new Date()) => {
  const hoy = ahora.toISOString().split('T')[0];
  const limite = new Date(ahora.getTime() + DIAS_PREVISION * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  return fecha >= hoy && fecha <= limite;
};

// Previsión de Open-Meteo para el día de la carrera. Devuelve null si no hay
// coordenadas, si la fecha queda fuera de la previsión o si la API no responde a tiempo.
export const obtenerClima = async (latitud: unknown, longitud: unknown, fecha: string, timeoutMs = 2000): Promise<Clima | null> => {
  const lat = Number(latitud);
  const lon = Number(longitud);
  if (latitud == null || longitud == null || !Number.isFinite(lat) || !Number.isFinite(lon) || !tienePrevision(fecha)) return null;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max&timezone=Europe/Madrid&start_date=${fecha}&end_date=${fecha}`;
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) return null;
    const { daily } = await res.json();
    if (!daily?.time?.length) return null;
    return {
      ...interpretarClima(daily.weather_code?.[0] ?? 0),
      tempMax: Math.round(daily.temperature_2m_max?.[0] ?? 0),
      tempMin: Math.round(daily.temperature_2m_min?.[0] ?? 0),
      lluvia: daily.precipitation_probability_max?.[0] ?? 0,
      viento: Math.round(daily.wind_speed_10m_max?.[0] ?? 0),
    };
  } catch {
    return null; // sin previsión antes que retrasar la página
  } finally {
    clearTimeout(timeoutId);
  }
};
