import type { APIRoute } from 'astro';
import { createClient } from '@libsql/client';

export const prerender = false;

type Carrera = {
  titulo: string;
  fecha: string;
  ubicacion: string | null;
  imagen: string | null;
  url_inscripcion: string | null;
  url_ficha: string | null;
};

const escaparHtml = (valor: string | null | undefined) =>
  String(valor || '').replace(/[&<>'"]/g, (caracter) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[caracter] || caracter);

const formatearFecha = (fecha: string) => new Intl.DateTimeFormat('es-ES', {
  day: 'numeric', month: 'long', timeZone: 'UTC',
}).format(new Date(`${fecha}T12:00:00Z`));

const respuesta = (cuerpo: Record<string, unknown>, status = 200) => new Response(JSON.stringify(cuerpo), {
  status,
  headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});

const construirEmail = (carreras: Carrera[], periodo: string, siteUrl: string) => {
  const [year, month] = periodo.split('-').map(Number);
  const mes = new Intl.DateTimeFormat('es-ES', { month: 'long', year: 'numeric', timeZone: 'UTC' })
    .format(new Date(Date.UTC(year, month - 1, 1)));
  const tarjetas = carreras.map((carrera) => {
    const enlace = carrera.url_inscripcion || carrera.url_ficha || siteUrl;
    const imagen = carrera.imagen ? `<img src="${escaparHtml(carrera.imagen)}" alt="" width="120" style="display:block;width:120px;height:90px;object-fit:cover;background:#292a2b;" />` : '';
    return `<tr><td style="padding:18px 0;border-bottom:1px solid #d9d5ca;">${imagen}</td><td style="padding:18px 0 18px 16px;border-bottom:1px solid #d9d5ca;font-family:Arial,sans-serif;"><div style="font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#e84b18;font-weight:bold;">${escaparHtml(formatearFecha(carrera.fecha))}</div><div style="margin:5px 0;font-size:20px;line-height:1.1;font-weight:bold;color:#121315;">${escaparHtml(carrera.titulo)}</div><div style="font-size:14px;color:#5b5d5a;">${escaparHtml(carrera.ubicacion)}</div>${enlace ? `<a href="${escaparHtml(enlace)}" style="display:inline-block;margin-top:10px;color:#121315;font-size:12px;font-weight:bold;text-decoration:underline;text-transform:uppercase;">Ver carrera →</a>` : ''}</td></tr>`;
  }).join('');

  return `<!doctype html><html lang="es"><body style="margin:0;background:#f4f1ea;color:#121315;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1ea;"><tr><td align="center" style="padding:32px 16px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;"><tr><td style="padding:24px;background:#121315;color:#f4f1ea;font-family:Arial,sans-serif;"><div style="font-size:13px;letter-spacing:1px;color:#ff5a1f;font-weight:bold;">CALENDARIO / MURCIA / RUNNING</div><h1 style="margin:16px 0 0;font-size:38px;line-height:1;">Carreras de ${escaparHtml(mes)}</h1></td></tr><tr><td style="padding:24px;background:#f4f1ea;font-family:Arial,sans-serif;"><p style="margin:0 0 8px;font-size:16px;line-height:1.5;">Estas son las <strong>${carreras.length} carreras</strong> que tenemos en el radar este mes.</p><table role="presentation" width="100%" cellpadding="0" cellspacing="0">${tarjetas}</table><p style="margin:24px 0 0;font-size:12px;line-height:1.5;color:#5b5d5a;">Recibes este correo porque te suscribiste a la alerta mensual de Calendario Murcia Running.</p></td></tr></table></td></tr></table></body></html>`;
};

export const GET: APIRoute = async ({ request }) => {
  const cronSecret = import.meta.env.CRON_SECRET;
  if (!cronSecret || request.headers.get('authorization') !== `Bearer ${cronSecret}`) {
    return respuesta({ error: 'No autorizado' }, 401);
  }

  const tursoUrl = import.meta.env.TURSO_DATABASE_URL;
  const tursoToken = import.meta.env.TURSO_AUTH_TOKEN;
  const apiKey = import.meta.env.BREVO_API_KEY;
  const listId = Number(import.meta.env.BREVO_LIST_ID);
  const senderEmail = import.meta.env.BREVO_SENDER_EMAIL;
  const senderName = import.meta.env.BREVO_SENDER_NAME || 'Calendario Murcia Running';
  const siteUrl = import.meta.env.PUBLIC_SITE_URL || 'https://carreras-murcia.vercel.app';

  if (!tursoUrl || !tursoToken || !apiKey || !senderEmail || !Number.isInteger(listId) || listId <= 0) {
    return respuesta({ error: 'Faltan variables de configuración para el envío mensual.' }, 503);
  }

  const now = new Date();
  const periodo = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, '0')}`;
  const inicio = `${periodo}-01`;
  const siguiente = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 1)).toISOString().slice(0, 10);
  const db = createClient({ url: tursoUrl, authToken: tursoToken });

  try {
    await db.execute('CREATE TABLE IF NOT EXISTS envios_newsletter (periodo TEXT PRIMARY KEY, campania_id INTEGER NOT NULL, estado TEXT NOT NULL, creado_en TEXT NOT NULL)');
    const envioPrevio = await db.execute({ sql: 'SELECT campania_id, estado FROM envios_newsletter WHERE periodo = ?', args: [periodo] });
    if (envioPrevio.rows.length) {
      return respuesta({ enviado: false, motivo: `El resumen de ${periodo} ya fue creado.`, campaniaId: envioPrevio.rows[0].campania_id, estado: envioPrevio.rows[0].estado });
    }

    const resultado = await db.execute({
      sql: 'SELECT titulo, fecha, ubicacion, imagen, url_inscripcion, url_ficha FROM carreras WHERE fecha >= ? AND fecha < ? ORDER BY fecha ASC',
      args: [inicio, siguiente],
    });
    const carreras = resultado.rows as unknown as Carrera[];
    if (!carreras.length) return respuesta({ enviado: false, motivo: `No hay carreras para ${periodo}.` });

    const campaña = await fetch('https://api.brevo.com/v3/emailCampaigns', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'api-key': apiKey },
      body: JSON.stringify({
        name: `Carreras Murcia · ${periodo}`,
        subject: `Carreras en Murcia · ${new Intl.DateTimeFormat('es-ES', { month: 'long' }).format(now)}`,
        sender: { name: senderName, email: senderEmail },
        type: 'classic',
        recipients: { listIds: [listId] },
        htmlContent: construirEmail(carreras, periodo, siteUrl),
      }),
    });
    if (!campaña.ok) throw new Error(`Brevo no pudo crear la campaña: ${campaña.status} ${await campaña.text()}`);
    const { id: campaniaId } = await campaña.json();

    await db.execute({ sql: 'INSERT INTO envios_newsletter (periodo, campania_id, estado, creado_en) VALUES (?, ?, ?, ?)', args: [periodo, campaniaId, 'creada', new Date().toISOString()] });
    const envio = await fetch(`https://api.brevo.com/v3/emailCampaigns/${campaniaId}/sendNow`, { method: 'POST', headers: { 'api-key': apiKey } });
    if (!envio.ok) throw new Error(`Brevo no pudo enviar la campaña: ${envio.status} ${await envio.text()}`);

    await db.execute({ sql: 'UPDATE envios_newsletter SET estado = ? WHERE periodo = ?', args: ['enviada', periodo] });
    return respuesta({ enviado: true, campaniaId, carreras: carreras.length, periodo });
  } catch (error) {
    console.error('Error en newsletter mensual:', error);
    return respuesta({ error: 'No se ha podido generar el resumen mensual.' }, 502);
  } finally {
    db.close();
  }
};
