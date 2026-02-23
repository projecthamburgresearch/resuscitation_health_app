// === TICKER ENGINE ===
import { evaluateTickerRules } from './rules';

let lastMessage = '';
let tickerEl: HTMLElement | null = null;

export function initTicker(element: HTMLElement): void {
  tickerEl = element;
}

export function updateTicker(): void {
  if (!tickerEl) return;

  const result = evaluateTickerRules();

  if (result.text !== lastMessage) {
    lastMessage = result.text;

    // Fade transition
    tickerEl.classList.add('ticker-fade-out');
    setTimeout(() => {
      if (!tickerEl) return;
      tickerEl.textContent = result.text;
      tickerEl.classList.remove('ticker-fade-out');
      tickerEl.classList.add('ticker-fade-in');
      setTimeout(() => {
        if (tickerEl) tickerEl.classList.remove('ticker-fade-in');
      }, 300);
    }, 200);
  }
}
