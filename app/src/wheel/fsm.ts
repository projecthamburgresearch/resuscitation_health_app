// === WHEEL FINITE STATE MACHINE ===
import type { Card, WheelMode } from '../types';

export function computeWheelMode(card: Card | null): WheelMode {
  if (!card) return 'LINEAR';
  if (card.type === 'cover') return 'COVER';
  if (card.type === 'decision') return 'DECISION';
  if (card.type === 'terminal') return 'TERMINAL';
  if (card.wheel_config && (card.wheel_config.phase === 'cpr_loop' || card.wheel_config.phase === 'loop')) return 'LOOP';
  return 'LINEAR';
}
