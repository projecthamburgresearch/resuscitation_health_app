// === ANCHOR-POINT NAVIGATION ENGINE ===
import type { Anchor, Card, WheelArc } from '../types';
import { state, DECK, RUNTIME_ALGORITHM } from '../state/store';
import { normalizeWheelArc } from '../algorithms/loader';

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
  const path = computeForwardPath();
  const arc = getCurrentWheelArc();

  if (path.length === 0) return [];
  if (path.length === 1) {
    return [{ id: path[0], angle: arc.start_degrees }];
  }

  return path.map((id, i) => ({
    id,
    angle: angleOnArc(arc, i / (path.length - 1)),
  }));
}

function findAnchorIndex(cardId: string): number {
  return state.anchors.findIndex((a) => a.id === cardId);
}

export function currentAnchorAngle(): number {
  if (state.anchorIndex >= 0 && state.anchorIndex < state.anchors.length) {
    return state.anchors[state.anchorIndex].angle;
  }
  return getCurrentWheelArc().start_degrees;
}

export function syncAnchors(): void {
  state.anchors = computeAnchors();
  const idx = findAnchorIndex(state.currentId);
  if (idx >= 0) {
    state.anchorIndex = idx;
  } else {
    state.anchorIndex = Math.max(0, state.anchors.length - 1);
  }
}
