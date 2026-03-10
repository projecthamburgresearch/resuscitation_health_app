// === ZONE DRAG NAVIGATION ===
// Drag preview cards down = advance, drag history cards up = rewind.
import { getDom } from '../main';
import { advance, rewind } from './advance';
import { triggerHaptic } from '../ui/haptic';
import { createDragOverlay } from '../ui/drag-overlay';
import type { DragOverlaySession } from '../ui/drag-overlay';
import { beginDrag, clearDrag, cancelAnyDrag } from '../ui/drag-lock';

const DRAG_OWNER = 'zone';
const ADVANCE_THRESHOLD_RATIO = 0.30;
const REWIND_THRESHOLD_RATIO = 0.22;

interface DragState {
  active: boolean;
  overlay: DragOverlaySession | null;
  startY: number;
  startX: number;
  direction: 'advance' | 'rewind' | null;
  zoneHeight: number;
}

const drag: DragState = {
  active: false,
  overlay: null,
  startY: 0,
  startX: 0,
  direction: null,
  zoneHeight: 0,
};

function removePointerListeners(): void {
  document.removeEventListener('mousemove', onPointerMove as EventListener);
  document.removeEventListener('touchmove', onPointerMove as EventListener);
  document.removeEventListener('mouseup', onPointerUp as EventListener);
  document.removeEventListener('touchend', onPointerUp as EventListener);
  document.removeEventListener('touchcancel', cancelPointerDrag as EventListener);
  window.removeEventListener('blur', cancelPointerDrag);
}

function clearZoneVisuals(): void {
  const dom = getDom();
  dom.zoneTop.classList.remove('dragging');
  dom.zoneBottom.classList.remove('dragging');
  dom.activeCard.style.outline = 'none';
  dom.activeCard.style.outlineOffset = '';
}

function resetDragState(): void {
  drag.active = false;
  drag.overlay = null;
  drag.startY = 0;
  drag.startX = 0;
  drag.direction = null;
  drag.zoneHeight = 0;
}

function cleanupZoneDrag(): void {
  removePointerListeners();
  clearZoneVisuals();
  if (drag.overlay) {
    drag.overlay.cleanup();
  }
  clearDrag(DRAG_OWNER);
  resetDragState();
}

function cancelPointerDrag(): void {
  if (!drag.active) return;
  cleanupZoneDrag();
}

function commitThreshold(): number {
  if (drag.direction === 'rewind') {
    return drag.zoneHeight * REWIND_THRESHOLD_RATIO;
  }
  return drag.zoneHeight * ADVANCE_THRESHOLD_RATIO;
}

function onPointerDown(
  e: MouseEvent | TouchEvent,
  direction: 'advance' | 'rewind',
  targetElement: HTMLElement,
): void {
  if (!targetElement) return;
  if (targetElement.classList.contains('decision-option-card')) return;

  cancelAnyDrag(DRAG_OWNER);
  if (drag.active) cancelPointerDrag();

  const touch = 'touches' in e ? e.touches[0] : e;
  drag.active = true;
  drag.startY = touch.clientY;
  drag.startX = touch.clientX;
  drag.direction = direction;

  const dom = getDom();
  const zone = direction === 'advance' ? dom.zoneTop : dom.zoneBottom;
  drag.zoneHeight = zone.getBoundingClientRect().height;
  zone.classList.add('dragging');

  drag.overlay = createDragOverlay(targetElement, {
    className: 'zone-drag-ghost',
    scale: 1.03,
    zIndex: 1500,
  });

  beginDrag(DRAG_OWNER, cancelPointerDrag);

  e.preventDefault();

  document.addEventListener('mousemove', onPointerMove as EventListener);
  document.addEventListener('touchmove', onPointerMove as EventListener, { passive: false });
  document.addEventListener('mouseup', onPointerUp as EventListener);
  document.addEventListener('touchend', onPointerUp as EventListener);
  document.addEventListener('touchcancel', cancelPointerDrag as EventListener);
  window.addEventListener('blur', cancelPointerDrag);
}

function onPointerMove(e: MouseEvent | TouchEvent): void {
  if (!drag.active || !drag.overlay) return;
  e.preventDefault();

  const touch = 'touches' in e ? e.touches[0] : e;
  const dy = touch.clientY - drag.startY;
  const dx = touch.clientX - drag.startX;
  const threshold = commitThreshold();

  drag.overlay.moveBy(dx * 0.3, dy);

  const dom = getDom();
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

  const touch = 'changedTouches' in e ? e.changedTouches[0] : e;
  const dy = touch.clientY - drag.startY;
  const threshold = commitThreshold();
  const direction = drag.direction;

  let committed = false;
  if (direction === 'advance' && dy > threshold) {
    committed = advance({ source: 'zone-drag' });
  } else if (direction === 'rewind' && dy < -threshold) {
    committed = rewind();
  }

  cleanupZoneDrag();

  if (committed) {
    triggerHaptic(15);
  }
}

export function attachZoneDragListeners(): void {
  const dom = getDom();

  dom.zoneTop.addEventListener('mousedown', (e: MouseEvent) => {
    const card = (e.target as HTMLElement).closest('.preview-card-primary');
    if (card) {
      onPointerDown(e, 'advance', card as HTMLElement);
    }
  });

  dom.zoneTop.addEventListener('touchstart', (e: TouchEvent) => {
    const card = (e.target as HTMLElement).closest('.preview-card-primary');
    if (card) {
      onPointerDown(e, 'advance', card as HTMLElement);
    }
  }, { passive: false });

  dom.zoneBottom.addEventListener('mousedown', (e: MouseEvent) => {
    const card = (e.target as HTMLElement).closest('.history-card');
    if (card) {
      onPointerDown(e, 'rewind', card as HTMLElement);
    }
  });

  dom.zoneBottom.addEventListener('touchstart', (e: TouchEvent) => {
    const card = (e.target as HTMLElement).closest('.history-card');
    if (card) {
      onPointerDown(e, 'rewind', card as HTMLElement);
    }
  }, { passive: false });
}
