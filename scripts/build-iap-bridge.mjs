import { build } from 'esbuild';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const entry = resolve(root, 'node_modules/capacitor-plugin-cdv-purchase/dist/index.js');
const outfile = resolve(root, 'www/cdv-purchase.bundle.js');

await build({
  entryPoints: [entry],
  outfile,
  bundle: true,
  format: 'iife',
  globalName: '__CdvPurchaseModule',
  platform: 'browser',
  target: ['es2020'],
  minify: true,
  sourcemap: false,
  legalComments: 'none',
});

console.log(`IAP native bridge bundle created: ${outfile}`);
