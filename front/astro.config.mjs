// @ts-check
import { defineConfig } from 'astro/config';
import vercel from '@astrojs/vercel';

// https://astro.build/config
export default defineConfig({
  site: 'https://carreras-murcia.vercel.app',
  output: 'server',
  adapter: vercel({ webAnalytics: { enabled: true } }),
});
