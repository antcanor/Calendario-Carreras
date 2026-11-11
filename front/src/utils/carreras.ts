export const SITE_URL = 'https://carreras-murcia.vercel.app';

export const meses = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'];
export const mesesLargos = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const diasCortos = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const diasLargos = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];

export const formatearFecha = (valor: string) => {
  if (!valor) return { dia: '', mes: '', mesLargo: '', diaSemana: '', completa: '', larga: '' };
  const [a, m, d] = valor.split('-');
  const date = new Date(Number(a), Number(m) - 1, Number(d));
  const mesLargo = mesesLargos[date.getMonth()];
  return {
    dia: date.getDate().toString(),
    mes: meses[date.getMonth()],
    mesLargo,
    diaSemana: diasCortos[date.getDay()],
    completa: `${date.getDate()} ${mesLargo} ${a}`,
    larga: `${diasLargos[date.getDay()]}, ${date.getDate()} de ${mesLargo.toLowerCase()} de ${a}`
  };
};

export const etiquetaMes = (valor: string) => {
  const [a, m] = valor.split('-');
  return `${mesesLargos[Number(m) - 1]} ${a}`;
};

// La base guarda las distancias como km separados por comas: '0.6,5,10,21.097'
export const leerDistancias = (valor: unknown): number[] =>
  String(valor ?? '').split(',').map(Number).filter((km) => Number.isFinite(km) && km > 0).sort((a, b) => a - b);

const formatearKm = (km: number) => km.toLocaleString('es-ES', { maximumFractionDigits: 1 });

// '5, 10 y 21,1 km'. Con `maximo`, se quedan las más largas y se omiten las infantiles (menos de 1 km).
export const formatearDistancias = (valor: unknown, maximo?: number) => {
  let kms = leerDistancias(valor);
  if (maximo) {
    const principales = kms.filter((km) => km >= 1);
    kms = (principales.length ? principales : kms).slice(-maximo);
  }
  if (!kms.length) return '';
  const textos = [...new Set(kms.map(formatearKm))];
  const lista = textos.length > 1 ? `${textos.slice(0, -1).join(', ')} y ${textos[textos.length - 1]}` : textos[0];
  return `${lista} km`;
};

const formatearEuros = (importe: number) => `${importe.toLocaleString('es-ES', { minimumFractionDigits: Number.isInteger(importe) ? 0 : 2, maximumFractionDigits: 2 })} €`;

// 'Gratis', '12 €' o 'Desde 8 €' (con `rango`, 'De 8 a 20 €'). '' si no se conoce el precio.
export const formatearPrecio = (minimo: unknown, maximo: unknown, rango = false) => {
  if (minimo == null || minimo === '') return '';
  const min = Number(minimo);
  const max = maximo == null || maximo === '' ? min : Number(maximo);
  if (!Number.isFinite(min)) return '';
  if (max <= 0) return 'Gratis';
  if (min === max) return formatearEuros(min);
  if (rango) return min <= 0 ? `Gratis o hasta ${formatearEuros(max)}` : `De ${formatearEuros(min).replace(' €', '')} a ${formatearEuros(max)}`;
  return min <= 0 ? 'Desde gratis' : `Desde ${formatearEuros(min)}`;
};

export const generarSlug =(titulo: string, fecha?: string) => {
  const anio = fecha ? fecha.substring(0, 4) : '';
  const base = `${titulo} ${anio}`
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return base;
};

type CarreraEnlazable = { titulo: string; fecha: string; ubicacion?: string; url_inscripcion?: string; url_ficha?: string };

export const crearGoogleCalendarUrl = (carrera: CarreraEnlazable, slug?: string) => {
  const [a, m, d] = carrera.fecha.split('-').map(Number);
  const inicio = `${a}${String(m).padStart(2, '0')}${String(d).padStart(2, '0')}`;
  const finDate = new Date(Date.UTC(a, m - 1, d + 1));
  const fin = `${finDate.getUTCFullYear()}${String(finDate.getUTCMonth() + 1).padStart(2, '0')}${String(finDate.getUTCDate()).padStart(2, '0')}`;
  const titulo = carrera.titulo;
  const ubicacion = `${carrera.ubicacion || 'Región de Murcia'}, España`;
  const enlace = slug ? `${SITE_URL}/carrera/${slug}` : (carrera.url_inscripcion || carrera.url_ficha || SITE_URL);
  const detalles = `Información e inscripciones: ${enlace}\n\nEncuentra más carreras en Calendario Murcia Running: ${SITE_URL}`;
  return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(titulo)}&dates=${inicio}/${fin}&details=${encodeURIComponent(detalles)}&location=${encodeURIComponent(ubicacion)}`;
};

export const crearWhatsAppShareUrl = (carrera: CarreraEnlazable, slug?: string) => {
  const enlaceFicha = slug ? `${SITE_URL}/carrera/${slug}` : (carrera.url_inscripcion || carrera.url_ficha || SITE_URL);
  const texto = `🏃‍♂️ ¡Mira esta carrera en Murcia!\n\n🔥 *${carrera.titulo}*\n📅 ${formatearFecha(carrera.fecha).completa}\n📍 ${carrera.ubicacion || 'Región de Murcia'}\n\n👉 Ficha e inscripciones:\n${enlaceFicha}\n\nEncuentra más en: ${SITE_URL}`;
  return `https://api.whatsapp.com/send?text=${encodeURIComponent(texto)}`;
};
