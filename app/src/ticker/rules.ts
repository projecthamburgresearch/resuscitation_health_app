// === TICKER RULES — Priority-based coaching messages ===
import type { Card } from '../types';
import { state, DECK } from '../state/store';

export interface TickerMessage {
  priority: number;
  text: string;
}

// Priority 1: Unchecked required items
function checkUncheckedItems(card: Card): TickerMessage | null {
  if (!card.checklist || card.checklist.length === 0) return null;

  const unchecked = card.checklist.filter(item => {
    if (item.visible_if) {
      const parts = item.visible_if.split(' AND ');
      const visible = parts.every(part => {
        const match = part.trim().match(/(\w+)\s*==\s*(true|false)/);
        if (match) {
          const [, id, expected] = match;
          return !!state.checklistState[id] === (expected === 'true');
        }
        return true;
      });
      if (!visible) return false;
    }
    return !state.checklistState[item.id];
  });

  if (unchecked.length > 0) {
    return {
      priority: 1,
      text: `Reminder: ${unchecked[0].label}`,
    };
  }
  return null;
}

// Priority 2: Decision point ahead
function checkDecisionAhead(card: Card): TickerMessage | null {
  if (!card.transitions) return null;

  let nextId: string | null = null;
  if (card.transitions.type === 'linear') {
    nextId = card.transitions.next_id;
  }
  if (nextId && DECK[nextId] && DECK[nextId].type === 'decision') {
    return {
      priority: 2,
      text: `Decision ahead: ${DECK[nextId].content.title}`,
    };
  }
  return null;
}

// Priority 3: Loop count
function checkLoopCount(): TickerMessage | null {
  // Count how many times loop_start cards appear in history
  const loopCards = state.history.filter(id => {
    const c = DECK[id];
    return c && (c.type === 'loop_start' || c.wheel_config.phase === 'cpr_loop');
  });
  if (loopCards.length > 0) {
    const count = Math.ceil(loopCards.length / 2); // rough cycle count
    return {
      priority: 3,
      text: `CPR cycle ${count} — continue compressions`,
    };
  }
  return null;
}

// Priority 4: Steps remaining to next decision
function checkStepsRemaining(card: Card): TickerMessage | null {
  let steps = 0;
  let currentId: string | null = null;

  if (card.transitions && card.transitions.type === 'linear') {
    currentId = card.transitions.next_id;
  }

  while (currentId && DECK[currentId] && steps < 10) {
    const c = DECK[currentId];
    if (c.type === 'decision' || c.type === 'terminal') {
      return {
        priority: 4,
        text: `${steps + 1} step${steps > 0 ? 's' : ''} to ${c.type === 'decision' ? 'next decision' : 'end'}`,
      };
    }
    steps++;
    if (c.transitions && c.transitions.type === 'linear') {
      currentId = c.transitions.next_id;
    } else {
      break;
    }
  }
  return null;
}

// Priority 5: Timer milestone
function checkTimerMilestone(): TickerMessage | null {
  const s = state.timerSeconds;
  if (s > 0 && s % 120 === 0) {
    const mins = s / 60;
    return {
      priority: 5,
      text: `${mins} minute${mins > 1 ? 's' : ''} elapsed — reassess`,
    };
  }
  return null;
}

// Priority 6: Default / idle
const DEFAULT_MESSAGES = [
  'Follow the protocol — you\'re doing great',
  'Stay calm, follow each step',
  'Check the checklist before advancing',
];

function getDefaultMessage(): TickerMessage {
  const idx = Math.floor(state.timerSeconds / 10) % DEFAULT_MESSAGES.length;
  return {
    priority: 6,
    text: DEFAULT_MESSAGES[idx],
  };
}

// Evaluate all rules, return highest priority message
export function evaluateTickerRules(): TickerMessage {
  const card = DECK[state.currentId];
  if (!card) return getDefaultMessage();

  const candidates: TickerMessage[] = [];

  const r1 = checkUncheckedItems(card);
  if (r1) candidates.push(r1);

  const r2 = checkDecisionAhead(card);
  if (r2) candidates.push(r2);

  const r3 = checkLoopCount();
  if (r3) candidates.push(r3);

  const r4 = checkStepsRemaining(card);
  if (r4) candidates.push(r4);

  const r5 = checkTimerMilestone();
  if (r5) candidates.push(r5);

  if (candidates.length === 0) return getDefaultMessage();

  // Sort by priority (lower = higher priority)
  candidates.sort((a, b) => a.priority - b.priority);
  return candidates[0];
}
