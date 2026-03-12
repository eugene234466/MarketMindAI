# ============================================================
# APP/CACHE.PY — Two-tier caching: Redis → in-memory fallback
# ============================================================
# Drop-in replacement for the _cache dict in routes.py.
# Set REDIS_URL in env to enable Redis (multi-worker safe).
# Without Redis, falls back to an in-memory LRU dict.
# ============================================================
import os
import json
import hashlib

_MEMORY: dict = {}
_MAX_MEMORY   = 100          # slots
_TTL_SECONDS  = 60 * 60 * 6 # 6 hours

_redis = None


def _get_redis():
    global _redis
    if _redis is not None:
        return _redis
    url = os.environ.get("REDIS_URL")
    if not url:
        return None
    try:
        import redis
        _redis = redis.from_url(url, decode_responses=True, socket_timeout=2)
        _redis.ping()
        print("[Cache] Redis connected")
        return _redis
    except Exception as e:
        print(f"[Cache] Redis unavailable, using memory: {e}")
        return None


def _key(idea: str) -> str:
    return "mm:analysis:" + hashlib.md5(idea.strip().lower().encode()).hexdigest()


def get_cached(idea: str) -> dict | None:
    k = _key(idea)
    r = _get_redis()
    if r:
        try:
            raw = r.get(k)
            return json.loads(raw) if raw else None
        except Exception:
            pass
    return _MEMORY.get(k)


def set_cache(idea: str, results: dict):
    k = _key(idea)
    r = _get_redis()
    if r:
        try:
            r.setex(k, _TTL_SECONDS, json.dumps(results))
            return
        except Exception:
            pass
    # In-memory LRU eviction
    if len(_MEMORY) >= _MAX_MEMORY:
        oldest = next(iter(_MEMORY))
        del _MEMORY[oldest]
    _MEMORY[k] = results


def clear_cache() -> int:
    count = len(_MEMORY)
    _MEMORY.clear()
    r = _get_redis()
    if r:
        try:
            keys = r.keys("mm:analysis:*")
            if keys:
                count += len(keys)
                r.delete(*keys)
        except Exception:
            pass
    return count


def cache_info() -> dict:
    r = _get_redis()
    redis_count = 0
    if r:
        try:
            redis_count = len(r.keys("mm:analysis:*"))
        except Exception:
            pass
    return {
        "backend"      : "redis" if r else "memory",
        "memory_slots" : len(_MEMORY),
        "redis_keys"   : redis_count,
        "max_memory"   : _MAX_MEMORY,
        "ttl_hours"    : _TTL_SECONDS // 3600,
    }
