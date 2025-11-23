# GerdsenAI-CLI Upgrade Guide

## November 2025 Major Overhaul

This guide covers the comprehensive overhaul completed in November 2025.

## Summary of Changes

### Critical Fixes

**Timeout Configuration (FIXED)**
- All timeouts increased from 30s to 600s (10 minutes) for local AI compatibility
- Granular timeout controls added for different operations
- Configurable per-operation timeouts in Settings

**Package Updates**
- All dependencies updated to latest Nov 2025 versions
- No deprecated packages
- Added tiktoken 0.8.0 and cachetools 5.5.0

### New Features

**Request Caching**
- TTL-based cache (1 hour default, configurable)
- SHA256 content hashing
- Automatic caching for deterministic requests (temperature < 0.5)
- Cache statistics tracking

**Rate Limiting**
- Token bucket algorithm (2 rps default, burst of 5)
- Per-operation rate limits
- Prevents overwhelming local AI servers

**Accurate Token Counting**
- Replaced 4-char/token heuristic with tiktoken
- Supports 15+ model families
- Smart message truncation

**TUI Improvements**
- Dynamic terminal width (60-120 chars)
- Better error handling
- Robust markdown rendering

### Configuration Changes

**New Settings Fields**

```python
# Old configuration (still works)
api_timeout = 30.0  # seconds

# New configuration (recommended)
api_timeout = 600.0  # Default timeout
health_check_timeout = 10.0  # Health checks
model_list_timeout = 30.0  # Model listing
chat_timeout = 600.0  # Chat completions
stream_timeout = 600.0  # Streaming responses
```

### Migration

**Automatic Migration**
- Existing configurations automatically use new 600s defaults
- No manual migration required
- Old api_timeout values respected if customized

**Recommended Updates**

Update your config.json to use granular timeouts:

```json
{
  "api_timeout": 600.0,
  "health_check_timeout": 10.0,
  "model_list_timeout": 30.0,
  "chat_timeout": 600.0,
  "stream_timeout": 600.0,
  "max_retries": 3
}
```

### Breaking Changes

**Timeout Defaults**
- Default timeout increased from 30s to 600s
- May affect tests expecting quick timeouts
- Update test fixtures to use shorter timeouts if needed

**Settings Schema**
- Added new timeout fields
- Auto-migrated with backward compatibility

### Upgrade Steps

1. Pull latest code
2. Install updated dependencies: `pip install -e .[dev]`
3. Run tests to verify: `pytest`
4. Update custom configs (optional)

### New Capabilities

**Cache Usage**

```python
from gerdsenai_cli.core.cache import get_cache

cache = get_cache()
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")
```

**Rate Limiting**

```python
from gerdsenai_cli.core.rate_limiter import get_rate_limiter

limiter = get_rate_limiter(requests_per_second=5.0)
await limiter.acquire("chat")
```

**Token Counting**

```python
from gerdsenai_cli.core.token_counter import count_tokens

tokens = count_tokens("Hello, world!", model="llama-2-7b")
print(f"Tokens: {tokens}")
```

### Performance Improvements

- Request caching reduces redundant API calls
- Rate limiting prevents server overload
- Accurate token counting improves context budgeting

### Testing

**New Test Suite**
- 1,020+ tests across 40 test files
- Comprehensive coverage of new features
- Integration tests for timeout scenarios

**Run Tests**

```bash
pytest                          # All tests
pytest tests/test_cache.py      # Cache tests
pytest tests/test_rate_limiter.py  # Rate limiter tests
pytest tests/test_token_counter.py # Token counter tests
```

### Troubleshooting

**Timeouts Still Too Short**

Increase specific timeouts in config.json:

```json
{
  "chat_timeout": 1200.0,  # 20 minutes
  "stream_timeout": 1800.0  # 30 minutes
}
```

**Cache Not Working**

Check temperature setting (caching only works for temperature < 0.5):

```python
settings.user_preferences["temperature"] = 0.3  # Enable caching
```

**Rate Limiting Too Strict**

Adjust rate limits:

```json
{
  "rate_limit_rps": 10.0,  # 10 requests per second
  "rate_limit_burst": 20   # Allow bursts of 20
}
```

### Support

For issues or questions:
- GitHub Issues: https://github.com/GerdsenAI/GerdsenAI-CLI/issues
- Documentation: README.md
