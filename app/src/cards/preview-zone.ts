// === PREVIEW ZONE RENDERING ===
import type { Card } from '../types';
import { state, DECK } from '../state/store';
import { getDom } from '../main';
import { setupDecisionDrag } from './decision-cards';
import { normalizeDecisionIndexForCard } from '../state/decisions';

// Lazy import to break circular dependency
let _render: (() => void) | null = null;
export function _setRenderFn(fn: () => void): void {
  _render = fn;
}

export function renderPreviewZone(card: Card): void {
  const dom = getDom();
  dom.zoneTop.innerHTML = '';
  dom.zoneTop.classList.remove('decision-mode');

  // DECISION MODE: Two options side-by-side with preview stacks
  if (card.type === 'decision' && card.transitions && card.transitions.type === 'split') {
    dom.zoneTop.classList.add('decision-mode');

    const options = card.transitions.options;

    options.forEach((opt, idx) => {
      const isSelected = state.decisionTapped && idx === state.decisionIndex;

      const optContainer = document.createElement('div');
      optContainer.className = `decision-option-container ${isSelected ? 'selected' : ''}`;
      optContainer.dataset.optionIndex = String(idx);

      const targetCard = DECK[opt.target_id];
      const previewStack = targetCard ? getUpcomingCardsFrom(opt.target_id, 3) : [];

      if (isSelected && previewStack.length > 0) {
        [...previewStack].reverse().forEach((pc, pi) => {
          const depth = previewStack.length - pi;
          const stackCard = document.createElement('div');
          stackCard.className = 'card preview-stack-card';
          stackCard.style.transform = `translateY(${-depth * 8}px) scale(${1 - depth * 0.04})`;
          stackCard.style.zIndex = String(5 - depth);
          stackCard.innerHTML = `<div class="card-header small">${pc.content.title}</div>`;
          optContainer.appendChild(stackCard);
        });
      }

      const optCard = document.createElement('div');
      optCard.className = `card decision-option-card ${isSelected ? 'selected' : ''}`;
      optCard.style.zIndex = '10';
      optCard.innerHTML = `
        <div class="card-header">${card.content.title}</div>
        <div class="card-body small">${card.content.body || ''}</div>
        <div class="option-badge">${opt.label}</div>
      `;

      optCard.onclick = (e) => {
        e.stopPropagation();
        selectDecisionOption(idx);
      };

      optContainer.appendChild(optCard);
      dom.zoneTop.appendChild(optContainer);
    });

    setupDecisionDrag();
    return;
  }

  // LINEAR MODE: Vertical stack
  const upcoming = getUpcomingCards(card, 3);
  [...upcoming].reverse().forEach((c, i) => {
    const depth = upcoming.length - 1 - i;
    const el = document.createElement('div');
    el.className = 'card preview-card';
    el.style.setProperty('--depth', String(depth));
    el.style.zIndex = String(10 - depth);

    let iconHtml = '';
    if (c.type === 'decision') {
      iconHtml = '<svg class="decision-indicator"><use href="#icon-decision"/></svg>';
    }

    el.innerHTML = `
      ${iconHtml}
      <div class="card-header">${c.content.title}</div>
    `;

    dom.zoneTop.appendChild(el);
  });
}

function selectDecisionOption(idx: number): void {
  const card = DECK[state.currentId];
  if (!card) return;
  state.decisionIndex = normalizeDecisionIndexForCard(card, idx);
  state.decisionTapped = true;
  if (_render) _render();
}

function getUpcomingCardsFrom(startId: string, max: number): Card[] {
  const result: Card[] = [];
  let currentId: string | null = startId;

  while (currentId && result.length < max && DECK[currentId]) {
    const currentCard: Card = DECK[currentId];
    result.push(currentCard);

    if (currentCard.transitions) {
      if (currentCard.transitions.type === 'linear') {
        currentId = currentCard.transitions.next_id;
      } else if (currentCard.transitions.type === 'split' && currentCard.transitions.options[0]) {
        currentId = currentCard.transitions.options[0].target_id;
      } else {
        break;
      }
    } else {
      break;
    }
  }
  return result;
}

function getUpcomingCards(card: Card, max: number): Card[] {
  let nextId: string | null = null;

  if (card.transitions) {
    if (card.transitions.type === 'linear') {
      nextId = card.transitions.next_id;
    } else if (card.transitions.type === 'split' && card.transitions.options[0]) {
      nextId = card.transitions.options[0].target_id;
    }
  }

  return nextId ? getUpcomingCardsFrom(nextId, max) : [];
}
