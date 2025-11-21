import time
import asyncio
import redis
import redis.asyncio as redis_async
from langchain_core.rate_limiters import BaseRateLimiter


class RedisRateLimiter(BaseRateLimiter):
    """
    Redis-based RateLimiter implementation compatible with LangChain's BaseRateLimiter.

    Redis 기반의 RateLimiter 구현체로, LangChain의 BaseRateLimiter와 호환됩니다.
    """

    # Lua script for token bucket algorithm
    # 토큰 버킷 알고리즘을 위한 Lua 스크립트
    _LUA_SCRIPT = """
        local key = KEYS[1]
        local max_bucket_size = tonumber(ARGV[1])
        local requests_per_second = tonumber(ARGV[2])
        
        local time_result = redis.call('TIME')
        local current_time = tonumber(time_result[1]) + (tonumber(time_result[2]) / 1000000)

        local bucket = redis.call('hmget', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1])
        local last_refill = tonumber(bucket[2])

        if not tokens or not last_refill then
            tokens = max_bucket_size
            last_refill = current_time
        end

        local elapsed = current_time - last_refill
        if elapsed < 0 then elapsed = 0 end
        
        local refill = elapsed * requests_per_second
        tokens = math.min(max_bucket_size, tokens + refill)
        last_refill = current_time

        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('hmset', key, 'tokens', tokens, 'last_refill', last_refill)
            redis.call('expire', key, 86400)
            return 1
        else
            redis.call('hmset', key, 'tokens', tokens, 'last_refill', last_refill)
            redis.call('expire', key, 86400)
            return 0
        end
        """

    def __init__(
        self,
        *,
        redis_url: str,
        key_prefix: str = "langchain_limiter",
        requests_per_second: float = 1,
        check_every_n_seconds: float = 0.1,
        max_bucket_size: float = 1,
    ):
        """
        Initialize the RedisRateLimiter.

        Args:
            redis_url: URL for the Redis instance.
            key_prefix: Prefix for Redis keys.
            requests_per_second: Number of requests allowed per second.
            check_every_n_seconds: Interval to check for tokens when blocking.
            max_bucket_size: Maximum number of tokens in the bucket (burst size).

        RedisRateLimiter를 초기화합니다.

        매개변수:
            redis_url: Redis 인스턴스 URL.
            key_prefix: Redis 키 접두사.
            requests_per_second: 초당 허용되는 요청 수.
            check_every_n_seconds: 블로킹 시 토큰 확인 간격.
            max_bucket_size: 버킷의 최대 토큰 수 (버스트 크기).
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.requests_per_second = requests_per_second
        self.check_every_n_seconds = check_every_n_seconds
        self.max_bucket_size = max_bucket_size
        self._redis_client: redis.Redis = redis.from_url(
            self.redis_url, decode_responses=True
        )
        self._async_redis_client: redis_async.Redis = redis_async.from_url(
            self.redis_url, decode_responses=True
        )

    def acquire(self, *, blocking: bool = True) -> bool:
        """
        Attempt to acquire a token.

        토큰 획득을 시도합니다.
        """
        if not blocking:
            return self._consume()

        while not self._consume():
            time.sleep(self.check_every_n_seconds)

        return True

    async def aacquire(self, *, blocking: bool = True) -> bool:
        """
        Attempt to acquire a token asynchronously.

        비동기적으로 토큰 획득을 시도합니다.
        """
        if not blocking:
            return await self._aconsume()

        while not await self._aconsume():
            await asyncio.sleep(self.check_every_n_seconds)

        return True

    def _execute_lua(self, client: redis.Redis) -> bool:
        """
        Execute the Lua script to check and update the token bucket (sync).
        Lua script을 실행하여 토큰 버킷을 확인하고 업데이트합니다 (동기).
        """
        key = f"{self.key_prefix}:rate_limit"

        return client.eval(
            self._LUA_SCRIPT,
            1,
            key,
            self.max_bucket_size,
            self.requests_per_second,
        )

    async def _execute_lua_async(self, client: redis_async.Redis) -> bool:
        """
        Execute the Lua script to check and update the token bucket (async).
        Lua script을 실행하여 토큰 버킷을 확인하고 업데이트합니다 (비동기).
        """
        key = f"{self.key_prefix}:rate_limit"

        return await client.eval(
            self._LUA_SCRIPT,
            1,
            key,
            self.max_bucket_size,
            self.requests_per_second,
        )

    def _consume(self) -> bool:
        return bool(self._execute_lua(self._redis_client))

    async def _aconsume(self) -> bool:
        return bool(await self._execute_lua_async(self._async_redis_client))
