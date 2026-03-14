"""Sample Python module for Blueprint testing.

This file has known entities and complexity values so unit tests
can verify parser output against expected results.

Expected entities:
- 1 FILE entity
- 3 FUNCTION entities: greet, compute_total, fetch_data
- 2 CLASS entities: User, AdminUser
- 3 METHOD entities: User.__init__, User.full_name, AdminUser.promote
- 2 IMPORT entities (at least)
- 2 VARIABLE/CONSTANT entities: MAX_RETRIES, default_greeting

Expected edges:
- CALLS: compute_total -> greet, fetch_data -> compute_total
- INHERITS: AdminUser -> User
- CONTAINS: FILE -> all top-level entities
- IMPORTS: FILE -> imports
"""

import os
from typing import List, Optional

MAX_RETRIES = 3
default_greeting = "Hello"


def greet(name: str, greeting: str = "Hello") -> str:
    """Return a greeting string."""
    return f"{greeting}, {name}!"


def compute_total(items: List[int], tax_rate: float = 0.1) -> float:
    """Compute total with tax applied.

    Cyclomatic complexity: 4 (1 + if + for + if)
    """
    if not items:
        return 0.0

    total = 0.0
    for item in items:
        if item > 0:
            total += item

    # Call another function
    label = greet("customer")
    return total * (1 + tax_rate)


def fetch_data(url: str, retries: int = MAX_RETRIES) -> Optional[dict]:
    """Fetch data with retry logic.

    Cyclomatic complexity: 5 (1 + while + try/except + if + if)
    """
    attempt = 0
    while attempt < retries:
        try:
            # Simulate network call
            result = {"data": url, "total": compute_total([1, 2, 3])}
            if result:
                return result
        except Exception:
            attempt += 1
            if attempt >= retries:
                return None
    return None


class User:
    """A user in the system."""

    def __init__(self, first_name: str, last_name: str, email: str) -> None:
        """Initialize a new user."""
        self.first_name = first_name
        self.last_name = last_name
        self.email = email

    def full_name(self) -> str:
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}"


class AdminUser(User):
    """An admin user with elevated privileges."""

    def promote(self, target: User) -> bool:
        """Promote a regular user.

        Cyclomatic complexity: 3 (1 + if + if)
        """
        if not target:
            return False
        if target.email == self.email:
            return False
        return True
