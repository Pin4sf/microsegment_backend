import time
from collections import defaultdict, deque
from typing import Dict, Deque

class InMemoryRateLimiter:
    def __init__(self):
        self.requests: Dict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, identifier: str, limit: int, period_seconds: int) -> bool:
        """
        Checks if a request from the given identifier is allowed based on the limit
        and period.

        Args:
            identifier: A unique identifier for the request source (e.g., account_id, IP address).
            limit: The maximum number of requests allowed in the period.
            period_seconds: The time window in seconds to check requests.

        Returns:
            True if the request is allowed, False otherwise.
        """
        current_time = time.monotonic()
        request_timestamps = self.requests[identifier]

        # Remove timestamps older than the current period
        while request_timestamps and request_timestamps[0] <= current_time - period_seconds:
            request_timestamps.popleft()

        # Check if the number of requests exceeds the limit
        if len(request_timestamps) < limit:
            request_timestamps.append(current_time)
            return True
        else:
            return False

# Global instance of the rate limiter
# This can be imported and used across the application.
# For more complex scenarios (e.g. distributed systems), a more robust solution
# like Redis would be needed.
global_rate_limiter = InMemoryRateLimiter()
