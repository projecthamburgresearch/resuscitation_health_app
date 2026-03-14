"""Warden persistent memory system.

Provides memory that persists across sessions, allowing the warden
to remember learnings, context, and patterns across runs.

Memory is organized by category:
- learnings: Things learned from errors and successes
- context: Project-specific context
- patterns: Detected patterns in the codebase
- preferences: User preferences discovered during operation
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MemoryItem:
    """A single memory item."""
    key: str
    value: Any
    category: str
    created_at: str
    updated_at: str
    access_count: int = 0
    estimated_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "access_count": self.access_count,
            "estimated_tokens": self.estimated_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryItem":
        return cls(
            key=data["key"],
            value=data["value"],
            category=data["category"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            access_count=data.get("access_count", 0),
            estimated_tokens=data.get("estimated_tokens", 0),
        )


class WardenMemory:
    """Persistent memory for the Warden.

    Usage:
        memory = WardenMemory(warden_dir)
        memory.load()

        # Remember something
        memory.remember("tsx_fix", "Use --jsx flag", "learnings")

        # Recall it later
        fix = memory.recall("tsx_fix")

        # Get all learnings
        learnings = memory.get_category("learnings")

        # Get context within token limit
        context = memory.get_context_for_limit(50000)

        memory.save()
    """

    def __init__(self, warden_dir: Path):
        self.warden_dir = Path(warden_dir)
        self.memory_dir = self.warden_dir / "memory"
        self.memory_file = self.memory_dir / "memory.json"
        self.items: Dict[str, MemoryItem] = {}

    def load(self) -> None:
        """Load memory from disk."""
        if not self.memory_file.exists():
            return

        try:
            data = json.loads(self.memory_file.read_text())
            for item_data in data.get("items", []):
                item = MemoryItem.from_dict(item_data)
                self.items[item.key] = item
        except (json.JSONDecodeError, OSError):
            pass

    def save(self) -> None:
        """Save memory to disk."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "saved_at": datetime.now().isoformat(),
            "item_count": len(self.items),
            "items": [item.to_dict() for item in self.items.values()],
        }

        self.memory_file.write_text(json.dumps(data, indent=2))

    def remember(
        self,
        key: str,
        value: Any,
        category: str = "general",
        estimated_tokens: int = 0,
    ) -> None:
        """Store a memory item.

        Args:
            key: Unique identifier for this memory.
            value: The value to remember.
            category: Category for organization (learnings, context, etc.)
            estimated_tokens: Estimated token count for context management.
        """
        now = datetime.now().isoformat()

        if key in self.items:
            # Update existing
            item = self.items[key]
            item.value = value
            item.updated_at = now
            if estimated_tokens > 0:
                item.estimated_tokens = estimated_tokens
        else:
            # Create new
            self.items[key] = MemoryItem(
                key=key,
                value=value,
                category=category,
                created_at=now,
                updated_at=now,
                estimated_tokens=estimated_tokens,
            )

    def recall(self, key: str) -> Optional[Any]:
        """Retrieve a memory item by key.

        Args:
            key: The key to look up.

        Returns:
            The stored value, or None if not found.
        """
        item = self.items.get(key)
        if item:
            item.access_count += 1
            return item.value
        return None

    def forget(self, key: str) -> bool:
        """Remove a memory item.

        Args:
            key: The key to remove.

        Returns:
            True if item was removed, False if not found.
        """
        if key in self.items:
            del self.items[key]
            return True
        return False

    def get_category(self, category: str) -> List[MemoryItem]:
        """Get all items in a category.

        Args:
            category: Category to filter by.

        Returns:
            List of items in that category.
        """
        return [
            item for item in self.items.values()
            if item.category == category
        ]

    def get_context_for_limit(self, token_limit: int) -> List[Dict[str, Any]]:
        """Get memory items that fit within a token limit.

        Prioritizes by:
        1. Most recently accessed
        2. Most frequently accessed
        3. Most recently created

        Args:
            token_limit: Maximum tokens to include.

        Returns:
            List of items that fit within the limit.
        """
        # Sort by priority (access count * recency factor)
        def priority(item: MemoryItem) -> float:
            # Higher access count = higher priority
            # More recent = higher priority
            recency = 1.0  # Could calculate from updated_at
            return item.access_count * recency

        sorted_items = sorted(
            self.items.values(),
            key=priority,
            reverse=True,
        )

        # Collect items until we hit the limit
        result = []
        total_tokens = 0

        for item in sorted_items:
            item_tokens = item.estimated_tokens or self._estimate_tokens(item.value)
            if total_tokens + item_tokens <= token_limit:
                result.append({
                    "key": item.key,
                    "value": item.value,
                    "category": item.category,
                })
                total_tokens += item_tokens

        return result

    def _estimate_tokens(self, value: Any) -> int:
        """Estimate token count for a value."""
        text = json.dumps(value) if not isinstance(value, str) else value
        # Rough estimate: 1 token per 4 characters
        return len(text) // 4

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of memory contents."""
        categories: Dict[str, int] = {}
        for item in self.items.values():
            categories[item.category] = categories.get(item.category, 0) + 1

        return {
            "total_items": len(self.items),
            "categories": categories,
            "total_estimated_tokens": sum(
                item.estimated_tokens or self._estimate_tokens(item.value)
                for item in self.items.values()
            ),
        }

    def search(self, query: str) -> List[MemoryItem]:
        """Search memory items by key or value content.

        Args:
            query: Search string (case-insensitive).

        Returns:
            Matching items.
        """
        query_lower = query.lower()
        results = []

        for item in self.items.values():
            if query_lower in item.key.lower():
                results.append(item)
                continue

            value_str = json.dumps(item.value) if not isinstance(item.value, str) else item.value
            if query_lower in value_str.lower():
                results.append(item)

        return results
