# LangChain Redis Rate Limiter

[English](README.md) | [한국어](README_ko.md)

LangChain의 `BaseRateLimiter`와 호환되는 Redis 기반 RateLimiter입니다. **분당/초당 요청 수(RPM/RPS)** 제한 기능을 지원하며, 분산 환경에서도 안정적으로 사용이 가능합니다.

## 주요 기능

- **Redis 지원**: Local Redis, AWS ElastiCache, Valkey와 호환됩니다.
- **LangChain 통합**: `BaseRateLimiter`를 상속받아 LangChain 모델에 직접 사용할 수 있습니다.
- **비동기 지원**: 동기(Sync) 및 비동기(Async) 요청을 모두 지원합니다.
- **분산 환경 지원**: Redis를 통해 여러 서버나 프로세스 간에 공유되는 상태를 관리할 수 있습니다.

## 설치

```bash
pip install langchain-redis-rate-limiter
```

## 사용법

### 모델 직접 통합 (권장)

`rate_limiter` 매개변수를 지원하는 LangChain 모델(예: `ChatOpenAI`, `ChatAnthropic`, `ChatGoogleGenerativeAI`)에 `RedisRateLimiter`를 직접 전달할 수 있습니다.

```python
from langchain_redis_rate_limiter import RedisRateLimiter
from langchain_openai import ChatOpenAI

# 초당 1회 요청 (60 RPM)
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

### 매개변수

- redis_url: Redis 연결 URL (예: redis://localhost:6379)
- key_prefix: Redis 키 접두사 (기본값: langchain_limiter). 여러 모델에 다른 제한을 걸고 싶다면 이 값을 다르게 설정하세요.
- requests_per_second: 1초 동안 몇 번까지 요청을 보낼 수 있는지 설정합니다. 예: 5라면 초당 최대 5번까지 호출 가능합니다.
- check_every_n_seconds: 요청이 너무 많아 잠시 대기해야 할 때, "다시 요청을 다시 보내도 되는지" 확인하는 간격입니다. 예: 0.1이면 0.1초마다 다시 확인합니다.
- max_bucket_size: 짧은 순간에 얼마나 많은 요청 폭주를 허용할지 결정하는 값입니다. 값이 클수록 짧은 시간 동안 더 많은 요청을 보낼 수 있습니다.

## 라이선스

Apache-2.0 license
