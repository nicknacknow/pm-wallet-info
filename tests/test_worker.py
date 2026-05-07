"""Tests for worker event parsing and logic — no Redis or DB required."""
import json
import pytest

from app.pubsub.worker import _extract_wallet


class TestExtractWallet:
    def test_valid_event(self):
        event = json.dumps({
            "event_type": "trade",
            "event_version": "2.0.0",
            "trade": {
                "wallet": "0xAbC123",
                "block_number": 1,
                "timestamp": "2024-01-01T00:00:00Z",
                "transaction_hash": "0xdeadbeef",
                "token_id": "tok1",
                "condition_id": "0x" + "a" * 64,
                "side": 0,
                "maker_amount": 1000000,
                "taker_amount": 950000,
            }
        })
        assert _extract_wallet(event) == "0xAbC123"

    def test_missing_trade_key(self):
        assert _extract_wallet(json.dumps({"event_type": "trade"})) is None

    def test_missing_wallet_field(self):
        assert _extract_wallet(json.dumps({"trade": {"side": 0}})) is None

    def test_malformed_json(self):
        assert _extract_wallet("not-json") is None

    def test_empty_string(self):
        assert _extract_wallet("") is None

    def test_trade_not_dict(self):
        assert _extract_wallet(json.dumps({"trade": "oops"})) is None

    def test_wallet_empty_string(self):
        assert _extract_wallet(json.dumps({"trade": {"wallet": ""}})) is None

    def test_wallet_is_numeric_coerced_to_str(self):
        # wallet field is coerced to str regardless of type
        event = json.dumps({"trade": {"wallet": 12345}})
        assert _extract_wallet(event) == "12345"
