from trade_engine.engine.order_journal import OrderJournal


def test_order_journal_record_update_and_query(tmp_path):
    db_file = tmp_path / "orders.sqlite"
    journal = OrderJournal(str(db_file))

    journal_id = journal.record_order(
        symbol="TCS.NS",
        side="BUY",
        quantity=10,
        price=100.0,
        mode="live",
        status="SENT",
        broker_order_id="abc-123",
    )
    assert journal_id > 0

    open_orders = journal.get_open_live_orders()
    assert len(open_orders) == 1
    assert open_orders[0]["broker_order_id"] == "abc-123"

    updated = journal.update_order(journal_id=journal_id, status="COMPLETE", reason="filled")
    assert updated

    open_orders_after = journal.get_open_live_orders()
    assert len(open_orders_after) == 0
