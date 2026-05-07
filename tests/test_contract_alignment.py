"""Contract checks between DB SQL and protobuf messages."""
import re

from app import db
from app.generated import wallet_pb2


def test_pm_profile_sql_uses_new_columns_only():
    sql = db._UPSERT_PM_PROFILE + db._SELECT_PM_PROFILE  # noqa: SLF001
    assert "total_realized_pnl" in sql
    assert "avg_pnl_per_trade" in sql
    assert "portfolio_value" in sql
    assert re.search(r"\bpnl\b", sql) is None
    assert re.search(r"\bnum_trades\b", sql) is None
    assert re.search(r"\bpositions_count\b", sql) is None
    assert re.search(r"\bpositions_value\b", sql) is None
    assert re.search(r"\bpositions_pnl\b", sql) is None


def test_polymarket_profile_proto_fields_match_new_shape():
    field_names = set(wallet_pb2.PolymarketProfile.DESCRIPTOR.fields_by_name.keys())
    assert {
        "wallet",
        "profile_status",
        "username",
        "display_name",
        "created_at",
        "total_trades",
        "total_volume",
        "total_realized_pnl",
        "win_rate",
        "avg_pnl_per_trade",
        "portfolio_value",
        "last_enriched_at",
    } <= field_names
    assert "pnl" not in field_names
    assert "num_trades" not in field_names
    assert "positions_count" not in field_names


def test_full_profile_proto_fields_match_new_shape():
    field_names = set(wallet_pb2.FullProfile.DESCRIPTOR.fields_by_name.keys())
    assert {
        "wallet",
        "polygon_balance",
        "tx_count",
        "profile_status",
        "username",
        "display_name",
        "created_at",
        "total_trades",
        "total_volume",
        "total_realized_pnl",
        "win_rate",
        "avg_pnl_per_trade",
        "portfolio_value",
        "last_enriched_at",
    } <= field_names
    assert "pnl" not in field_names
    assert "positions_value" not in field_names
