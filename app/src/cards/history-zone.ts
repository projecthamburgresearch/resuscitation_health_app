// === HISTORY ZONE RENDERING ===
import { state, DECK } from '../state/store';
import { getDom } from '../main';

export function renderHistoryZone(): void {
  const dom = getDom();
  dom.zoneBottom.innerHTML = '';

  const recent = state.history.slice(-3);
  recent.forEach((id, i, arr) => {
    const c = DECK[id];
    if (!c) return;

    const depth = arr.length - 1 - i;
    const el = document.createElement('div');
    el.className = 'card history-card';
    el.style.setProperty('--depth', String(depth));
    el.style.zIndex = String(10 - depth);
    el.innerHTML = `<div class="card-header">${c.content.title}</div>`;
    dom.zoneBottom.appendChild(el);
  });
}
