import type { APIRoute } from 'astro';
import { createClient } from '@libsql/client';
import { generarSlug } from '../utils/carreras';

export const prerender = false;

export const GET: APIRoute = async () => {
  const tursoUrl = import.meta.env.TURSO_DATABASE_URL;
  const tursoToken = import.meta.env.TURSO_AUTH_TOKEN;
  const siteUrl = 'https://carreras-murcia.vercel.app';
  const hoy = new Date().toISOString().split('T')[0];

  let carreras: Array<{ titulo: string; fecha: string }> = [];

  if (tursoUrl && tursoToken) {
    try {
      const db = createClient({ url: tursoUrl, authToken: tursoToken });
      const { rows } = await db.execute({
        sql: 'SELECT titulo, fecha FROM carreras WHERE fecha >= ? ORDER BY fecha ASC',
        args: [hoy]
      });
      carreras = rows as unknown as Array<{ titulo: string; fecha: string }>;
    } catch (error) {
      console.error('Error al generar sitemap.xml:', error);
    }
  }

  const urls = [
    `  <url>\n    <loc>${siteUrl}/</loc>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>`,
    ...carreras.map((c) => {
      const slug = generarSlug(c.titulo, c.fecha);
      return `  <url>\n    <loc>${siteUrl}/carrera/${slug}</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>`;
    })
  ];

  const sitemapXml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join('\n')}\n</urlset>`;

  return new Response(sitemapXml, {
    status: 200,
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400'
    }
  });
};

