// === KNOB DRAG HANDLING ===
import { state, DECK } from '../state/store';
import { getDom } from '../main';
import { getCurrentWheelArc, clampAngleToArc, angleDelta, setKnobPosition } from './physics';
import { isForwardGesture, isReverseGesture } from './gestures';
import { advance, rewind } from '../navigation/advance';
import { triggerHaptic } from '../ui/haptic';
import { currentAnchorAngle } from '../navigation/anchors';

let isDraggingKnob = false;

function getAngleFromEvent(e: MouseEvent | TouchEvent): number {
  const dom = getDom();
  const touch = 'touches' in e ? e.touches[0] : e;
  const rect = dom.wheel.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;

  let deg = Math.atan2(touch.clientY - cy, touch.clientX - cx) * 180 / Math.PI + 90;
  if (deg < 0) deg += 360;
  return deg;
}

function startKnobDrag(e: MouseEvent | TouchEvent): void {
  isDraggingKnob = true;
  const dom = getDom();
  dom.knob.classList.add('dragging');
  e.preventDefault();
  e.stopPropagation();

  const arc = getCurrentWheelArc();
  const startAngle = clampAngleToArc(getAngleFromEvent(e), arc);
  state.wheel.dragOrigin = startAngle;
  state.wheel.navConsumed = false;
}

function handleDecisionWheelDrag(delta: number): void {
  const card = DECK[state.currentId];
  if (!card || !card.transitions || card.transitions.type !== 'split') return;
  const dom = getDom();
  const arc = getCurrentWheelArc();

  if (isReverseGesture(delta, arc)) {
    dom.knob.classList.remove('dragging');
    const moved = rewind();
    if (moved) {
      state.wheel.navConsumed = true;
      triggerHaptic(15);
    }
    return;
  }

  if (state.decisionTapped && isForwardGesture(delta, arc)) {
    dom.knob.classList.remove('dragging');
    const moved = advance({ source: 'wheel-drag', splitConfirmed: true });
    if (moved) {
      state.wheel.navConsumed = true;
      triggerHaptic(15);
    }
  }
}

function onKnobDrag(e: MouseEvent | TouchEvent): void {
  if (!isDraggingKnob) return;
  e.preventDefault();

  const card = DECK[state.currentId];
  if (!card) return;

  const arc = getCurrentWheelArc();
  const currentAngle = clampAngleToArc(getAngleFromEvent(e), arc);

  if (state.wheel.dragOrigin == null) {
    state.wheel.dragOrigin = currentAngle;
  }

  const delta = angleDelta(state.wheel.dragOrigin, currentAngle);
  const mode = state.wheel.mode;

  if (state.wheel.navConsumed) return;

  const dom = getDom();

  if (mode === 'COVER') {
    if (isForwardGesture(delta, arc)) {
      dom.knob.classList.remove('dragging');
      advance({ source: 'wheel-drag' });
      state.wheel.navConsumed = true;
      triggerHaptic(15);
    } else {
      setKnobPosition(currentAngle);
    }
    return;
  }

  if (mode === 'TERMINAL') {
    if (isReverseGesture(delta, arc)) {
      dom.knob.classList.remove('dragging');
      rewind();
      state.wheel.navConsumed = true;
      triggerHaptic(15);
    } else {
      setKnobPosition(currentAngle);
    }
    return;
  }

  if (mode === 'DECISION') {
    handleDecisionWheelDrag(delta);
    return;
  }

  // LINEAR / LOOP
  if (isForwardGesture(delta, arc)) {
    dom.knob.classList.remove('dragging');
    advance({ source: 'wheel-drag' });
    state.wheel.navConsumed = true;
    triggerHaptic(15);
    return;
  }

  if (isReverseGesture(delta, arc)) {
    dom.knob.classList.remove('dragging');
    rewind();
    state.wheel.navConsumed = true;
    triggerHaptic(15);
    return;
  }

  setKnobPosition(currentAngle);
}

function endKnobDrag(): void {
  if (!isDraggingKnob) return;
  isDraggingKnob = false;

  const dom = getDom();
  dom.knob.classList.remove('dragging');
  state.wheel.dragOrigin = null;
  state.wheel.navConsumed = false;

  state.wheel.angle = currentAnchorAngle();
  setKnobPosition(state.wheel.angle);
}

export function setupKnobListeners(): void {
  const dom = getDom();
  dom.knob.addEventListener('mousedown', startKnobDrag as EventListener);
  dom.knob.addEventListener('touchstart', startKnobDrag as EventListener, { passive: false });
  document.addEventListener('mousemove', onKnobDrag as EventListener);
  document.addEventListener('touchmove', onKnobDrag as EventListener, { passive: false });
  document.addEventListener('mouseup', endKnobDrag);
  document.addEventListener('touchend', endKnobDrag);
}
