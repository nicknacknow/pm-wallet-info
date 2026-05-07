"""Tests for gRPC response builder helpers."""
from datetime import datetime, timezone
from google.protobuf.timestamp_pb2 import Timestamp
import pytest

from app.rpc.server import _ts, _str, _int


class TestTimestampHelper:
    def test_none_returns_zero_timestamp(self):
        t = _ts(None)
        assert isinstance(t, Timestamp)
        assert t.seconds == 0

    def test_aware_datetime(self):
        dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        t = _ts(dt)
        assert t.seconds > 0

    def test_naive_datetime_treated_as_utc(self):
        naive = datetime(2024, 6, 1, 12, 0, 0)
        aware = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert _ts(naive).seconds == _ts(aware).seconds


class TestStrHelper:
    def test_none_returns_empty(self):
        assert _str(None) == ""

    def test_decimal_str(self):
        from decimal import Decimal
        assert _str(Decimal("123.45")) == "123.45"

    def test_string_passthrough(self):
        assert _str("hello") == "hello"


class TestIntHelper:
    def test_none_returns_zero(self):
        assert _int(None) == 0

    def test_int_passthrough(self):
        assert _int(42) == 42

    def test_string_int(self):
        assert _int("7") == 7
