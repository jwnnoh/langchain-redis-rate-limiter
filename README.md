# LangChain Redis Rate Limiter

[English](README.md) | [한국어](README_ko.md)

A Redis-based RateLimiter for LangChain, compatible with `BaseRateLimiter`.
It supports **both Requests Per Minute (RPM) and Requests Per Second (RPS)** limiting, designed to work seamlessly in distributed environments.

## Features

- **Redis Support**: Compatible with Local Redis, AWS ElastiCache.
- **LangChain Integration**: Inherits from `BaseRateLimiter`, allowing direct usage with LangChain models.
- **Async Support**: Supports both sync and async requests.
- **Distributed Support**: Uses Redis to manage shared status across multiple servers or processes.

## Installation

You can install using the `pip` or `uv` package manager.

```bash
pip install langchain-redis-rate-limiter
```

```bash
uv pip install langchain-redis-rate-limiter
```

## Usage

### Direct Model Integration (Recommended)

You can pass the `RedisRateLimiter` directly to LangChain models that support the `rate_limiter` parameter (e.g., `ChatOpenAI`, `ChatAnthropic`, `ChatGoogleGenerativeAI`).

```python
from langchain_redis_rate_limiter import RedisRateLimiter
from langchain_openai import ChatOpenAI

# 1 request per second (60 RPM)
limiter = RedisRateLimiter(
    redis_url="redis://localhost:6379",
    requests_per_second=1,
    check_every_n_seconds=0.1,
    max_bucket_size=1
)

model = ChatOpenAI(
    model="gpt-4o",
    rate_limiter=limiter
)

model.invoke("Hello world")
```

### TLS/SSL Connection (AWS ElastiCache, etc.)

If Encryption in Transit is enabled on AWS ElastiCache, Valkey, or other managed Redis services, you must use the `rediss://` scheme instead of `redis://`.

```
limiter = RedisRateLimiter(
    redis_url="rediss://master.example-cache.amazonaws.com:6379",
    ...
)
```

## Parameters

- `redis_url`: Redis connection URL (e.g., redis://localhost:6379).
- `key_prefix`: Prefix for Redis keys (default: langchain_limiter). Use different prefixes for different limit rules.
- `requests_per_second`: The maximum number of requests allowed per second. For example, setting this to 5 means you can make up to five requests each second. To configure Requests Per Minute (RPM), simply divide your desired RPM by 60 (e.g., setting this to `0.5` equals 30 RPM).
- `check_every_n_seconds`: When the limit is reached and a request needs to wait, this value determines how often the system checks again to see whether a new request is allowed. Example: 0.1 checks every 0.1 seconds.
- `max_bucket_size`: Controls how many requests can be handled in a short burst. A larger value allows brief spikes in traffic before the limiter slows things down.

## License

Apache-2.0 license
