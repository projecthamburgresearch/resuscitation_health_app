// === MAIN ENTRY POINT ===
import './styles/tokens.css';
import './styles/layout.css';
import './styles/wheel.css';
import './styles/cards.css';
import './styles/stack.css';
import './styles/ticker.css';
import './styles/menu.css';
import './styles/responsive.css';

import type { Algorithm } from './types';
import { state, DECK, RUNTIME_ALGORITHM, rebuildDeckMap, setRuntimeAlgorithm, setActiveAlgorithmSource } from './state/store';
import { isSplitDecisionCard } from './state/decisions';
import { normalizeAlgorithm, sanitizeAlgorithmFile, loadAlgorithmByFileName, discoverAvailableAlgorithmFiles, DEFAULT_ALGORITHM_FILES, getDefaultAlgorithm } from './algorithms/loader';
import { computeWheelMode } from './wheel/fsm';
import { updateDimensions } from './wheel/physics';
import { setupKnobListeners } from './wheel/knob';
import { currentAlgorithmStartId } from './navigation/anchors';
import { attachZoneDragListeners } from './navigation/zone-drag';
import { advance, canTapAdvance } from './navigation/advance';
import { resetTimerState } from './ui/timer';
import { closeModal } from './ui/modal';
import { render } from './cards/renderer';
import { _setRenderFn } from './cards/preview-zone';
import { setupWardenAutomation } from './automation';
import { initTicker } from './ticker/engine';
import { initMenu, applySavedSettings } from './ui/menu';
import { registerServiceWorker } from './pwa/register';

// === DOM REFERENCES ===
interface DomRefs {
  zoneTop: HTMLElement;
  zoneBottom: HTMLElement;
  activeCard: HTMLElement;
  knob: HTMLElement;
  wheel: HTMLElement;
  checklistArea: HTMLElement;
  timerEl: HTMLElement;
  tickerText: HTMLElement;
  modalOverlay: HTMLElement;
}

let dom: DomRefs | null = null;

export function getDom(): DomRefs {
  if (!dom) {
    dom = {
      zoneTop: document.getElementById('zone-top')!,
      zoneBottom: document.getElementById('zone-bottom')!,
      activeCard: document.getElementById('active-card')!,
      knob: document.getElementById('knob')!,
      wheel: document.getElementById('wheel')!,
      checklistArea: document.getElementById('checklist-area')!,
      timerEl: document.getElementById('timer')!,
      tickerText: document.getElementById('ticker-text')!,
      modalOverlay: document.getElementById('modal-overlay')!,
    };
  }
  return dom;
}

// === ALGORITHM APPLICATION ===
export function syncHeaderFromAlgorithm(): void {
  const titleEl = document.querySelector('.app-title');
  if (!titleEl) return;
  const title = RUNTIME_ALGORITHM && RUNTIME_ALGORITHM.algorithm_meta
    ? RUNTIME_ALGORITHM.algorithm_meta.title
    : '';
  titleEl.textContent = title || 'Resuscitation Handbook';
}

export function applyAlgorithm(rawAlgorithm: unknown, sourceLabel?: string): {
  ok: boolean;
  source: string;
  algorithm_id: string | null;
  card_count: number;
} {
  const algo = normalizeAlgorithm(rawAlgorithm);
  setRuntimeAlgorithm(algo);
  setActiveAlgorithmSource(sourceLabel || 'inline-default');
  rebuildDeckMap(algo.deck);
  state.currentId = currentAlgorithmStartId() || 'CARD_00_START';
  state.history = [];
  state.decisionIndex = 0;
  state.decisionRecords = {};
  state.decisionTrail = [];
  state.decisionTapped = false;
  state.carouselIndex = 0;
  state.checklistState = {};
  state.anchors = [];
  state.anchorIndex = 0;
  state.wheel.dragOrigin = null;
  state.wheel.navConsumed = false;

  if (state.currentId && DECK[state.currentId]) {
    state.wheel.mode = computeWheelMode(DECK[state.currentId]);
  } else {
    state.wheel.mode = 'LINEAR';
  }
  state.wheel.angle = 330;
  state.wheel.visualAngle = 330;

  resetTimerState();
  syncHeaderFromAlgorithm();
  render();
  return {
    ok: true,
    source: sourceLabel || 'inline-default',
    algorithm_id: algo.algorithm_meta && algo.algorithm_meta.id
      ? algo.algorithm_meta.id
      : null,
    card_count: algo.deck.length,
  };
}

async function initAlgorithmFromUrl(): Promise<void> {
  const params = new URLSearchParams(window.location.search);
  const requested = sanitizeAlgorithmFile(params.get('algo'));
  if (requested) {
    try {
      const loaded = await loadAlgorithmByFileName(requested);
      applyAlgorithm(loaded, requested);
      return;
    } catch (err) {
      console.error(err);
    }
  }

  try {
    const available = await discoverAvailableAlgorithmFiles();
    const preferred = DEFAULT_ALGORITHM_FILES.find((file) => available.includes(file))
      || available[0]
      || null;
    if (preferred) {
      const loaded = await loadAlgorithmByFileName(preferred);
      applyAlgorithm(loaded, preferred);
      return;
    }
  } catch (err) {
    console.error(err);
  }

  applyAlgorithm(getDefaultAlgorithm(), 'inline-default-fallback');
}

// === INIT ===
function init(): void {
  // Cache DOM refs
  getDom();

  // Wire circular dependency
  _setRenderFn(render);

  // Responsive dimensions
  updateDimensions();
  window.addEventListener('resize', updateDimensions);

  // Knob drag listeners
  setupKnobListeners();

  // Zone drag (swipe preview/history cards to navigate)
  attachZoneDragListeners();

  const d = getDom();

  // Ticker coach
  initTicker(d.tickerText);

  // Wheel tap = advance
  d.wheel.addEventListener('click', (e: MouseEvent) => {
    if (e.target === d.knob) return;
    const card = DECK[state.currentId];
    if (!canTapAdvance(card)) return;
    advance({ source: 'wheel-tap' });
  });

  // Knob tap = advance
  d.knob.addEventListener('click', () => {
    const card = DECK[state.currentId];
    if (!canTapAdvance(card)) return;
    advance({ source: 'knob-tap' });
  });

  // Carousel click on active card
  d.activeCard.addEventListener('click', (e: MouseEvent) => {
    const card = DECK[state.currentId];
    if (!card) return;
    if (card.type === 'carousel_action' && card.content.slides && card.content.slides.length > 1) {
      const rect = d.activeCard.getBoundingClientRect();
      const x = e.clientX - rect.left;

      if (x > rect.width / 2) {
        state.carouselIndex = (state.carouselIndex + 1) % card.content.slides.length;
      } else {
        state.carouselIndex = (state.carouselIndex - 1 + card.content.slides.length) % card.content.slides.length;
      }
      render();
    }
  });

  // Modal close (click overlay)
  d.modalOverlay.addEventListener('click', (e: MouseEvent) => {
    if (e.target === d.modalOverlay) closeModal();
  });

  // Modal close button
  const closeBtn = d.modalOverlay.querySelector('.modal-close');
  if (closeBtn) closeBtn.addEventListener('click', closeModal);

  // Prevent modal content clicks from closing
  const modalContent = d.modalOverlay.querySelector('.modal-content');
  if (modalContent) modalContent.addEventListener('click', (e: Event) => e.stopPropagation());

  // Menu & settings
  initMenu();
  applySavedSettings();

  // Warden automation API
  setupWardenAutomation();

  // PWA service worker
  registerServiceWorker();

  // Load algorithm
  initAlgorithmFromUrl();
}

// Start
init();
