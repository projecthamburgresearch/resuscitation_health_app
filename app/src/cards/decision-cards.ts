// === DECISION DRAG-TO-CONFIRM ===
import { state, DECK } from '../state/store';
import { getDom } from '../main';
import { advance } from '../navigation/advance';

let isDraggingDecision = false;
let draggedElement: HTMLElement | null = null;
let dragStartY = 0;
let dragStartX = 0;
let originalTransform = '';

export function setupDecisionDrag(): void {
  const dom = getDom();
  const optionCards = dom.zoneTop.querySelectorAll('.decision-option-card.selected');
  optionCards.forEach(card => {
    card.addEventListener('mousedown', startDecisionDrag as EventListener);
    card.addEventListener('touchstart', startDecisionDrag as EventListener, { passive: false });
  });
}

function startDecisionDrag(e: MouseEvent | TouchEvent): void {
  const card = DECK[state.currentId];
  if (!card || card.type !== 'decision') return;

  isDraggingDecision = true;
  draggedElement = e.currentTarget as HTMLElement;
  originalTransform = draggedElement.style.transform;

  const touch = 'touches' in e ? e.touches[0] : e;
  dragStartY = touch.clientY;
  dragStartX = touch.clientX;

  e.preventDefault();
  e.stopPropagation();

  document.addEventListener('mousemove', onDecisionDrag as EventListener);
  document.addEventListener('touchmove', onDecisionDrag as EventListener, { passive: false });
  document.addEventListener('mouseup', endDecisionDrag as EventListener);
  document.addEventListener('touchend', endDecisionDrag as EventListener);
}

function onDecisionDrag(e: MouseEvent | TouchEvent): void {
  if (!isDraggingDecision || !draggedElement) return;
  e.preventDefault();

  const dom = getDom();
  const touch = 'touches' in e ? e.touches[0] : e;
  const dy = touch.clientY - dragStartY;
  const dx = touch.clientX - dragStartX;

  draggedElement.style.transform = `translate(${dx}px, ${dy}px) scale(1.05)`;
  draggedElement.style.zIndex = '100';
  draggedElement.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';

  if (dy > 30) {
    dom.activeCard.style.outline = '3px dashed #666';
  } else {
    dom.activeCard.style.outline = 'none';
  }
}

function endDecisionDrag(e: MouseEvent | TouchEvent): void {
  if (!isDraggingDecision) return;

  document.removeEventListener('mousemove', onDecisionDrag as EventListener);
  document.removeEventListener('touchmove', onDecisionDrag as EventListener);
  document.removeEventListener('mouseup', endDecisionDrag as EventListener);
  document.removeEventListener('touchend', endDecisionDrag as EventListener);

  const dom = getDom();
  const touch = 'changedTouches' in e ? e.changedTouches[0] : e;
  const dy = touch.clientY - dragStartY;

  dom.activeCard.style.outline = 'none';

  if (dy > 60 && state.decisionTapped) {
    advance({ source: 'decision-confirm', splitConfirmed: true });
  } else {
    if (draggedElement) {
      draggedElement.style.transform = originalTransform || '';
      draggedElement.style.zIndex = '10';
      draggedElement.style.boxShadow = '';
    }
  }

  isDraggingDecision = false;
  draggedElement = null;
}
