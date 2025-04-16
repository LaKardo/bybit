import time
import threading
import logging
from collections import defaultdict
class TokenBucket:
    def __init__(self, max_tokens, refill_rate, initial_tokens=None, logger=None):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = initial_tokens if initial_tokens is not None else max_tokens
        self.last_refill_time = time.time()
        self.lock = threading.RLock()
        self.logger = logger
    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill_time
        new_tokens = elapsed * self.refill_rate
        if new_tokens > 0:
            self.tokens = min(self.max_tokens, self.tokens + new_tokens)
            self.last_refill_time = now
    def consume(self, tokens=1, block=True, timeout=None):
        start_time = time.time()
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            if not block:
                if self.logger:
                    self.logger.debug(f"Rate limit hit, not enough tokens ({self.tokens}/{tokens})")
                return False
            deficit = tokens - self.tokens
            wait_time = deficit / self.refill_rate
            if timeout is not None and wait_time > timeout:
                if self.logger:
                    self.logger.debug(f"Rate limit hit, wait time ({wait_time:.2f}s) exceeds timeout ({timeout:.2f}s)")
                return False
            if self.logger:
                self.logger.debug(f"Rate limit hit, waiting {wait_time:.2f}s for tokens to refill")
            time.sleep(wait_time)
            self._refill()
            self.tokens -= tokens
            if self.logger:
                self.logger.debug(f"Resumed after waiting {time.time() - start_time:.2f}s for rate limit")
            return True
    def get_token_count(self):
        with self.lock:
            self._refill()
            return self.tokens
class RateLimiter:
    def __init__(self, logger=None):
        self.logger = logger
        self.buckets = {}
        self.lock = threading.RLock()
        self.default_limits = {
            "default": (100, 10),  
            "order": (50, 10),     
            "position": (50, 10),  
            "market": (120, 10),   
            "account": (60, 10)    
        }
        for key, (max_tokens, interval) in self.default_limits.items():
            self.buckets[key] = TokenBucket(
                max_tokens=max_tokens,
                refill_rate=max_tokens / interval,
                logger=self.logger
            )
        self.stats = defaultdict(int)
        self.stats_lock = threading.RLock()
    def add_limit(self, key, max_tokens, interval):
        with self.lock:
            self.buckets[key] = TokenBucket(
                max_tokens=max_tokens,
                refill_rate=max_tokens / interval,
                logger=self.logger
            )
    def limit(self, key="default", tokens=1, block=True, timeout=None):
        bucket = self.buckets.get(key)
        if bucket is None:
            bucket = self.buckets.get("default")
            if self.logger:
                self.logger.warning(f"Rate limit key '{key}' not found, using default")
        with self.stats_lock:
            self.stats[key] += 1
        return bucket.consume(tokens, block, timeout)
    def get_stats(self):
        with self.stats_lock:
            return dict(self.stats)
    def reset_stats(self):
        with self.stats_lock:
            self.stats.clear()
    def get_token_count(self, key="default"):
        bucket = self.buckets.get(key)
        if bucket is None:
            return 0
        return bucket.get_token_count()
    def get_limits(self):
        limits = {}
        try:
            for key, bucket in self.buckets.items():
                try:
                    limits[key] = {
                        "max_tokens": bucket.max_tokens,
                        "refill_rate": bucket.refill_rate,
                        "current_tokens": bucket.get_token_count()
                    }
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error getting limit info for {key}: {e}")
                    limits[key] = {
                        "max_tokens": getattr(bucket, "max_tokens", 0),
                        "refill_rate": getattr(bucket, "refill_rate", 0),
                        "current_tokens": 0,
                        "error": str(e)
                    }
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting rate limits: {e}")
            return {"error": str(e)}
        return limits
