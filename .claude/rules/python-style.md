# Python Style

- Always add `from __future__ import annotations` as the first import
- Use `X | Y` union syntax, not `Union[X, Y]` or `Optional[X]`
- Use `type` aliases for complex types: `type UserID = str`
- Use `StrEnum` for string enumerations, not plain strings or class variables
- Import from `collections.abc` for abstract types: `Iterator`, `AsyncIterator`, `Sequence`
- Use `TYPE_CHECKING` guard for imports only needed by type checkers:
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from fastapi import FastAPI
  ```
- Prefer f-strings over `.format()` or `%` formatting
- Use `pathlib.Path` for file paths, not `os.path`
- Never use `print()` in `src/` — use `structlog` via `get_logger(__name__)`
- Never use bare `except:` — always catch a specific exception type
- Prefer early returns to reduce nesting
- Catch the narrowest exception: `except ImportError` for optional deps, not `except (ImportError, OSError)`
- Set explicit `max_tokens` on every LLM generation call — never rely on large defaults
- Use lazy-initialized singletons in FastAPI route modules to avoid circular imports
- Test doubles should subclass the real client and override network methods (e.g., `CannedPrometheusClient(PrometheusClient)`)
- Use `TYPE_CHECKING` for imports that are only needed at runtime in specific functions — move to runtime import inside the function if needed
