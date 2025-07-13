from typing import Callable, Any

# A CommandFunctor is an async, zero-argument function that returns any result.
# It encapsulates a deferred action (e.g., lambda: some_unit.train()).
CommandFunctor = Callable[[], Any]
