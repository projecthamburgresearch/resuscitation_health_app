"""Blueprint custom exception hierarchy."""


class BlueprintError(Exception):
    """Base exception for all Blueprint errors."""
    pass


class ParseError(BlueprintError):
    """Error during source code parsing."""

    def __init__(self, file_path: str, message: str, line: int | None = None):
        self.file_path = file_path
        self.line = line
        loc = f":{line}" if line else ""
        super().__init__(f"Parse error in {file_path}{loc}: {message}")


class ConfigError(BlueprintError):
    """Invalid or missing configuration."""
    pass


class FileAccessError(BlueprintError):
    """Cannot read or write a file."""

    def __init__(self, file_path: str, operation: str, reason: str):
        self.file_path = file_path
        self.operation = operation
        super().__init__(f"Cannot {operation} {file_path}: {reason}")


class GraphError(BlueprintError):
    """Error in knowledge graph operations."""
    pass


class CortexInjectionError(BlueprintError):
    """Error injecting metadata into source code comments."""

    def __init__(self, file_path: str, message: str):
        self.file_path = file_path
        super().__init__(f"Cortex injection error in {file_path}: {message}")


class DomainError(BlueprintError):
    """Error within a domain's execution."""

    def __init__(self, domain: str, message: str):
        self.domain = domain
        super().__init__(f"[{domain}] {message}")


class GitAnalysisError(BlueprintError):
    """Error during git analysis."""
    pass
