// === CHECKLIST RENDERING ===
import type { Card } from '../types';
import { state, DECK } from '../state/store';
import { getDom } from '../main';

export function renderChecklist(card: Card): void {
  const dom = getDom();
  dom.checklistArea.innerHTML = '';

  if (!card.checklist) return;

  card.checklist.forEach(item => {
    const el = document.createElement('label');
    el.className = `check-item ${item.type === 'boolean_toggle' ? 'toggle-item' : ''}`;

    if (item.visible_if) {
      const visible = evaluateVisibility(item.visible_if);
      if (!visible) el.classList.add('hidden');
    }

    const checked = state.checklistState[item.id] ? 'checked' : '';
    const input = document.createElement('input');
    input.type = 'checkbox';
    if (state.checklistState[item.id]) input.checked = true;
    input.addEventListener('change', () => {
      handleCheckChange(item.id, input.checked);
    });

    const span = document.createElement('span');
    span.textContent = item.label;

    el.appendChild(input);
    el.appendChild(span);
    dom.checklistArea.appendChild(el);
  });
}

function evaluateVisibility(condition: string): boolean {
  const parts = condition.split(' AND ');
  return parts.every(part => {
    const match = part.trim().match(/(\w+)\s*==\s*(true|false)/);
    if (match) {
      const [, id, expected] = match;
      const actual = !!state.checklistState[id];
      return actual === (expected === 'true');
    }
    return true;
  });
}

function handleCheckChange(id: string, checked: boolean): void {
  state.checklistState[id] = checked;
  const card = DECK[state.currentId];
  if (card) renderChecklist(card);
}
