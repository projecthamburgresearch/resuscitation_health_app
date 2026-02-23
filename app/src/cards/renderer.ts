// === RENDER ENGINE ===
import type { Card } from '../types';
import { state, DECK } from '../state/store';
import { computeWheelMode } from '../wheel/fsm';
import { setKnobPosition } from '../wheel/physics';
import { syncAnchors, currentAnchorAngle } from '../navigation/anchors';
import { getDom } from '../main';
import { renderPreviewZone } from './preview-zone';
import { renderHistoryZone } from './history-zone';
import { renderChecklist } from './checklist';
import { openToolbox, openFullscreen } from '../ui/modal';
import { updateTicker } from '../ticker/engine';

export function render(): void {
  const card = DECK[state.currentId];
  if (!card) return;

  // 1. Derive wheel mode
  state.wheel.mode = computeWheelMode(card);

  // 2. Anchor-point model
  syncAnchors();
  state.wheel.angle = currentAnchorAngle();
  setKnobPosition(state.wheel.angle);

  // 3. Rendering pipeline
  renderActiveCard(card);
  renderPreviewZone(card);
  renderHistoryZone();
  renderChecklist(card);

  // 4. Ticker coach
  updateTicker();
}

let lastRenderedCardId: string | null = null;

function renderActiveCard(card: Card): void {
  const dom = getDom();
  const el = dom.activeCard;
  const cardChanged = lastRenderedCardId !== card.id;
  lastRenderedCardId = card.id;

  el.className = '';

  if (card.type === 'cover') {
    el.classList.add('cover-mode');
  }

  if (card.wheel_config.animation === 'pulse' || card.type === 'loop_start') {
    el.classList.add('loop-mode');
  }

  // Trigger entrance animation when navigating to a new card
  if (cardChanged && card.type !== 'cover') {
    el.classList.add('card-enter');
    el.addEventListener('animationend', () => {
      el.classList.remove('card-enter');
    }, { once: true });
  }

  let html = '';

  if (card.type === 'cover') {
    html = `
      <div class="cover-content">
        <div class="cover-title">${card.content.title}</div>
        <div class="cover-subtitle">${card.content.subtitle || ''}</div>
      </div>
    `;
  } else {
    const hasToolbox = card.toolbox && card.toolbox.length > 0;
    const hasSlides = card.content.slides && card.content.slides.length > 1;

    html = `
      <svg class="card-icon icon-tr" data-action="fullscreen"><use href="#icon-fullscreen"/></svg>
      ${hasToolbox ? '<svg class="card-icon icon-bl" data-action="toolbox"><use href="#icon-toolbox"/></svg>' : ''}

      <div class="card-header">${card.type.replace('_', ' ')}</div>
      <div class="card-title">${card.content.title}</div>
      <div class="card-body">${getCardBodyContent(card)}</div>

      ${hasSlides ? renderCarouselDots(card.content.slides!.length) : ''}
    `;
  }

  el.innerHTML = html;

  // Bind event listeners (replacing inline onclick)
  const fullscreenBtn = el.querySelector('[data-action="fullscreen"]');
  if (fullscreenBtn) fullscreenBtn.addEventListener('click', openFullscreen);

  const toolboxBtn = el.querySelector('[data-action="toolbox"]');
  if (toolboxBtn) toolboxBtn.addEventListener('click', openToolbox);
}

function getCardBodyContent(card: Card): string {
  if (card.content.slides && card.content.slides.length > 0) {
    if (card.type === 'carousel_action' && card.content.slides.length > 1) {
      const slide = card.content.slides[state.carouselIndex] || card.content.slides[0];
      return `<strong>${slide.header || slide.label}</strong><br>${slide.text}`;
    } else if (card.content.slides[0]) {
      const slide = card.content.slides[0];
      return slide.text || card.content.body || '';
    }
  }
  return card.content.body || '';
}

function renderCarouselDots(count: number): string {
  let dots = '';
  for (let i = 0; i < count; i++) {
    dots += `<div class="dot ${i === state.carouselIndex ? 'active' : ''}"></div>`;
  }
  return `<div class="carousel-dots">${dots}</div>`;
}
