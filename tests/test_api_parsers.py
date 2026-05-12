"""Tests for API client parsing logic — no network calls."""
from decimal import Decimal
import pytest

from app.api.polymarket import (
    _dec,
    _extract_positions,
    _extract_profile_entry,
    _sum_field,
    _active_count,
    _parse_dt,
)


# ---------------------------------------------------------------------------
# polymarket parsers
# ---------------------------------------------------------------------------

class TestPolymarketParsers:
    def test_extract_profile_list(self):
        payload = [{"name": "alice", "pseudonym": "Alice"}]
        entry = _extract_profile_entry(payload)
        assert entry["name"] == "alice"

    def test_extract_profile_dict_direct(self):
        payload = {"name": "bob"}
        assert _extract_profile_entry(payload)["name"] == "bob"

    def test_extract_profile_dict_with_data(self):
        payload = {"data": [{"name": "carol"}]}
        assert _extract_profile_entry(payload)["name"] == "carol"

    def test_extract_profile_empty_list(self):
        assert _extract_profile_entry([]) == {}

    def test_extract_profile_none(self):
        assert _extract_profile_entry(None) == {}

    def test_extract_positions_list(self):
        payload = [{"currentValue": "10"}, {"currentValue": "20"}]
        result = _extract_positions(payload)
        assert len(result) == 2

    def test_extract_positions_dict_with_data(self):
        payload = {"data": [{"currentValue": "5"}]}
        result = _extract_positions(payload)
        assert len(result) == 1

    def test_extract_positions_empty(self):
        assert _extract_positions([]) == []

    def test_sum_field_basic(self):
        entries = [{"cashPnl": "10.5"}, {"cashPnl": "5.5"}]
        assert _sum_field(entries, "cashPnl") == Decimal("16.0")

    def test_sum_field_with_none(self):
        entries = [{"cashPnl": "10"}, {"cashPnl": None}]
        assert _sum_field(entries, "cashPnl") == Decimal("10")

    def test_sum_field_all_missing(self):
        entries = [{"other": "10"}]
        assert _sum_field(entries, "cashPnl") is None

    def test_sum_field_empty(self):
        assert _sum_field([], "cashPnl") is None

    def test_active_count_basic(self):
        entries = [
            {"currentValue": "100"},
            {"currentValue": "0"},
            {"currentValue": "50"},
        ]
        assert _active_count(entries) == 2

    def test_active_count_all_zero(self):
        entries = [{"currentValue": "0"}, {"currentValue": "0"}]
        assert _active_count(entries) == 0

    def test_active_count_no_value_field(self):
        entries = [{"other": "10"}]
        assert _active_count(entries) is None

    def test_parse_dt_iso(self):
        dt = _parse_dt("2024-01-15T12:00:00Z")
        assert dt is not None
        assert dt.year == 2024

    def test_parse_dt_none(self):
        assert _parse_dt(None) is None

    def test_parse_dt_empty_string(self):
        assert _parse_dt("") is None

    def test_dec_valid(self):
        assert _dec("123.45") == Decimal("123.45")

    def test_dec_none(self):
        assert _dec(None) is None

    def test_dec_invalid(self):
        assert _dec("not-a-number") is None
