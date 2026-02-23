// === DECISION STATE HELPERS ===
import type { Card } from '../types';
import { state } from './store';

export function isSplitDecisionCard(card: Card | null): boolean {
  return !!(
    card
    && card.transitions
    && card.transitions.type === 'split'
    && 'options' in card.transitions
    && Array.isArray(card.transitions.options)
    && card.transitions.options.length > 0
  );
}

export function normalizeDecisionIndexForCard(card: Card | null, requestedIndex: number): number {
  if (!card || !card.transitions || card.transitions.type !== 'split') return 0;
  const options = 'options' in card.transitions && Array.isArray(card.transitions.options)
    ? card.transitions.options
    : [];
  if (options.length === 0) return 0;
  const value = Number.isFinite(requestedIndex) ? Math.floor(requestedIndex) : 0;
  return Math.max(0, Math.min(options.length - 1, value));
}

export function rememberedDecisionIndexForCard(card: Card): number {
  if (!isSplitDecisionCard(card)) return 0;
  const remembered = Object.prototype.hasOwnProperty.call(state.decisionRecords, card.id)
    ? state.decisionRecords[card.id]
    : state.decisionIndex;
  return normalizeDecisionIndexForCard(card, remembered);
}
