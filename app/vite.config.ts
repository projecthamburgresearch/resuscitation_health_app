import { defineConfig } from 'vite';
import { resolve } from 'path';
import { copyFileSync, mkdirSync, readdirSync } from 'fs';

// Copy algorithms and icons to public for production builds
function copyStaticAssets() {
  return {
    name: 'copy-static-assets',
    writeBundle() {
      const algSrc = resolve(__dirname, 'algorithms');
      const algDest = resolve(__dirname, 'dist/algorithms');
      const iconSrc = resolve(__dirname, 'icons');
      const iconDest = resolve(__dirname, 'dist/icons');
      try {
        mkdirSync(algDest, { recursive: true });
        for (const f of readdirSync(algSrc)) {
          copyFileSync(resolve(algSrc, f), resolve(algDest, f));
        }
        mkdirSync(iconDest, { recursive: true });
        for (const f of readdirSync(iconSrc)) {
          copyFileSync(resolve(iconSrc, f), resolve(iconDest, f));
        }
      } catch { /* ignore if dirs don't exist */ }
    },
  };
}

// GitHub Pages serves at https://<user>.github.io/<repo>/ so we need a base path in production
const base = process.env.BASE_PATH ?? '/';

export default defineConfig({
  base,
  root: '.',
  publicDir: 'public',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    open: false,
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  plugins: [copyStaticAssets()],
});
