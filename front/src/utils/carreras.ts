export const meses = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'];
export const mesesLargos = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

export const formatearFecha = (valor: string) => {
  if (!valor) return { dia: '', mes: '', completa: '' };
  const [a, m, d] = valor.split('-');
  const date = new Date(Number(a), Number(m) - 1, Number(d));
  return {
    dia: date.getDate().toString(),
    mes: meses[date.getMonth()],
    completa: `${date.getDate()} ${mesesLargos[date.getMonth()]} ${a}`
  };
};

export const generarSlug = (titulo: string, fecha?: string) => {
  const anio = fecha ? fecha.substring(0, 4) : '';
  const base = `${titulo} ${anio}`
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return base;
};

export const crearGoogleCalendarUrl = (carrera: { titulo: string; fecha: string; ubicacion?: string; url_inscripcion?: string; url_ficha?: string }) => {
  const [a, m, d] = carrera.fecha.split('-').map(Number);
  const inicio = `${a}${String(m).padStart(2, '0')}${String(d).padStart(2, '0')}`;
  const finDate = new Date(Date.UTC(a, m - 1, d + 1));
  const fin = `${finDate.getUTCFullYear()}${String(finDate.getUTCMonth() + 1).padStart(2, '0')}${String(finDate.getUTCDate()).padStart(2, '0')}`;
  const titulo = carrera.titulo;
  const ubicacion = `${carrera.ubicacion || 'Región de Murcia'}, España`;
  const enlace = carrera.url_inscripcion || carrera.url_ficha || 'https://calendario-carreras.vercel.app';
  const detalles = `Información e inscripciones: ${enlace}\n\nEncuentra más carreras en Calendario Murcia Running: https://calendario-carreras.vercel.app`;
  return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(titulo)}&dates=${inicio}/${fin}&details=${encodeURIComponent(detalles)}&location=${encodeURIComponent(ubicacion)}`;
};

export const crearWhatsAppShareUrl = (carrera: { titulo: string; fecha: string; ubicacion?: string; url_inscripcion?: string; url_ficha?: string }, slug?: string) => {
  const urlBase = 'https://calendario-carreras.vercel.app';
  const enlaceFicha = slug ? `${urlBase}/carrera/${slug}` : (carrera.url_inscripcion || carrera.url_ficha || urlBase);
  const texto = `🏃‍♂️ ¡Mira esta carrera en Murcia!\n\n🔥 *${carrera.titulo}*\n📅 ${formatearFecha(carrera.fecha).completa}\n📍 ${carrera.ubicacion || 'Región de Murcia'}\n\n👉 Ficha e inscripciones:\n${enlaceFicha}\n\nEncuentra más en: ${urlBase}`;
  return `https://api.whatsapp.com/send?text=${encodeURIComponent(texto)}`;
};

