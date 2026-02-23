// === CHECKLIST AS NAVIGABLE CARD IN MIDDLE ZONE ===
// When a card has checklist items, a "checklist view" can be shown
// as a card overlay in the middle zone, styled like a regular card.
import type { Card, ChecklistItem } from '../types';
import { state } from '../state/store';

export function hasChecklistItems(card: Card): boolean {
  return !!(card.checklist && card.checklist.length > 0);
}

export function renderChecklistCardContent(card: Card): string {
  if (!card.checklist || card.checklist.length === 0) return '';

  const items = card.checklist
    .filter(item => {
      if (!item.visible_if) return true;
      return evaluateVisibility(item.visible_if);
    })
    .map(item => {
      const checked = state.checklistState[item.id] ? 'checked' : '';
      const isToggle = item.type === 'boolean_toggle';
      return `
        <label class="checklist-card-item ${isToggle ? 'toggle-item' : ''}" data-checklist-id="${item.id}">
          <input type="checkbox" ${checked}>
          <span>${item.label}</span>
        </label>
      `;
    })
    .join('');

  return `
    <div class="checklist-card-content">
      <div class="card-header">checklist</div>
      <div class="card-title">${card.content.title}</div>
      <div class="checklist-card-items">${items}</div>
    </div>
  `;
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
