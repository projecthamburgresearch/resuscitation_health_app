// === ADVANCE & REWIND NAVIGATION ===
import type { AdvanceOptions } from '../types';
import { state, DECK, RUNTIME_ALGORITHM } from '../state/store';
import { isSplitDecisionCard, normalizeDecisionIndexForCard, rememberedDecisionIndexForCard } from '../state/decisions';
import { computeWheelMode } from '../wheel/fsm';
import { render } from '../cards/renderer';
import { startTimer, resetTimerState } from '../ui/timer';

export function advance(options: AdvanceOptions = {}): boolean {
  const source = options.source || 'ui';
  const splitConfirmed = Boolean(options.splitConfirmed || source === 'automation');
  const card = DECK[state.currentId];

  if (!card || card.status === 'complete') return false;

  let nextId: string | null = null;

  if (!card.transitions || !card.transitions.type) {
    return false;
  }

  if (card.transitions.type === 'linear') {
    nextId = card.transitions.next_id;
  } else if (card.transitions.type === 'split') {
    if (!Array.isArray(card.transitions.options) || card.transitions.options.length === 0) return false;
    if (!splitConfirmed) return false;
    const pickedIndex = normalizeDecisionIndexForCard(card, state.decisionIndex);
    const picked = card.transitions.options[pickedIndex] || null;
    nextId = picked ? picked.target_id : null;
    state.decisionRecords[card.id] = pickedIndex;
    state.decisionTrail.push({
      card_id: card.id,
      option_index: pickedIndex,
      option_label: picked && picked.label ? picked.label : `Option ${pickedIndex + 1}`,
      target_id: nextId || null,
      interaction: 'forward-decision-confirm',
      source,
      timestamp: new Date().toISOString(),
    });
  } else if (card.transitions.type === 'self_loop') {
    nextId = card.transitions.next_id || card.id;
  }

  if (nextId && DECK[nextId]) {
    if (nextId !== state.currentId) {
      state.history.push(state.currentId);
    }
    state.currentId = nextId;
    const nextCard = DECK[nextId];
    if (isSplitDecisionCard(nextCard)) {
      state.decisionIndex = rememberedDecisionIndexForCard(nextCard);
    } else {
      state.decisionIndex = 0;
    }
    state.decisionTapped = false;
    state.carouselIndex = 0;

    const autoStartCard = RUNTIME_ALGORITHM
      && RUNTIME_ALGORITHM.algorithm_meta
      && RUNTIME_ALGORITHM.algorithm_meta.global_timer
      ? RUNTIME_ALGORITHM.algorithm_meta.global_timer.auto_start_on_card
      : null;
    const shouldStartTimer = !autoStartCard || nextId === autoStartCard;
    if (!state.timerRunning && shouldStartTimer) startTimer();

    render();
    return true;
  }
  return false;
}

export function rewind(): boolean {
  if (state.history.length <= 0) return false;
  const prevId = state.history.pop()!;
  state.currentId = prevId;
  const prevCard = DECK[prevId];
  if (isSplitDecisionCard(prevCard)) {
    state.decisionIndex = rememberedDecisionIndexForCard(prevCard);
    state.decisionTapped = Object.prototype.hasOwnProperty.call(state.decisionRecords, prevId);
  } else {
    state.decisionIndex = 0;
    state.decisionTapped = false;
  }
  state.carouselIndex = 0;

  render();
  return true;
}

export function canTapAdvance(card: { type: string; status?: string; transitions: unknown } | null): boolean {
  if (!card || card.status === 'complete') return false;
  if (isSplitDecisionCard(card as import('../types').Card)) return false;
  return true;
}

export { resetTimerState };
