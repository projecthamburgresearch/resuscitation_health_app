// === PROTOCOL LANDING PAGE ===
// Shown when no algorithm is loaded via URL param.
// Table of contents listing all available algorithms.
import { loadAlgorithmByFileName } from '../algorithms/loader';
import { applyAlgorithm, getDom } from '../main';

export function showProtocolLanding(algorithms: Array<{
  file: string;
  title: string;
  context: string;
  version: string;
}>): void {
  const dom = getDom();
  const stage = document.getElementById('stage')!;

  // Create landing overlay
  const landing = document.createElement('div');
  landing.id = 'protocol-landing';
  landing.className = 'protocol-landing';
  landing.innerHTML = `
    <div class="landing-header">
      <h2>Select Protocol</h2>
      <p>Choose a resuscitation algorithm to begin</p>
    </div>
    <div class="landing-list">
      ${algorithms.map(algo => `
        <button class="landing-item" data-file="${algo.file}">
          <div class="landing-item-title">${algo.title}</div>
          <div class="landing-item-meta">${algo.context} &middot; v${algo.version}</div>
        </button>
      `).join('')}
    </div>
  `;

  landing.addEventListener('click', async (e) => {
    const btn = (e.target as HTMLElement).closest('.landing-item') as HTMLElement;
    if (!btn) return;
    const file = btn.dataset.file;
    if (!file) return;
    try {
      const loaded = await loadAlgorithmByFileName(file);
      applyAlgorithm(loaded, file);
      landing.remove();
    } catch (err) {
      console.error('Failed to load protocol:', err);
    }
  });

  // Insert before stage
  dom.zoneTop.parentElement?.parentElement?.insertBefore(landing, stage);
  stage.style.display = 'none';

  // When algorithm loads, remove landing and show stage
  const observer = new MutationObserver(() => {
    if (!document.getElementById('protocol-landing')) {
      stage.style.display = '';
      observer.disconnect();
    }
  });
  observer.observe(document.getElementById('app')!, { childList: true });
}
