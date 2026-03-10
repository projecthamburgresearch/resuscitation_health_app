// === DECISION DRAG-TO-CONFIRM ===
// Uses a drag ghost (clone) appended to body so it always renders above zone-middle.
// Original stays in place (hidden) — no put-back logic, no stuck cards.
import { state, DECK } from '../state/store';
import { getDom } from '../main';
import { advance } from '../navigation/advance';

let isDraggingDecision = false;
let dragGhost: HTMLElement | null = null;
let originalElement: HTMLElement | null = null;
let originalTransform = '';
let dragStartY = 0;
let dragStartX = 0;

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

  originalElement = e.currentTarget as HTMLElement;
  const touch = 'touches' in e ? e.touches[0] : e;
  dragStartY = touch.clientY;
  dragStartX = touch.clientX;
  const rect = originalElement.getBoundingClientRect();

  // Clone for drag ghost — always in body, guaranteed above everything
  const ghost = originalElement.cloneNode(true) as HTMLElement;
  ghost.style.cssText = `
    position: fixed;
    left: ${rect.left}px;
    top: ${rect.top}px;
    width: ${rect.width}px;
    height: ${rect.height}px;
    margin: 0;
    transform: translate(0, 0) scale(1.05);
    z-index: 999999;
    box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    pointer-events: none;
  `;
  document.body.appendChild(ghost);

  // Hide original so only ghost is visible during drag
  originalElement.style.visibility = 'hidden';

  isDraggingDecision = true;
  dragGhost = ghost;

  e.preventDefault();
  e.stopPropagation();

  document.addEventListener('mousemove', onDecisionDrag as EventListener);
  document.addEventListener('touchmove', onDecisionDrag as EventListener, { passive: false });
  document.addEventListener('mouseup', endDecisionDrag as EventListener);
  document.addEventListener('touchend', endDecisionDrag as EventListener);
}

function onDecisionDrag(e: MouseEvent | TouchEvent): void {
  if (!isDraggingDecision || !dragGhost) return;
  e.preventDefault();

  const dom = getDom();
  const touch = 'touches' in e ? e.touches[0] : e;
  const dy = touch.clientY - dragStartY;
  const dx = touch.clientX - dragStartX;

  dragGhost.style.transform = `translate(${dx}px, ${dy}px) scale(1.05)`;

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
    // Element stays in body; render will replace zone content
  const dy = touch.clientY - dragStartY;

  dom.activeCard.style.outline = 'none';

  // Always remove ghost and unhide original
  if (dragGhost?.parentElement) {
    dragGhost.remove();
  }
  if (originalElement) {
    if (draggedElement?.parentElement) {
  } else if (draggedElement && originalParent) {
    // Put element back and restore styles
    originalParent.insertBefore(draggedElement, originalNextSibling);
    draggedElement.style.position = '';
    draggedElement.style.left = '';
    draggedElement.style.top = '';
    draggedElement.style.width = '';
    draggedElement.style.height = '';
    draggedElement.style.margin = '';
    draggedElement.style.transform = originalTransform || '';
    draggedElement.style.zIndex = '';
    draggedElement.style.boxShadow = '';
      draggedElement.remove();
    }
    originalElement.style.visibility = '';
  }

  if (dy > 60 && state.decisionTapped) {
    advance({ source: 'decision-confirm', splitConfirmed: true });
  }

  isDraggingDecision = false;
  dragGhost = null;
  originalElement = null;
}
