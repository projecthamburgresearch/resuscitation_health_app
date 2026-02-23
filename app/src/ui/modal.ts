// === TOOLBOX / MODAL ===
import { getDom } from '../main';

export function openToolbox(): void {
  const dom = getDom();
  dom.modalOverlay.classList.add('visible');
}

export function closeModal(): void {
  const dom = getDom();
  dom.modalOverlay.classList.remove('visible');
}

export function openFullscreen(): void {
  alert('Fullscreen mode - would expand card details');
}
