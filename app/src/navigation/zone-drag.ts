// === ZONE DRAG NAVIGATION ===
// Drag preview cards down = advance, drag history cards up = rewind
import { state, DECK } from '../state/store';
import { getDom } from '../main';
import { advance, rewind } from './advance';
import { triggerHaptic } from '../ui/haptic';

const ZONE_THRESHOLD_RATIO = 0.35; // 35% of zone height to commit

interface DragState {
  active: boolean;
  element: HTMLElement | null;
  startY: number;
  startX: number;
  direction: 'advance' | 'rewind' | null;
  zoneHeight: number;
  originalTransform: string;
}

const drag: DragState = {
  active: false,
  element: null,
  startY: 0,
  startX: 0,
  direction: null,
  zoneHeight: 0,
  originalTransform: '',
};

function onPointerDown(e: MouseEvent | TouchEvent, direction: 'advance' | 'rewind'): void {
  const target = e.currentTarget as HTMLElement;
  if (!target) return;

  // Don't interfere with decision card drag
  if (target.classList.contains('decision-option-card')) return;

  const touch = 'touches' in e ? e.touches[0] : e;
  drag.active = true;
  drag.element = target;
  drag.startY = touch.clientY;
  drag.startX = touch.clientX;
  drag.direction = direction;
  drag.originalTransform = target.style.transform;

  const dom = getDom();
  const zone = direction === 'advance' ? dom.zoneTop : dom.zoneBottom;
  drag.zoneHeight = zone.getBoundingClientRect().height;

  e.preventDefault();

  document.addEventListener('mousemove', onPointerMove as EventListener);
  document.addEventListener('touchmove', onPointerMove as EventListener, { passive: false });
  document.addEventListener('mouseup', onPointerUp as EventListener);
  document.addEventListener('touchend', onPointerUp as EventListener);
}

function onPointerMove(e: MouseEvent | TouchEvent): void {
  if (!drag.active || !drag.element) return;
  e.preventDefault();

  const touch = 'touches' in e ? e.touches[0] : e;
  const dy = touch.clientY - drag.startY;
  const dx = touch.clientX - drag.startX;

  // Small tilt based on drag distance
  const tiltX = Math.max(-10, Math.min(10, dy * 0.08));

  drag.element.style.transform = `translate(${dx * 0.3}px, ${dy}px) rotateX(${-tiltX}deg) scale(1.03)`;
  drag.element.style.zIndex = '100';
  drag.element.style.transition = 'none';

  // Highlight active card zone when crossing threshold
  const dom = getDom();
  const threshold = drag.zoneHeight * ZONE_THRESHOLD_RATIO;
  const crossed = drag.direction === 'advance' ? dy > threshold : dy < -threshold;

  if (crossed) {
    dom.activeCard.style.outline = '3px dashed var(--accent-red)';
    dom.activeCard.style.outlineOffset = '4px';
  } else {
    dom.activeCard.style.outline = 'none';
    dom.activeCard.style.outlineOffset = '';
  }
}

function onPointerUp(e: MouseEvent | TouchEvent): void {
  if (!drag.active) return;

  document.removeEventListener('mousemove', onPointerMove as EventListener);
  document.removeEventListener('touchmove', onPointerMove as EventListener);
  document.removeEventListener('mouseup', onPointerUp as EventListener);
  document.removeEventListener('touchend', onPointerUp as EventListener);

  const dom = getDom();
  dom.activeCard.style.outline = 'none';
  dom.activeCard.style.outlineOffset = '';

  const touch = 'changedTouches' in e ? e.changedTouches[0] : e;
  const dy = touch.clientY - drag.startY;
  const threshold = drag.zoneHeight * ZONE_THRESHOLD_RATIO;

  let committed = false;
  if (drag.direction === 'advance' && dy > threshold) {
    committed = advance({ source: 'zone-drag' });
  } else if (drag.direction === 'rewind' && dy < -threshold) {
    committed = rewind();
  }

  if (committed) {
    triggerHaptic(15);
  } else if (drag.element) {
    // Rubber-band snap back
    drag.element.style.transition = 'transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)';
    drag.element.style.transform = drag.originalTransform;
    drag.element.style.zIndex = '';
  }

  drag.active = false;
  drag.element = null;
  drag.direction = null;
}

export function attachZoneDragListeners(): void {
  // Use event delegation on the zone containers
  const dom = getDom();

  // Preview cards: drag down = advance
  dom.zoneTop.addEventListener('mousedown', (e: MouseEvent) => {
    const card = (e.target as HTMLElement).closest('.preview-card');
    if (card && !card.classList.contains('decision-option-card')) {
      onPointerDown(e, 'advance');
    }
  });
  dom.zoneTop.addEventListener('touchstart', (e: TouchEvent) => {
    const card = (e.target as HTMLElement).closest('.preview-card');
    if (card && !card.classList.contains('decision-option-card')) {
      // Set the drag element to the card
      drag.element = card as HTMLElement;
      onPointerDown(e, 'advance');
    }
  }, { passive: false });

  // History cards: drag up = rewind
  dom.zoneBottom.addEventListener('mousedown', (e: MouseEvent) => {
    const card = (e.target as HTMLElement).closest('.history-card');
    if (card) {
      onPointerDown(e, 'rewind');
    }
  });
  dom.zoneBottom.addEventListener('touchstart', (e: TouchEvent) => {
    const card = (e.target as HTMLElement).closest('.history-card');
    if (card) {
      drag.element = card as HTMLElement;
      onPointerDown(e, 'rewind');
    }
  }, { passive: false });
}
