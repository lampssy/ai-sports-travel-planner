# Open-Meteo Backfill Transport Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make historical weather backfills less fragile by reusing HTTP connections, adding jittered pacing, and cooling down globally when repeated timeout-like provider pressure appears.

**Architecture:** Keep Open-Meteo access isolated in `app/integrations/open_meteo.py` and keep backfill orchestration in `app/data/backfill_historical_weather.py`. Use `httpx.Client` for connection pooling and convert retry/rate-limit logic to handle `httpx` exceptions while preserving existing `urllib.error.HTTPError` test compatibility.

**Tech Stack:** Python 3.13, `httpx`, FastAPI project dependencies, pytest, GitHub Actions workflow inputs.

---

## Decision And Review Gate

Classification: `review-gated`

Reason: This changes external-provider transport behavior, retry timing, batch-job reliability, dependency scope, and operational runbook behavior.

Developer Decision Checkpoints before implementation:

1. Dependency scope: promote `httpx` from dev-only dependency to runtime dependency. This is required if `OpenMeteoClient` imports `httpx` in production code.
2. Default pacing policy: use `request_jitter_ratio=0.25`, `retry_jitter_ratio=0.25`, `provider_pressure_error_threshold=3`, and `provider_pressure_cooldown_seconds=300`.
3. Counter semantics: count timeout-like provider-pressure errors across the whole backfill run and reset only after a cooldown. Do not reset after every successful retry, because the observed failure pattern is repeated first-attempt handshake timeouts across many chunks.

ADR status: not required unless the implementation expands into a broader provider abstraction or changes where weather data is fetched. Update `docs/engineering-notes.md` and `docs/production-runbook.md` instead.

Advisory review status: recommended before implementation with `observability-ops` and `backend-api` in `design-review` mode. If skipped, record the skip reason in the final handoff.

## File Structure

- Modify `pyproject.toml`: move `httpx>=0.28,<1.0` from dev dependency group into runtime dependencies.
- Modify `uv.lock`: update via `uv lock` or `uv sync --dev --no-config` after dependency change.
- Modify `app/integrations/open_meteo.py`: replace `urlopen` calls with a persistent `httpx.Client`, close support, timeout/limits, and status handling.
- Modify `app/data/backfill_historical_weather.py`: add jitter helpers, `httpx`-aware rate-limit/retry parsing, timeout-like provider-pressure classification, and global cooldown logic.
- Modify `.github/workflows/backfill-historical-weather.yml`: expose jitter/cooldown inputs if CLI options are added.
- Modify `tests/test_open_meteo.py`: add unit coverage for persistent client usage, `httpx` 429 handling, jittered sleep, and provider-pressure cooldown.
- Modify `docs/production-runbook.md`: document recommended backfill pacing and explain cooldown behavior.
- Modify `docs/engineering-notes.md`: briefly document the Open-Meteo transport policy.

## Task 1: Promote `httpx` To Runtime Dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Move dependency in `pyproject.toml`**

Change:

```toml
dependencies = [
  "fastapi>=0.115,<1.0",
  "opentelemetry-api>=1.34,<2.0",
  "opentelemetry-exporter-otlp-proto-http>=1.34,<2.0",
  "opentelemetry-instrumentation-fastapi>=0.55b0,<1.0",
  "opentelemetry-instrumentation-logging>=0.55b0,<1.0",
  "opentelemetry-instrumentation-psycopg>=0.55b0,<1.0",
  "opentelemetry-instrumentation-urllib>=0.55b0,<1.0",
  "opentelemetry-sdk>=1.34,<2.0",
  "uvicorn>=0.34,<1.0",
  "pydantic>=2.11,<3.0",
  "psycopg[binary]>=3.2,<4.0",
]

[dependency-groups]
dev = [
  "pre-commit>=4.2,<5.0",
  "pytest>=8.3,<9.0",
  "ruff>=0.11,<1.0",
  "httpx>=0.28,<1.0",
]
```

to:

```toml
dependencies = [
  "fastapi>=0.115,<1.0",
  "httpx>=0.28,<1.0",
  "opentelemetry-api>=1.34,<2.0",
  "opentelemetry-exporter-otlp-proto-http>=1.34,<2.0",
  "opentelemetry-instrumentation-fastapi>=0.55b0,<1.0",
  "opentelemetry-instrumentation-logging>=0.55b0,<1.0",
  "opentelemetry-instrumentation-psycopg>=0.55b0,<1.0",
  "opentelemetry-instrumentation-urllib>=0.55b0,<1.0",
  "opentelemetry-sdk>=1.34,<2.0",
  "uvicorn>=0.34,<1.0",
  "pydantic>=2.11,<3.0",
  "psycopg[binary]>=3.2,<4.0",
]

[dependency-groups]
dev = [
  "pre-commit>=4.2,<5.0",
  "pytest>=8.3,<9.0",
  "ruff>=0.11,<1.0",
]
```

- [ ] **Step 2: Refresh lockfile**

Run:

```bash
uv lock --no-config
```

Expected: `uv.lock` remains consistent and `httpx` is available to non-dev installs.

- [ ] **Step 3: Commit dependency scope**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: promote httpx for weather transport"
```

## Task 2: Add Persistent `httpx.Client` To Open-Meteo Integration

**Files:**
- Modify: `app/integrations/open_meteo.py`
- Test: `tests/test_open_meteo.py`

- [ ] **Step 1: Write failing test for client reuse**

Add this helper and test to `tests/test_open_meteo.py`:

```python
class FakeHttpxResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class FakeHttpxClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict]] = []
        self.closed = False

    def get(self, url: str, *, params: dict, timeout) -> FakeHttpxResponse:
        self.calls.append((url, params))
        return FakeHttpxResponse(self.payload)

    def close(self) -> None:
        self.closed = True


def test_open_meteo_client_reuses_injected_http_client() -> None:
    fake_http_client = FakeHttpxClient(_historical_payload())
    client = OpenMeteoClient(http_client=fake_http_client)

    client.fetch_historical_weather(
        _ski_area(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        elevation_m=2500,
    )
    client.fetch_historical_weather(
        _ski_area(),
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 2),
        elevation_m=2500,
    )

    assert len(fake_http_client.calls) == 2
    assert fake_http_client.calls[0][0] == OPEN_METEO_ARCHIVE_URL
    assert fake_http_client.calls[1][0] == OPEN_METEO_ARCHIVE_URL
```

If `_historical_payload()` or `_ski_area()` do not exist with these names, reuse the existing test helpers in `tests/test_open_meteo.py` that produce a historical payload and ski area fixture.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_open_meteo.py::test_open_meteo_client_reuses_injected_http_client -q
```

Expected: failure because `OpenMeteoClient` does not accept `http_client`.

- [ ] **Step 3: Implement persistent client**

In `app/integrations/open_meteo.py`, replace `urllib.request.urlopen` usage with `httpx.Client`.

Add imports:

```python
import httpx
```

Remove:

```python
from urllib.request import urlopen
```

Add module constants:

```python
OPEN_METEO_TIMEOUT = httpx.Timeout(
    connect=30.0,
    read=90.0,
    write=10.0,
    pool=30.0,
)
OPEN_METEO_LIMITS = httpx.Limits(
    max_connections=4,
    max_keepalive_connections=2,
    keepalive_expiry=60.0,
)
OPEN_METEO_USER_AGENT = "snowcast-weather-backfill/0.1"
```

Update `OpenMeteoClient`:

```python
class OpenMeteoClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self._http_client = http_client or httpx.Client(
            timeout=OPEN_METEO_TIMEOUT,
            limits=OPEN_METEO_LIMITS,
            headers={"User-Agent": OPEN_METEO_USER_AGENT},
        )
        self._owns_http_client = http_client is None

    def close(self) -> None:
        if self._owns_http_client:
            self._http_client.close()

    def __enter__(self) -> OpenMeteoClient:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def _get_json(
        self,
        url: str,
        *,
        params: dict[str, object],
        timeout: httpx.Timeout,
    ) -> dict[str, Any]:
        response = self._http_client.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
```

Change `fetch_conditions` to build a `params` dict instead of pre-encoded query string:

```python
payload = self._get_json(
    OPEN_METEO_FORECAST_URL,
    params={
        "latitude": resort.latitude,
        "longitude": resort.longitude,
        "elevation": elevation_m or resort.summit_elevation_m,
        "timezone": "auto",
        "forecast_days": 1,
        "hourly": "snow_depth,visibility",
        "daily": ",".join([...]),
        "current": ",".join([...]),
    },
    timeout=httpx.Timeout(connect=15.0, read=45.0, write=10.0, pool=15.0),
)
return payload
```

Change `fetch_historical_weather` similarly:

```python
return self._get_json(
    OPEN_METEO_ARCHIVE_URL,
    params={
        "latitude": resort.latitude,
        "longitude": resort.longitude,
        "elevation": elevation_m or resort.summit_elevation_m,
        "timezone": "auto",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "hourly": "snow_depth",
        "daily": ",".join([...]),
    },
    timeout=OPEN_METEO_TIMEOUT,
)
```

- [ ] **Step 4: Close default client in backfill ownership path**

In `app/data/backfill_historical_weather.py`, replace:

```python
weather_client = client or OpenMeteoClient()
```

with:

```python
weather_client = client or OpenMeteoClient()
owns_weather_client = client is None
```

Wrap the main loop in:

```python
try:
    for resort, ski_area in selected_ski_areas:
        ...
finally:
    if owns_weather_client:
        weather_client.close()
```

Keep indentation narrow by extracting the current nested loop into a private helper only if the patch becomes too hard to read.

- [ ] **Step 5: Run Open-Meteo tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_open_meteo.py -q
```

Expected: existing tests and new persistent-client test pass.

- [ ] **Step 6: Commit persistent client**

```bash
git add app/integrations/open_meteo.py app/data/backfill_historical_weather.py tests/test_open_meteo.py
git commit -m "fix: reuse Open-Meteo HTTP connections"
```

## Task 3: Make Rate-Limit And Retry Helpers `httpx`-Aware

**Files:**
- Modify: `app/data/backfill_historical_weather.py`
- Test: `tests/test_open_meteo.py`

- [ ] **Step 1: Write failing tests for `httpx.HTTPStatusError`**

Add a fake client:

```python
class HttpxRateLimitedHistoricalClient(StubClient):
    def __init__(self, *, retry_after: str | None = None) -> None:
        super().__init__()
        self.calls = 0
        self.retry_after = retry_after

    def fetch_historical_weather(
        self,
        resort,
        *,
        start_date: date,
        end_date: date,
        elevation_m: int | None = None,
    ) -> dict:
        import httpx

        self.calls += 1
        request = httpx.Request("GET", "https://archive-api.open-meteo.com/v1/archive")
        response = httpx.Response(
            429,
            request=request,
            headers=(
                {"Retry-After": self.retry_after}
                if self.retry_after is not None
                else {}
            ),
        )
        raise httpx.HTTPStatusError(
            "Too Many Requests",
            request=request,
            response=response,
        )
```

Add tests:

```python
def test_backfill_historical_weather_aborts_after_httpx_rate_limit(
    monkeypatch,
) -> None:
    sleep_delays: list[float] = []
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.time.sleep",
        lambda seconds: sleep_delays.append(seconds),
    )

    result = backfill_historical_weather(
        client=HttpxRateLimitedHistoricalClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        targets=("tignes", "cervinia"),
        chunk_days=1,
        retry_attempts=1,
        backoff_seconds=30,
    )

    assert result.failed_chunks == 1
    assert result.failures[0].resort_name == "Tignes"
    assert sleep_delays == [30]


def test_backfill_historical_weather_honors_httpx_retry_after_header(
    monkeypatch,
) -> None:
    sleep_delays: list[float] = []
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.time.sleep",
        lambda seconds: sleep_delays.append(seconds),
    )

    result = backfill_historical_weather(
        client=HttpxRateLimitedHistoricalClient(retry_after="12"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        targets=("tignes",),
        chunk_days=1,
        retry_attempts=1,
        backoff_seconds=1,
    )

    assert result.failed_chunks == 1
    assert sleep_delays == [12]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_open_meteo.py::test_backfill_historical_weather_aborts_after_httpx_rate_limit tests/test_open_meteo.py::test_backfill_historical_weather_honors_httpx_retry_after_header -q
```

Expected: failure because `_is_rate_limit_error` and `_retry_after_seconds` only know `urllib.error.HTTPError`.

- [ ] **Step 3: Implement `httpx`-aware helpers**

In `app/data/backfill_historical_weather.py`, add:

```python
import httpx
```

Change `_is_rate_limit_error`:

```python
def _is_rate_limit_error(error: Exception) -> bool:
    if isinstance(error, HTTPError):
        return error.code == 429
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code == 429
    return False
```

Change `_retry_after_seconds`:

```python
def _retry_after_seconds(error: Exception) -> float | None:
    if isinstance(error, HTTPError):
        retry_after = error.headers.get("Retry-After") if error.headers else None
    elif isinstance(error, httpx.HTTPStatusError):
        retry_after = error.response.headers.get("Retry-After")
    else:
        return None

    if retry_after is None:
        return None
    try:
        return max(float(retry_after), 0.0)
    except ValueError:
        return None
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_open_meteo.py::test_backfill_historical_weather_aborts_after_provider_rate_limit tests/test_open_meteo.py::test_backfill_historical_weather_honors_retry_after_header tests/test_open_meteo.py::test_backfill_historical_weather_aborts_after_httpx_rate_limit tests/test_open_meteo.py::test_backfill_historical_weather_honors_httpx_retry_after_header -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit helper compatibility**

```bash
git add app/data/backfill_historical_weather.py tests/test_open_meteo.py
git commit -m "fix: handle httpx provider rate limits"
```

## Task 4: Add Jittered Pacing

**Files:**
- Modify: `app/data/backfill_historical_weather.py`
- Test: `tests/test_open_meteo.py`
- Modify: `.github/workflows/backfill-historical-weather.yml`

- [ ] **Step 1: Write failing helper tests**

Add tests:

```python
def test_jittered_delay_applies_fractional_spread(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.random.uniform",
        lambda lower, upper: upper,
    )

    from app.data.backfill_historical_weather import _jittered_delay_seconds

    assert _jittered_delay_seconds(10, jitter_ratio=0.25) == 12.5


def test_jittered_delay_can_be_disabled() -> None:
    from app.data.backfill_historical_weather import _jittered_delay_seconds

    assert _jittered_delay_seconds(10, jitter_ratio=0) == 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_open_meteo.py::test_jittered_delay_applies_fractional_spread tests/test_open_meteo.py::test_jittered_delay_can_be_disabled -q
```

Expected: failure because `_jittered_delay_seconds` does not exist.

- [ ] **Step 3: Implement jitter helper and validation**

In `app/data/backfill_historical_weather.py`, add:

```python
import random
```

Add constants:

```python
REQUEST_JITTER_RATIO = 0.25
RETRY_JITTER_RATIO = 0.25
```

Add validation in `backfill_historical_weather`:

```python
if request_jitter_ratio < 0:
    raise ValueError("request_jitter_ratio must be non-negative")
if retry_jitter_ratio < 0:
    raise ValueError("retry_jitter_ratio must be non-negative")
```

Add helper:

```python
def _jittered_delay_seconds(base_delay_seconds: float, *, jitter_ratio: float) -> float:
    if base_delay_seconds <= 0 or jitter_ratio <= 0:
        return base_delay_seconds
    spread = base_delay_seconds * jitter_ratio
    return max(random.uniform(base_delay_seconds - spread, base_delay_seconds + spread), 0.0)
```

Update function signature:

```python
def backfill_historical_weather(
    ...
    request_delay_seconds: float = REQUEST_DELAY_SECONDS,
    request_jitter_ratio: float = REQUEST_JITTER_RATIO,
    retry_jitter_ratio: float = RETRY_JITTER_RATIO,
    ...
) -> HistoricalBackfillResult:
```

Update success sleep:

```python
if request_delay_seconds:
    time.sleep(
        _jittered_delay_seconds(
            request_delay_seconds,
            jitter_ratio=request_jitter_ratio,
        )
    )
```

Update retry sleep:

```python
delay_seconds = _jittered_delay_seconds(
    _retry_delay_seconds(
        error,
        attempt=attempt,
        backoff_seconds=backoff_seconds,
    ),
    jitter_ratio=retry_jitter_ratio,
)
```

- [ ] **Step 4: Add CLI args**

Add parser args:

```python
parser.add_argument(
    "--request-jitter-ratio",
    type=float,
    default=REQUEST_JITTER_RATIO,
    help="Fractional jitter applied to successful request delay, for example 0.25.",
)
parser.add_argument(
    "--retry-jitter-ratio",
    type=float,
    default=RETRY_JITTER_RATIO,
    help="Fractional jitter applied to retry delay, for example 0.25.",
)
```

Pass them into `backfill_historical_weather`.

- [ ] **Step 5: Update workflow inputs**

In `.github/workflows/backfill-historical-weather.yml`, add inputs:

```yaml
      request_jitter_ratio:
        description: "Fractional jitter applied to successful request delay."
        required: false
        default: "0.25"
        type: string
      retry_jitter_ratio:
        description: "Fractional jitter applied to retry delay."
        required: false
        default: "0.25"
        type: string
```

Add env:

```yaml
      REQUEST_JITTER_RATIO: ${{ inputs.request_jitter_ratio || '0.25' }}
      RETRY_JITTER_RATIO: ${{ inputs.retry_jitter_ratio || '0.25' }}
```

Validate:

```python
request_jitter_ratio = float(os.environ["REQUEST_JITTER_RATIO"])
retry_jitter_ratio = float(os.environ["RETRY_JITTER_RATIO"])
if request_jitter_ratio < 0:
    raise SystemExit("request_jitter_ratio must be non-negative")
if retry_jitter_ratio < 0:
    raise SystemExit("retry_jitter_ratio must be non-negative")
```

Pass CLI args:

```bash
--request-jitter-ratio "$REQUEST_JITTER_RATIO"
--retry-jitter-ratio "$RETRY_JITTER_RATIO"
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_open_meteo.py::test_jittered_delay_applies_fractional_spread tests/test_open_meteo.py::test_jittered_delay_can_be_disabled tests/test_open_meteo.py::test_backfill_historical_weather_can_throttle_successful_requests -q
```

Expected: all selected tests pass. Existing throttle test may need deterministic monkeypatching of `random.uniform` or `request_jitter_ratio=0`.

- [ ] **Step 7: Commit jittered pacing**

```bash
git add app/data/backfill_historical_weather.py .github/workflows/backfill-historical-weather.yml tests/test_open_meteo.py
git commit -m "fix: jitter weather backfill pacing"
```

## Task 5: Add Global Cooldown For Repeated Timeout-Like Provider Pressure

**Files:**
- Modify: `app/data/backfill_historical_weather.py`
- Test: `tests/test_open_meteo.py`
- Modify: `.github/workflows/backfill-historical-weather.yml`

- [ ] **Step 1: Write failing cooldown test**

Add fake client:

```python
class TimeoutThenSuccessHistoricalClient(StubClient):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def fetch_historical_weather(
        self,
        resort,
        *,
        start_date: date,
        end_date: date,
        elevation_m: int | None = None,
    ) -> dict:
        import httpx

        self.calls += 1
        if self.calls in {1, 3, 5}:
            request = httpx.Request("GET", "https://archive-api.open-meteo.com/v1/archive")
            raise httpx.ConnectTimeout(
                "The handshake operation timed out",
                request=request,
            )
        return super().fetch_historical_weather(
            resort,
            start_date=start_date,
            end_date=end_date,
            elevation_m=elevation_m,
        )
```

Add test:

```python
def test_backfill_historical_weather_cools_down_after_repeated_timeouts(
    monkeypatch,
) -> None:
    sleep_delays: list[float] = []
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.time.sleep",
        lambda seconds: sleep_delays.append(seconds),
    )
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.random.uniform",
        lambda lower, upper: lower,
    )

    result = backfill_historical_weather(
        client=TimeoutThenSuccessHistoricalClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        targets=("tignes",),
        chunk_days=1,
        retry_attempts=1,
        backoff_seconds=10,
        retry_jitter_ratio=0,
        provider_pressure_error_threshold=3,
        provider_pressure_cooldown_seconds=300,
    )

    assert result.failed_chunks == 0
    assert 300 in sleep_delays
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_open_meteo.py::test_backfill_historical_weather_cools_down_after_repeated_timeouts -q
```

Expected: failure because cooldown options and timeout classification do not exist.

- [ ] **Step 3: Implement provider-pressure classifier**

In `app/data/backfill_historical_weather.py`, add imports:

```python
from urllib.error import HTTPError, URLError
```

Ensure `HTTPError` remains imported if already present.

Add constants:

```python
PROVIDER_PRESSURE_ERROR_THRESHOLD = 3
PROVIDER_PRESSURE_COOLDOWN_SECONDS = 300.0
```

Add helper:

```python
def _is_provider_pressure_error(error: Exception) -> bool:
    if isinstance(
        error,
        (
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.PoolTimeout,
        ),
    ):
        return True
    if isinstance(error, TimeoutError):
        return True
    if isinstance(error, URLError):
        reason = str(error.reason).lower()
        return "timed out" in reason or "handshake operation timed out" in reason
    message = str(error).lower()
    return "handshake operation timed out" in message
```

- [ ] **Step 4: Add cooldown state to backfill loop**

Update function signature:

```python
def backfill_historical_weather(
    ...
    provider_pressure_error_threshold: int = PROVIDER_PRESSURE_ERROR_THRESHOLD,
    provider_pressure_cooldown_seconds: float = PROVIDER_PRESSURE_COOLDOWN_SECONDS,
    ...
) -> HistoricalBackfillResult:
```

Add validation:

```python
if provider_pressure_error_threshold < 0:
    raise ValueError("provider_pressure_error_threshold must be non-negative")
if provider_pressure_cooldown_seconds < 0:
    raise ValueError("provider_pressure_cooldown_seconds must be non-negative")
```

Before the area loop:

```python
provider_pressure_errors_since_cooldown = 0
```

Inside `except Exception as error`, before computing retry delay:

```python
cooldown_due = False
if _is_provider_pressure_error(error) and provider_pressure_error_threshold:
    provider_pressure_errors_since_cooldown += 1
    if provider_pressure_errors_since_cooldown >= provider_pressure_error_threshold:
        cooldown_due = True
        provider_pressure_errors_since_cooldown = 0
```

When calculating `delay_seconds`:

```python
base_delay_seconds = _retry_delay_seconds(
    error,
    attempt=attempt,
    backoff_seconds=backoff_seconds,
)
if cooldown_due:
    base_delay_seconds = max(base_delay_seconds, provider_pressure_cooldown_seconds)
    active_logger.warning(
        (
            "[COOLDOWN] provider pressure detected after %s timeout-like "
            "failures; next retry delayed by %.1fs"
        ),
        provider_pressure_error_threshold,
        base_delay_seconds,
    )
delay_seconds = _jittered_delay_seconds(
    base_delay_seconds,
    jitter_ratio=retry_jitter_ratio,
)
```

Do not count `429` as provider-pressure cooldown here; it already has separate rate-limit abort behavior.

- [ ] **Step 5: Add CLI args and workflow inputs**

Add parser args:

```python
parser.add_argument(
    "--provider-pressure-error-threshold",
    type=int,
    default=PROVIDER_PRESSURE_ERROR_THRESHOLD,
    help="Number of timeout-like provider failures before a global cooldown delay.",
)
parser.add_argument(
    "--provider-pressure-cooldown-seconds",
    type=float,
    default=PROVIDER_PRESSURE_COOLDOWN_SECONDS,
    help="Cooldown delay used after repeated timeout-like provider failures.",
)
```

Add workflow inputs:

```yaml
      provider_pressure_error_threshold:
        description: "Timeout-like provider failures before global cooldown."
        required: false
        default: "3"
        type: string
      provider_pressure_cooldown_seconds:
        description: "Cooldown seconds after repeated timeout-like provider failures."
        required: false
        default: "300"
        type: string
```

Pass them through validation, env, and CLI in the same style as existing backfill inputs.

- [ ] **Step 6: Run cooldown tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_open_meteo.py::test_backfill_historical_weather_cools_down_after_repeated_timeouts tests/test_open_meteo.py::test_backfill_historical_weather_retries_and_succeeds tests/test_open_meteo.py::test_backfill_historical_weather_records_failed_chunks_and_continues -q
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit cooldown policy**

```bash
git add app/data/backfill_historical_weather.py .github/workflows/backfill-historical-weather.yml tests/test_open_meteo.py
git commit -m "fix: cool down weather backfills under provider pressure"
```

## Task 6: Update Runbook And Engineering Notes

**Files:**
- Modify: `docs/production-runbook.md`
- Modify: `docs/engineering-notes.md`

- [ ] **Step 1: Update runbook command**

In `docs/production-runbook.md`, replace the large-run example with:

```bash
uv run python -m app.data.backfill_historical_weather \
  --database-url "$DATABASE_URL" \
  --target tignes \
  --start-date 1991-01-01 \
  --end-date 2025-12-31 \
  --retry-attempts 3 \
  --backoff-seconds 30 \
  --request-delay-seconds 10 \
  --request-jitter-ratio 0.25 \
  --retry-jitter-ratio 0.25 \
  --provider-pressure-error-threshold 3 \
  --provider-pressure-cooldown-seconds 300
```

Add text:

```markdown
The Open-Meteo archive client reuses HTTP connections with `httpx.Client`.
Backfill pacing should include jitter so GitHub Actions jobs do not create
predictable request bursts. Repeated timeout-like failures are treated as
provider pressure and trigger a global cooldown before the next retry.
```

- [ ] **Step 2: Update engineering notes**

Add a concise note to `docs/engineering-notes.md`:

```markdown
### Open-Meteo backfill transport policy

Historical archive backfills use a persistent HTTP client to avoid one TLS
handshake per provider chunk. Successful request pacing and retry delays include
jitter, and repeated timeout-like provider failures trigger a global cooldown.
This is intentionally scoped to batch backfills; request-path weather refreshes
should remain fast-failing and observable.
```

- [ ] **Step 3: Commit docs**

```bash
git add docs/production-runbook.md docs/engineering-notes.md
git commit -m "docs: document weather backfill transport policy"
```

## Task 7: Final Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run backend focused tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_open_meteo.py tests/test_services.py tests/test_api.py -q
```

Expected: pass.

- [ ] **Step 2: Run lint**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests
```

Expected: pass.

- [ ] **Step 3: Run formatting check**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff format --check app tests
```

Expected: pass.

- [ ] **Step 4: Run diff hygiene**

```bash
git diff --check
```

Expected: no whitespace errors.

- [ ] **Step 5: Manual dry-run shape**

Run a tiny one-day single-resort backfill against a local or test DB:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.backfill_historical_weather \
  --start-date 2024-01-01 \
  --end-date 2024-01-01 \
  --resort tignes \
  --retry-attempts 1 \
  --backoff-seconds 1 \
  --request-delay-seconds 1 \
  --request-jitter-ratio 0 \
  --retry-jitter-ratio 0 \
  --provider-pressure-error-threshold 3 \
  --provider-pressure-cooldown-seconds 5
```

Expected: command completes or fails only for real provider/database availability reasons. Logs should include normal `[CHUNK]` and `[DONE]` lines.

## Self-Review

Spec coverage:

- Persistent HTTP client with pooling: Task 2.
- Jittered pacing: Task 4.
- Repeated handshake/timeout global cooldown: Task 5.
- Tests: Tasks 2-5 and 7.
- Docs: Task 6.

Known implementation caveat:

- `httpx` is currently dev-only. Task 1 is required before importing `httpx` from production modules.
- Existing `opentelemetry-instrumentation-urllib` will no longer instrument Open-Meteo calls after switching to `httpx`. This plan does not add `opentelemetry-instrumentation-httpx`; add that only if observability review requires client spans for provider calls.
