// === WHEEL GESTURE DETECTION ===
import type { WheelArc } from '../types';
import { NAV_THRESHOLD_DEG } from './physics';

export function isForwardGesture(delta: number, arc: WheelArc, threshold?: number): boolean {
  const t = typeof threshold === 'number' ? threshold : NAV_THRESHOLD_DEG;
  if (arc.direction === 'anticlockwise') {
    return delta > t;
  }
  return delta < -t;
}

export function isReverseGesture(delta: number, arc: WheelArc, threshold?: number): boolean {
  const t = typeof threshold === 'number' ? threshold : NAV_THRESHOLD_DEG;
  if (arc.direction === 'anticlockwise') {
    return delta < -t;
  }
  return delta > t;
}
