// === PWA SERVICE WORKER REGISTRATION ===
export function registerServiceWorker(): void {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js');
        console.log('SW registered:', registration.scope);
      } catch (err) {
        console.log('SW registration failed (expected in dev):', err);
      }
    });
  }
}
