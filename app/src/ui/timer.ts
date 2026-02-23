// === TIMER ===
import { state } from '../state/store';
import { getDom } from '../main';

export function startTimer(): void {
  state.timerRunning = true;
  state.timerInterval = setInterval(() => {
    state.timerSeconds++;
    updateTimerDisplay();
  }, 1000);
}

export function updateTimerDisplay(): void {
  const dom = getDom();
  if (!dom.timerEl) return;
  const h = Math.floor(state.timerSeconds / 3600);
  const m = Math.floor((state.timerSeconds % 3600) / 60);
  const s = state.timerSeconds % 60;
  dom.timerEl.textContent = [h, m, s].map(v => v.toString().padStart(2, '0')).join(':');
}

export function resetTimerState(): void {
  if (state.timerInterval) {
    clearInterval(state.timerInterval);
  }
  state.timerInterval = null;
  state.timerRunning = false;
  state.timerSeconds = 0;
  updateTimerDisplay();
}
