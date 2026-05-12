"""Contract checks between DB SQL and protobuf messages."""

from app.generated import wallet_pb2


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
