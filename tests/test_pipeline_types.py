# tests/test_pipeline_types.py
from __future__ import annotations

import pytest

from chardet.pipeline import DetectionResult, PipelineContext


def test_detection_result_fields():
    r = DetectionResult(encoding="utf-8", confidence=0.99, language="en")
    assert r.encoding == "utf-8"
    assert r.confidence == 0.99
    assert r.language == "en"


def test_detection_result_to_dict():
    r = DetectionResult(encoding="utf-8", confidence=0.99, language=None)
    d = r.to_dict()
    assert d == {"encoding": "utf-8", "confidence": 0.99, "language": None}


def test_detection_result_none():
    r = DetectionResult(encoding=None, confidence=0.0, language=None)
    assert r.to_dict() == {"encoding": None, "confidence": 0.0, "language": None}


def test_detection_result_is_frozen():
    import dataclasses

    r = DetectionResult(encoding="utf-8", confidence=0.99, language=None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.encoding = "ascii"


def test_pipeline_context_defaults():
    ctx = PipelineContext()
    assert ctx.analysis_cache == {}
    assert ctx.non_ascii_count == -1
    assert ctx.mb_scores == {}


def test_pipeline_context_is_mutable():
    ctx = PipelineContext()
    ctx.analysis_cache[(123, 5, "utf-8")] = (0.9, 10, 5)
    ctx.non_ascii_count = 42
    ctx.mb_scores["shift_jis"] = 0.85
    assert ctx.analysis_cache[(123, 5, "utf-8")] == (0.9, 10, 5)
    assert ctx.non_ascii_count == 42
    assert ctx.mb_scores["shift_jis"] == 0.85
