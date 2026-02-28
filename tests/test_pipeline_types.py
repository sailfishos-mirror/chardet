# tests/test_pipeline_types.py
from __future__ import annotations

import pytest

from chardet.pipeline import DetectionResult


def test_detection_result_fields():
    r = DetectionResult(encoding="utf-8", confidence=0.99, language="English")
    assert r.encoding == "utf-8"
    assert r.confidence == 0.99
    assert r.language == "English"


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
