import { defineConfig } from 'vite';
import { resolve } from 'path';
import { copyFileSync, mkdirSync, readdirSync } from 'fs';

// Copy algorithms and icons to public for production builds
function copyStaticAssets() {
  return {
    name: 'copy-static-assets',
    writeBundle() {
      const root = __dirname;
      const outDir = resolve(root, 'dist');

      const algSrc = resolve(root, 'algorithms');
      const algDest = resolve(outDir, 'algorithms');
      const iconSrc = resolve(root, 'icons');
      const iconDest = resolve(outDir, 'icons');
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

      // Dev-mode overlay: single source in app/dev-mode/ so built dist has parity
      try {
        mkdirSync(resolve(outDir, 'dev-mode'), { recursive: true });
        copyFileSync(
          resolve(root, 'dev-mode/dev-mode-overlay.js'),
          resolve(outDir, 'dev-mode/dev-mode-overlay.js')
        );
      } catch { /* ignore */ }
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
    rollupOptions: {
      input: ['index.html', 'dev-mode/index.html'],
    },
  },
  plugins: [copyStaticAssets()],
});
