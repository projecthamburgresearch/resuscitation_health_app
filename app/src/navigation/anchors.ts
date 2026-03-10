// === ANCHOR-POINT NAVIGATION ENGINE ===
import type { Anchor, Card, HistoryEntry, WheelArc } from '../types';
import { state, DECK, RUNTIME_ALGORITHM } from '../state/store';
import { normalizeDegrees, normalizeWheelArc } from '../algorithms/loader';

function getCurrentWheelArc(): WheelArc {
  const meta = RUNTIME_ALGORITHM && RUNTIME_ALGORITHM.algorithm_meta
    ? RUNTIME_ALGORITHM.algorithm_meta
    : null;
  return normalizeWheelArc(meta as Record<string, unknown> | null);
}

function angleOnArc(arc: WheelArc, ratio: number): number {
  const t = Math.max(0, Math.min(1, Number(ratio)));
  const cwDistance = (arc.end_degrees - arc.start_degrees + 360) % 360;
  const ccwDistance = (arc.start_degrees - arc.end_degrees + 360) % 360;
  if (arc.direction === 'anticlockwise') {
    const n = arc.start_degrees - ccwDistance * t;
    const mod = n % 360;
    return mod < 0 ? mod + 360 : mod;
  }
  const n = arc.start_degrees + cwDistance * t;
  const mod = n % 360;
  return mod < 0 ? mod + 360 : mod;
}

export function currentAlgorithmStartId(): string | null {
  return RUNTIME_ALGORITHM.deck.length > 0 ? RUNTIME_ALGORITHM.deck[0].id : null;
}

function countPathLength(startId: string, alreadyVisited: Set<string>): number {
  let count = 0;
  let cardId: string | null = startId;
  const visited = new Set(alreadyVisited);
  while (cardId && DECK[cardId] && !visited.has(cardId)) {
    visited.add(cardId);
    count++;
    const card: Card = DECK[cardId];
    if (!card.transitions) break;
    if (card.transitions.type === 'linear') {
      cardId = card.transitions.next_id;
    } else if (card.transitions.type === 'split') {
      cardId = card.transitions.options[0] ? card.transitions.options[0].target_id : null;
    } else if (card.transitions.type === 'self_loop') {
      if (card.transitions.next_id === card.id) break;
      cardId = card.transitions.next_id;
    } else {
      break;
    }
  }
  return count;
}

function longestBranchTarget(card: Card, visited: Set<string>): string | null {
  if (!card.transitions || card.transitions.type !== 'split') return null;
  let bestTarget: string | null = null;
  let bestLength = -1;
  for (const opt of card.transitions.options) {
    if (!opt.target_id || !DECK[opt.target_id]) continue;
    if (visited.has(opt.target_id)) continue;
    const len = countPathLength(opt.target_id, visited);
    if (len > bestLength) {
      bestLength = len;
      bestTarget = opt.target_id;
    }
  }
  return bestTarget || (card.transitions.options[0] ? card.transitions.options[0].target_id : null);
}

export function computeForwardPath(): string[] {
  const path: string[] = [];
  const visited = new Set<string>();
  let cardId: string | null = currentAlgorithmStartId();

  while (cardId && DECK[cardId] && !visited.has(cardId)) {
    visited.add(cardId);
    path.push(cardId);

    const card = DECK[cardId];
    if (!card.transitions) break;

    if (card.transitions.type === 'linear') {
      cardId = card.transitions.next_id;
    } else if (card.transitions.type === 'split') {
      if (Object.prototype.hasOwnProperty.call(state.decisionRecords, card.id)) {
        const idx = state.decisionRecords[card.id];
        const opt = card.transitions.options[idx];
        cardId = opt ? opt.target_id : null;
      } else {
        cardId = longestBranchTarget(card, visited);
      }
    } else if (card.transitions.type === 'self_loop') {
      const nextId = card.transitions.next_id;
      if (nextId === card.id) break;
      cardId = nextId;
    } else {
      break;
    }
  }

  return path;
}

function computeAnchors(): Anchor[] {
  const historyTrail: HistoryEntry[] = state.history;
  const trail = [
    ...historyTrail,
    {
      card_id: state.currentId,
      visit_key: state.currentVisitKey,
    },
  ];
  if (trail.length === 0) return [];

  return trail.map((entry) => {
    const card = DECK[entry.card_id];
    const explicitAngle = card && card.wheel_config && typeof card.wheel_config.position_degrees === 'number'
      ? normalizeDegrees(card.wheel_config.position_degrees)
      : null;

    return {
      id: entry.card_id,
      angle: explicitAngle != null ? explicitAngle : getCurrentWheelArc().start_degrees,
      visit_key: entry.visit_key,
    };
  });
}

function findAnchorIndex(cardId: string, visitKey: number): number {
  return state.anchors.findIndex((a) => a.id === cardId && a.visit_key === visitKey);
}

export function currentAnchorAngle(): number {
  const currentCard = DECK[state.currentId];
  if (
    currentCard
    && currentCard.wheel_config
    && typeof currentCard.wheel_config.position_degrees === 'number'
  ) {
    return normalizeDegrees(currentCard.wheel_config.position_degrees);
  }
  if (state.anchorIndex >= 0 && state.anchorIndex < state.anchors.length) {
    return state.anchors[state.anchorIndex].angle;
  }
  return getCurrentWheelArc().start_degrees;
}

export function syncAnchors(): void {
  state.anchors = computeAnchors();
  const idx = findAnchorIndex(state.currentId, state.currentVisitKey);
  if (idx >= 0) {
    state.anchorIndex = idx;
  } else {
    state.anchorIndex = Math.max(0, state.anchors.length - 1);
  }
}
