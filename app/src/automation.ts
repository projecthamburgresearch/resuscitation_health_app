// === WARDEN AUTOMATION API ===
import type { AutomationSnapshot, TransitionSummary, Card } from './types';
import { state, DECK, RUNTIME_ALGORITHM, ACTIVE_ALGORITHM_SOURCE, rebuildDeckMap, setRuntimeAlgorithm, setActiveAlgorithmSource } from './state/store';
import { isSplitDecisionCard, normalizeDecisionIndexForCard, rememberedDecisionIndexForCard } from './state/decisions';
import { computeWheelMode } from './wheel/fsm';
import { canonicalAngleForCard } from './wheel/physics';
import { currentAlgorithmStartId } from './navigation/anchors';
import { advance, rewind, resetTimerState } from './navigation/advance';
import { render } from './cards/renderer';
import { normalizeAlgorithm, loadAlgorithmByFileName, discoverAvailableAlgorithmFiles } from './algorithms/loader';
import { syncHeaderFromAlgorithm, applyAlgorithm } from './main';

function summarizeTransition(card: Card | null): TransitionSummary | null {
  const transitions = card && card.transitions ? card.transitions : null;
  if (!transitions) return null;

  const options = transitions.type === 'split' && Array.isArray(transitions.options)
    ? transitions.options.map((opt, idx) => ({
      index: idx,
      label: opt.label || `option-${idx + 1}`,
      sub_label: opt.sub_label || null,
      target_id: opt.target_id || null,
      preview_card_title: opt.preview_card_title || null,
    }))
    : [];

  return {
    type: transitions.type || null,
    next_id: 'next_id' in transitions ? transitions.next_id : null,
    options,
  };
}

function snapshotForAutomation(): AutomationSnapshot {
  const card = DECK[state.currentId] || null;
  return {
    currentId: state.currentId,
    algorithmSource: ACTIVE_ALGORITHM_SOURCE,
    history: [...state.history],
    historySize: state.history.length,
    decisionIndex: state.decisionIndex,
    decisionRecords: { ...state.decisionRecords },
    decisionTrail: state.decisionTrail.slice(-30),
    carouselIndex: state.carouselIndex,
    timerSeconds: state.timerSeconds,
    anchors: state.anchors.map((a) => ({ id: a.id, angle: a.angle })),
    anchorIndex: state.anchorIndex,
    decisionTapped: state.decisionTapped,
    wheel: {
      mode: state.wheel.mode,
      angle: state.wheel.angle,
    },
    card: card ? {
      id: card.id,
      type: card.type,
      status: card.status || null,
      title: (card.content && card.content.title) ? card.content.title : '',
      phase: (card.wheel_config && card.wheel_config.phase) ? card.wheel_config.phase : null,
      canonicalAngle: canonicalAngleForCard(card, state.wheel.angle),
      transitions: summarizeTransition(card),
    } : null,
  };
}

function setCurrentCardForAutomation(cardId: string) {
  const card = DECK[cardId];
  if (!card) {
    return {
      ok: false,
      error: `Unknown card id: ${cardId}`,
      snapshot: snapshotForAutomation(),
    };
  }

  state.currentId = card.id;
  state.history = [];
  if (isSplitDecisionCard(card)) {
    state.decisionIndex = rememberedDecisionIndexForCard(card);
  } else {
    state.decisionIndex = 0;
  }
  state.decisionTapped = false;
  state.carouselIndex = 0;
  state.wheel.mode = computeWheelMode(card);
  state.wheel.dragOrigin = null;
  state.wheel.navConsumed = false;
  resetTimerState();
  render();

  return {
    ok: true,
    error: null,
    snapshot: snapshotForAutomation(),
  };
}

export function setupWardenAutomation(): void {
  (window as unknown as Record<string, unknown>).__WARDEN_AUTOMATION = {
    version: '1.0',
    listCards() {
      return RUNTIME_ALGORITHM.deck.map((card) => card.id);
    },
    listAvailableAlgorithms() {
      return discoverAvailableAlgorithmFiles();
    },
    async loadAlgorithm(fileName: string) {
      try {
        const loaded = await loadAlgorithmByFileName(fileName);
        const result = applyAlgorithm(loaded, fileName);
        return {
          ...result,
          error: null,
          snapshot: snapshotForAutomation(),
        };
      } catch (err: unknown) {
        return {
          ok: false,
          error: err && (err as Error).message ? (err as Error).message : String(err),
          snapshot: snapshotForAutomation(),
        };
      }
    },
    getModel() {
      return {
        start_id: currentAlgorithmStartId(),
        algorithm_source: ACTIVE_ALGORITHM_SOURCE,
        algorithm_meta: RUNTIME_ALGORITHM.algorithm_meta || null,
        cards: RUNTIME_ALGORITHM.deck.map((card) => ({
          id: card.id,
          type: card.type,
          status: card.status || null,
          title: (card.content && card.content.title) ? card.content.title : '',
          wheel: card.wheel_config || null,
          transitions: summarizeTransition(card),
        })),
      };
    },
    getSnapshot() {
      return snapshotForAutomation();
    },
    reset() {
      const startId = currentAlgorithmStartId() || state.currentId;
      return setCurrentCardForAutomation(startId);
    },
    gotoCard(cardId: string) {
      return setCurrentCardForAutomation(cardId);
    },
    selectDecisionOption(index: number) {
      const card = DECK[state.currentId];
      if (!card || !card.transitions || card.transitions.type !== 'split') {
        return {
          ok: false,
          error: 'Current card is not a split decision card',
          snapshot: snapshotForAutomation(),
        };
      }
      state.decisionIndex = normalizeDecisionIndexForCard(card, index);
      state.decisionTapped = true;
      render();
      return {
        ok: true,
        error: null,
        snapshot: snapshotForAutomation(),
      };
    },
    advance() {
      const beforeId = state.currentId;
      const moved = advance({ source: 'automation', splitConfirmed: true });
      return {
        ok: true,
        error: null,
        moved,
        before_id: beforeId,
        after_id: state.currentId,
        snapshot: snapshotForAutomation(),
      };
    },
    back() {
      const beforeId = state.currentId;
      rewind();
      return {
        ok: true,
        error: null,
        before_id: beforeId,
        after_id: state.currentId,
        snapshot: snapshotForAutomation(),
      };
    },
  };
}
