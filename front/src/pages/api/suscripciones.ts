import type { APIRoute } from 'astro';

export const prerender = false;

const emailValido = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const respuesta = (mensaje: string, status: number) =>
  new Response(JSON.stringify({ mensaje }), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

export const POST: APIRoute = async ({ request }) => {
  const apiKey = import.meta.env.BREVO_API_KEY;
  const listId = Number(import.meta.env.BREVO_LIST_ID);

  if (!apiKey || !Number.isInteger(listId) || listId <= 0) {
    return respuesta('La lista de alertas todavía no está configurada.', 503);
  }

  let datos: { email?: string; consentimiento?: boolean };
  try {
    datos = await request.json();
  } catch {
    return respuesta('No hemos podido procesar el formulario.', 400);
  }

  const email = datos.email?.trim().toLowerCase();
  if (!email || !emailValido.test(email)) {
    return respuesta('Introduce un email válido.', 400);
  }
  if (!datos.consentimiento) {
    return respuesta('Necesitamos tu consentimiento para enviarte la alerta mensual.', 400);
  }

  try {
    const brevo = await fetch('https://api.brevo.com/v3/contacts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'api-key': apiKey },
      body: JSON.stringify({ email, listIds: [listId], updateEnabled: true }),
    });

    if (!brevo.ok) {
      console.error('Brevo:', brevo.status, await brevo.text());
      return respuesta('No hemos podido guardar tu suscripción. Inténtalo de nuevo.', 502);
    }

    return respuesta('¡Listo! Te avisaremos cuando haya nuevas carreras.', 201);
  } catch (error) {
    console.error('Error conectando con Brevo:', error);
    return respuesta('No hemos podido conectar con el servicio de alertas.', 502);
  }
};
