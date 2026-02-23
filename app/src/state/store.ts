// === STATE STORE ===
import type { AppState, Algorithm, DeckMap } from '../types';

// Global mutable state
export const state: AppState = {
  currentId: 'CARD_00_START',
  history: [],
  decisionIndex: 0,
  decisionRecords: {},
  decisionTrail: [],
  decisionTapped: false,
  carouselIndex: 0,
  timerSeconds: 0,
  timerRunning: false,
  timerInterval: null,
  checklistState: {},
  anchors: [],
  anchorIndex: 0,
  wheel: {
    mode: 'COVER',
    angle: 330,
    visualAngle: 330,
    dragOrigin: null,
    navConsumed: false,
  },
};

// The runtime algorithm (mutable, replaced on load)
export let RUNTIME_ALGORITHM: Algorithm = {
  algorithm_meta: {},
  deck: [],
};

export function setRuntimeAlgorithm(algo: Algorithm): void {
  RUNTIME_ALGORITHM = algo;
}

// Active algorithm source label
export let ACTIVE_ALGORITHM_SOURCE = 'inline-default';

export function setActiveAlgorithmSource(source: string): void {
  ACTIVE_ALGORITHM_SOURCE = source;
}

// The deck map: card.id → Card (rebuilt on algorithm load)
export const DECK: DeckMap = {};

export function rebuildDeckMap(cards: Algorithm['deck']): void {
  for (const key of Object.keys(DECK)) {
    delete DECK[key];
  }
  for (const card of cards) {
    DECK[card.id] = card;
  }
}
