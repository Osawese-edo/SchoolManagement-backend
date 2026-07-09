import threading
import time
from typing import Any, Callable


class CacheEntry:
    def __init__(self, value: Any, ttl: float | None = None):
        self.value = value
        self.expires_at = (time.monotonic() + ttl) if ttl is not None else None

    def is_expired(self) -> bool:
        return self.expires_at is not None and time.monotonic() >= self.expires_at


class CacheManager:
    def __init__(self, max_size: int = 500):
        self._store: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._max_size = max_size

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._store[key]
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl: float | None = 300):
        with self._lock:
            self._store[key] = CacheEntry(value, ttl)
            if len(self._store) > self._max_size:
                self._evict_lru()

    def invalidate(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def invalidate_by_prefix(self, prefix: str):
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]

    def get_or_fetch(self, key: str, fetch: Callable[[], Any], ttl: float | None = 300) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = fetch()
        self.set(key, value, ttl)
        return value

    def _evict_lru(self):
        sorted_keys = sorted(self._store.keys(), key=lambda k: self._store[k].expires_at or 0)
        to_remove = len(self._store) - self._max_size
        for k in sorted_keys[:to_remove]:
            del self._store[k]


cache_manager = CacheManager()
