import logging

import pytest

from app.ai.llm_client import LLMClient, LLMClientError
from app.ai.parser import LLMBackedQueryParser
from app.ai.retry import complete_with_retries
from app.observability.metrics import (
    InMemoryMetricsRecorder,
    reset_metrics_recorder_for_tests,
    set_metrics_recorder_for_tests,
)


class FakeCache:
    def __init__(self, payload: dict | None = None) -> None:
        self.payload = payload

    def get_parse_cache(self, cache_key: str) -> dict | None:
        return self.payload

    def set_parse_cache(self, **kwargs) -> None:
        self.payload = kwargs["response"]


class SuccessfulClient(LLMClient):
    @property
    def model(self) -> str:
        return "test-model"

    def complete(self, **kwargs) -> str:
        return (
            '{"filters":{"location":"Italy","skill_level":"intermediate"},'
            '"confidence":0.91,"unknown_parts":[]}'
        )


class EmptyFiltersClient(LLMClient):
    @property
    def model(self) -> str:
        return "test-model"

    def complete(self, **kwargs) -> str:
        return '{"filters":{},"confidence":0.91,"unknown_parts":[]}'


class LowConfidenceClient(LLMClient):
    @property
    def model(self) -> str:
        return "test-model"

    def complete(self, **kwargs) -> str:
        return '{"filters":{"location":"France"},"confidence":0.2,"unknown_parts":[]}'


class InvalidOutputClient(LLMClient):
    @property
    def model(self) -> str:
        return "test-model"

    def complete(self, **kwargs) -> str:
        return "not json"


class FailingClient(LLMClient):
    @property
    def model(self) -> str:
        return "test-model"

    def complete(self, **kwargs) -> str:
        raise LLMClientError("network failed", reason="network_error")


class FlakyRetryClient(LLMClient):
    def __init__(self) -> None:
        self.calls = 0

    @property
    def model(self) -> str:
        return "test-model"

    def complete(self, **kwargs) -> str:
        self.calls += 1
        if self.calls == 1:
            raise LLMClientError("network failed", reason="network_error")
        return "{}"


def test_llm_parser_records_success_mode_and_model():
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    parser = LLMBackedQueryParser(
        client=SuccessfulClient(),
        cache_repository=FakeCache(),
    )
    try:
        payload, debug = parser.parse_with_debug("ski in italy")
    finally:
        reset_metrics_recorder_for_tests()

    assert payload["filters"]["location"] == "Italy"
    assert debug.parser_source == "llm"
    assert (
        "snowcast_parse_requests_total",
        {"mode": "llm", "status": "success"},
        1,
    ) in recorder.counters
    assert (
        "snowcast_llm_requests_total",
        {"operation": "query_parser", "model": "test-model", "status": "success"},
        1,
    ) in recorder.counters
    assert _histogram_values(recorder, "snowcast_parse_confidence") == [0.91]


def test_llm_parser_records_cache_mode_without_llm_request():
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    parser = LLMBackedQueryParser(
        client=SuccessfulClient(),
        cache_repository=FakeCache(
            {
                "filters": {"location": "Italy"},
                "confidence": 0.8,
                "unknown_parts": [],
            }
        ),
    )
    try:
        _, debug = parser.parse_with_debug("ski in italy")
    finally:
        reset_metrics_recorder_for_tests()

    assert debug.parser_source == "llm_cache"
    assert (
        "snowcast_parse_requests_total",
        {"mode": "llm_cache", "status": "success"},
        1,
    ) in recorder.counters
    assert not _counter_entries(recorder, "snowcast_llm_requests_total")


def test_llm_parser_records_fallback_reason_without_query_text():
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    parser = LLMBackedQueryParser(
        client=FailingClient(),
        cache_repository=FakeCache(),
    )
    try:
        _, debug = parser.parse_with_debug("ski in france in march")
    finally:
        reset_metrics_recorder_for_tests()

    assert debug.parser_source == "heuristic_fallback"
    assert debug.fallback_reason == "network_error"
    assert (
        "snowcast_parse_requests_total",
        {"mode": "deterministic_fallback", "status": "fallback"},
        1,
    ) in recorder.counters
    assert (
        "snowcast_llm_fallbacks_total",
        {"operation": "query_parser", "reason": "network_error"},
        1,
    ) in recorder.counters
    assert _all_metric_label_keys_are_allowed(recorder)
    assert _all_metric_label_values_omit_raw_text(
        recorder,
        forbidden=("ski in france in march", "Extract structured", "network failed"),
    )


@pytest.mark.parametrize(
    ("client", "reason", "confidence"),
    [
        (EmptyFiltersClient(), "empty_filters", 0.91),
        (LowConfidenceClient(), "low_confidence", 0.2),
        (InvalidOutputClient(), "invalid_output", None),
    ],
)
def test_llm_parser_records_structured_fallback_reasons(client, reason, confidence):
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    parser = LLMBackedQueryParser(client=client, cache_repository=FakeCache())
    try:
        _, debug = parser.parse_with_debug("ski in france in march")
    finally:
        reset_metrics_recorder_for_tests()

    assert debug.parser_source == "heuristic_fallback"
    assert debug.fallback_reason == reason
    assert (
        "snowcast_llm_fallbacks_total",
        {"operation": "query_parser", "reason": reason},
        1,
    ) in recorder.counters
    assert (
        "snowcast_parse_requests_total",
        {"mode": "deterministic_fallback", "status": "fallback"},
        1,
    ) in recorder.counters
    if confidence is not None:
        assert _histogram_values(recorder, "snowcast_parse_confidence") == [confidence]


def test_retry_helper_records_transient_retries():
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    client = FlakyRetryClient()
    try:
        complete_with_retries(
            llm_client=client,
            operation="query_parser",
            logger=logging.getLogger(__name__),
            system_prompt="prompt",
            user_prompt="raw user query",
            temperature=0,
        )
    finally:
        reset_metrics_recorder_for_tests()

    assert (
        "snowcast_llm_retries_total",
        {"operation": "query_parser", "model": "test-model", "reason": "network_error"},
        1,
    ) in recorder.counters
    assert client.calls == 2


def test_retry_helper_bounds_dynamic_operation_labels():
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    client = FlakyRetryClient()
    try:
        complete_with_retries(
            llm_client=client,
            operation="official_page_llm url=https://example.com/prices",
            logger=logging.getLogger(__name__),
            system_prompt="prompt",
            user_prompt="raw user query",
            temperature=0,
        )
    finally:
        reset_metrics_recorder_for_tests()

    assert (
        "snowcast_llm_retries_total",
        {
            "operation": "official_page_llm",
            "model": "test-model",
            "reason": "network_error",
        },
        1,
    ) in recorder.counters
    assert _all_metric_label_values_omit_raw_text(
        recorder,
        forbidden=("https://example.com/prices", "raw user query"),
    )


def _counter_entries(
    recorder: InMemoryMetricsRecorder, name: str
) -> list[tuple[str, dict[str, str | int | float | bool], int]]:
    return [entry for entry in recorder.counters if entry[0] == name]


def _histogram_values(recorder: InMemoryMetricsRecorder, name: str) -> list[float]:
    return [
        value
        for metric_name, _attributes, value in recorder.histograms
        if metric_name == name
    ]


def _all_metric_label_keys_are_allowed(recorder: InMemoryMetricsRecorder) -> bool:
    allowed = {"operation", "model", "mode", "status", "reason"}
    attributes = [
        metric_attributes for _name, metric_attributes, _amount in recorder.counters
    ] + [metric_attributes for _name, metric_attributes, _value in recorder.histograms]
    return all(set(metric_attributes) <= allowed for metric_attributes in attributes)


def _all_metric_label_values_omit_raw_text(
    recorder: InMemoryMetricsRecorder, *, forbidden: tuple[str, ...]
) -> bool:
    attributes = [
        metric_attributes for _name, metric_attributes, _amount in recorder.counters
    ] + [metric_attributes for _name, metric_attributes, _value in recorder.histograms]
    return all(
        forbidden_text not in str(value)
        for metric_attributes in attributes
        for value in metric_attributes.values()
        for forbidden_text in forbidden
    )
