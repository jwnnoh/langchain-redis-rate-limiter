import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_redis_rate_limiter.limiter import RedisRateLimiter


class TestRedisRateLimiterSync(unittest.TestCase):
    def setUp(self):
        self.redis_patcher = patch(
            "langchain_redis_rate_limiter.limiter.redis.from_url"
        )
        self.async_redis_patcher = patch(
            "langchain_redis_rate_limiter.limiter.redis_async.from_url"
        )

        self.mock_redis_cls = self.redis_patcher.start()
        self.mock_async_redis_cls = self.async_redis_patcher.start()

        self.mock_redis = MagicMock()
        self.mock_async_redis = MagicMock()

        self.mock_redis_cls.return_value = self.mock_redis
        self.mock_async_redis_cls.return_value = self.mock_async_redis

    def tearDown(self):
        self.redis_patcher.stop()
        self.async_redis_patcher.stop()

    def test_acquire_success_non_blocking(self):
        self.mock_redis.eval.return_value = 1

        limiter = RedisRateLimiter(redis_url="redis://localhost:6379")
        result = limiter.acquire(blocking=False)

        self.assertTrue(result)
        self.mock_redis.eval.assert_called_once()

    def test_acquire_fail_non_blocking(self):
        self.mock_redis.eval.return_value = 0

        limiter = RedisRateLimiter(redis_url="redis://localhost:6379")
        result = limiter.acquire(blocking=False)

        self.assertFalse(result)
        self.mock_redis.eval.assert_called_once()

    def test_acquire_blocking_waits_then_succeeds(self):
        self.mock_redis.eval.side_effect = [0, 1]

        limiter = RedisRateLimiter(
            redis_url="redis://localhost:6379",
            check_every_n_seconds=0.1,
        )

        with patch("langchain_redis_rate_limiter.limiter.time.sleep") as mock_sleep:
            result = limiter.acquire(blocking=True)

        self.assertTrue(result)
        self.assertEqual(self.mock_redis.eval.call_count, 2)
        mock_sleep.assert_called_once_with(0.1)

    def test_execute_lua_arguments_and_key_prefix(self):
        self.mock_redis.eval.return_value = 1

        limiter = RedisRateLimiter(
            redis_url="redis://localhost:6379",
            key_prefix="my_prefix",
            requests_per_second=3,
            max_bucket_size=7,
        )
        limiter.acquire(blocking=False)

        args, _ = self.mock_redis.eval.call_args
        lua_script = args[0]
        num_keys = args[1]
        key = args[2]
        max_bucket_size = args[3]
        rps = args[4]

        self.assertIsInstance(lua_script, str)
        self.assertEqual(num_keys, 1)
        self.assertEqual(key, "my_prefix:rate_limit")
        self.assertEqual(max_bucket_size, 7)
        self.assertEqual(rps, 3)

    def test_key_prefix_separates_keys_sync(self):
        self.mock_redis.eval.return_value = 1

        limiter_a = RedisRateLimiter(
            redis_url="redis://localhost:6379",
            key_prefix="prefix_a",
        )
        limiter_b = RedisRateLimiter(
            redis_url="redis://localhost:6379",
            key_prefix="prefix_b",
        )

        limiter_a.acquire(blocking=False)
        limiter_b.acquire(blocking=False)

        # eval은 총 2번 호출돼야 함
        self.assertEqual(self.mock_redis.eval.call_count, 2)

        # 각 호출에서 사용된 key(세 번째 positional arg)를 뽑아 비교
        calls = self.mock_redis.eval.call_args_list
        key_a = calls[0].args[2]
        key_b = calls[1].args[2]

        self.assertEqual(key_a, "prefix_a:rate_limit")
        self.assertEqual(key_b, "prefix_b:rate_limit")
        self.assertNotEqual(key_a, key_b)


class TestRedisRateLimiterAsync(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.redis_patcher = patch(
            "langchain_redis_rate_limiter.limiter.redis.from_url"
        )
        self.async_redis_patcher = patch(
            "langchain_redis_rate_limiter.limiter.redis_async.from_url"
        )

        self.mock_redis_cls = self.redis_patcher.start()
        self.mock_async_redis_cls = self.async_redis_patcher.start()

        self.mock_redis = MagicMock()
        self.mock_async_redis = MagicMock()
        self.mock_async_redis.eval = AsyncMock()

        self.mock_redis_cls.return_value = self.mock_redis
        self.mock_async_redis_cls.return_value = self.mock_async_redis

    async def asyncTearDown(self):
        self.redis_patcher.stop()
        self.async_redis_patcher.stop()

    async def test_aacquire_success_non_blocking(self):
        self.mock_async_redis.eval.return_value = 1

        limiter = RedisRateLimiter(redis_url="redis://localhost:6379")
        result = await limiter.aacquire(blocking=False)

        self.assertTrue(result)
        self.mock_async_redis.eval.assert_awaited_once()

    async def test_aacquire_fail_non_blocking(self):
        self.mock_async_redis.eval.return_value = 0

        limiter = RedisRateLimiter(redis_url="redis://localhost:6379")
        result = await limiter.aacquire(blocking=False)

        self.assertFalse(result)
        self.mock_async_redis.eval.assert_awaited_once()

    async def test_aacquire_blocking_waits_then_succeeds(self):
        self.mock_async_redis.eval.side_effect = [0, 1]

        limiter = RedisRateLimiter(
            redis_url="redis://localhost:6379",
            check_every_n_seconds=0.1,
        )

        with patch(
            "langchain_redis_rate_limiter.limiter.asyncio.sleep",
            new=AsyncMock(),
        ) as mock_sleep:
            result = await limiter.aacquire(blocking=True)

        self.assertTrue(result)
        self.assertEqual(self.mock_async_redis.eval.await_count, 2)
        mock_sleep.assert_awaited_once_with(0.1)

    async def test_execute_lua_async_arguments_and_key_prefix(self):
        self.mock_async_redis.eval.return_value = 1

        limiter = RedisRateLimiter(
            redis_url="redis://localhost:6379",
            key_prefix="async_prefix",
            requests_per_second=2,
            max_bucket_size=5,
        )
        await limiter.aacquire(blocking=False)

        args, _ = self.mock_async_redis.eval.call_args
        lua_script = args[0]
        num_keys = args[1]
        key = args[2]
        max_bucket_size = args[3]
        rps = args[4]

        self.assertIsInstance(lua_script, str)
        self.assertEqual(num_keys, 1)
        self.assertEqual(key, "async_prefix:rate_limit")
        self.assertEqual(max_bucket_size, 5)
        self.assertEqual(rps, 2)

    async def test_key_prefix_separates_keys_async(self):
        self.mock_async_redis.eval.return_value = 1

        limiter_a = RedisRateLimiter(
            redis_url="redis://localhost:6379",
            key_prefix="prefix_a",
        )
        limiter_b = RedisRateLimiter(
            redis_url="redis://localhost:6379",
            key_prefix="prefix_b",
        )

        await limiter_a.aacquire(blocking=False)
        await limiter_b.aacquire(blocking=False)

        self.assertEqual(self.mock_async_redis.eval.await_count, 2)

        calls = self.mock_async_redis.eval.call_args_list
        key_a = calls[0].args[2]
        key_b = calls[1].args[2]

        self.assertEqual(key_a, "prefix_a:rate_limit")
        self.assertEqual(key_b, "prefix_b:rate_limit")
        self.assertNotEqual(key_a, key_b)


if __name__ == "__main__":
    unittest.main()
