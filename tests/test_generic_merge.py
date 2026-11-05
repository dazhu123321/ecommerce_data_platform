
from unittest.mock import MagicMock

import pytest

from ingestion.generic_reconciliation import (
    TablePair,
    lab_pair,
)
from ingestion.generic_merge import (
    build_merge_sql,
    run_merge,
)


@pytest.mark.parametrize(
    "table_name,key",
    [
        ("orders", "ORDER_ID"),
        ("order_items", "ID"),
        ("users", "ID"),
        ("products", "ID"),
    ],
)
def test_merge_sql_for_four_tables(table_name, key):
    pair = lab_pair(table_name)
    sql = build_merge_sql(pair)

    assert f"ON t.{key} = s.{key}" in sql
    assert "MERGE INTO" in sql
    assert "WHEN MATCHED AND" in sql
    assert "WHEN NOT MATCHED" in sql
    assert "IS DISTINCT FROM" in sql

    # Missing records must not be deleted.
    assert "THEN DELETE" not in sql.upper()


def test_merge_sql_uses_explicit_columns():
    sql = build_merge_sql(lab_pair("orders"))

    assert "UPDATE SET" in sql
    assert "INSERT (ORDER_ID" in sql
    assert "NUM_OF_ITEM = s.NUM_OF_ITEM" in sql

    # Avoid physical column-order assumptions.
    assert "ALL BY NAME" not in sql


def test_reject_modified_table_pair():
    pair = lab_pair("orders")

    unsafe_pair = TablePair(
        name=pair.name,
        source=pair.source,
        target="ECOM_RAW.THELOOK.ORDERS",
        primary_key=pair.primary_key,
        columns=pair.columns,
    )

    with pytest.raises(ValueError):
        build_merge_sql(unsafe_pair)


def test_dry_run_does_not_write():
    conn = MagicMock()
    cursor = conn.cursor.return_value

    cursor.fetchone.side_effect = [
        (3, 3, 0),  # Source validation
        (4, 4, 0),  # Target validation
    ]

    cursor.fetchall.return_value = [
        ("UNCHANGED", 3),
        ("MISSING", 1),
    ]

    result = run_merge(
        conn,
        table_name="orders",
        apply=False,
    )

    assert result["applied"] is False
    assert result["before"]["UNCHANGED"] == 3
    assert result["before"]["MISSING"] == 1

    statements = [
        call.args[0].upper()
        for call in cursor.execute.call_args_list
    ]

    assert not any("MERGE INTO" in s for s in statements)
    assert not any("BEGIN TRANSACTION" in s for s in statements)


def test_other_tables_cannot_apply_yet():
    conn = MagicMock()

    with pytest.raises(ValueError, match="ORDERS"):
        run_merge(
            conn,
            table_name="products",
            apply=True,
        )

    conn.cursor.assert_not_called()
