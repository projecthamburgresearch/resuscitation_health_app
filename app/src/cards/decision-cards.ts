// === DECISION DRAG-TO-CONFIRM ===
import { state, DECK } from '../state/store';
import { getDom } from '../main';
import { advance } from '../navigation/advance';
import { createDragOverlay } from '../ui/drag-overlay';
import type { DragOverlaySession } from '../ui/drag-overlay';
import { beginDrag, clearDrag, cancelAnyDrag } from '../ui/drag-lock';

const DRAG_OWNER = 'decision';

let isDraggingDecision = false;
let dragOverlay: DragOverlaySession | null = null;
let dragStartY = 0;
let dragStartX = 0;

export function setupDecisionDrag(): void {
  const dom = getDom();
  const optionCards = dom.zoneTop.querySelectorAll('.decision-option-card.selected');
  optionCards.forEach((card) => {
    card.addEventListener('mousedown', startDecisionDrag as EventListener);
    card.addEventListener('touchstart', startDecisionDrag as EventListener, { passive: false });
  });
}

function removeDecisionDragListeners(): void {
  document.removeEventListener('mousemove', onDecisionDrag as EventListener);
  document.removeEventListener('touchmove', onDecisionDrag as EventListener);
  document.removeEventListener('mouseup', endDecisionDrag as EventListener);
  document.removeEventListener('touchend', endDecisionDrag as EventListener);
  document.removeEventListener('touchcancel', cancelDecisionDrag as EventListener);
  window.removeEventListener('blur', cancelDecisionDrag);
}

function cleanupDecisionDragVisuals(): void {
  const dom = getDom();
  dom.activeCard.style.outline = 'none';
  if (dragOverlay) {
    dragOverlay.cleanup();
  }
}

function resetDecisionDragState(): void {
  isDraggingDecision = false;
  dragOverlay = null;
  dragStartY = 0;
  dragStartX = 0;
}

function cancelDecisionDrag(): void {
  if (!isDraggingDecision) return;
  removeDecisionDragListeners();
  cleanupDecisionDragVisuals();
  clearDrag(DRAG_OWNER);
  resetDecisionDragState();
}

function startDecisionDrag(e: MouseEvent | TouchEvent): void {
  const card = DECK[state.currentId];
  if (!card || card.type !== 'decision') return;

  cancelAnyDrag(DRAG_OWNER);
  if (isDraggingDecision) cancelDecisionDrag();

  const originalElement = e.currentTarget as HTMLElement | null;
  if (!originalElement) return;
  if (!originalElement.classList.contains('selected')) return;

  const touch = 'touches' in e ? e.touches[0] : e;
  dragStartY = touch.clientY;
  dragStartX = touch.clientX;

  dragOverlay = createDragOverlay(originalElement, {
    className: 'decision-drag-ghost',
    scale: 1.05,
    zIndex: 1650,
  });

  isDraggingDecision = true;
  beginDrag(DRAG_OWNER, cancelDecisionDrag);

  e.preventDefault();
  e.stopPropagation();

  document.addEventListener('mousemove', onDecisionDrag as EventListener);
  document.addEventListener('touchmove', onDecisionDrag as EventListener, { passive: false });
  document.addEventListener('mouseup', endDecisionDrag as EventListener);
  document.addEventListener('touchend', endDecisionDrag as EventListener);
  document.addEventListener('touchcancel', cancelDecisionDrag as EventListener);
  window.addEventListener('blur', cancelDecisionDrag);
}

function onDecisionDrag(e: MouseEvent | TouchEvent): void {
  if (!isDraggingDecision || !dragOverlay) return;
  e.preventDefault();

  const dom = getDom();
  const touch = 'touches' in e ? e.touches[0] : e;
  const dy = touch.clientY - dragStartY;
  const dx = touch.clientX - dragStartX;

  dragOverlay.moveBy(dx, dy);

  if (dy > 30) {
    dom.activeCard.style.outline = '3px dashed #666';
  } else {
    dom.activeCard.style.outline = 'none';
  }
}

function endDecisionDrag(e: MouseEvent | TouchEvent): void {
  if (!isDraggingDecision) return;

  removeDecisionDragListeners();

  const touch = 'changedTouches' in e ? e.changedTouches[0] : e;
  const dy = touch.clientY - dragStartY;
  const shouldAdvance = dy > 60 && state.decisionTapped;

  cleanupDecisionDragVisuals();

  if (shouldAdvance) {
    advance({ source: 'decision-confirm', splitConfirmed: true });
  }

  clearDrag(DRAG_OWNER);
  resetDecisionDragState();
}
