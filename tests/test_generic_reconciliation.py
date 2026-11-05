
from unittest.mock import MagicMock

import pytest

from ingestion.generic_reconciliation import (
    lab_pair,
    build_reconciliation_sql,
    reconcile_pair,
    validate_key,
    TablePair,
)


@pytest.mark.parametrize(
    "table_name,expected_key",
    [
        ("orders", "ORDER_ID"),
        ("order_items", "ID"),
        ("users", "ID"),
        ("products", "ID"),
    ],
)
def test_lab_pair(table_name, expected_key):

    pair = lab_pair(table_name)

    assert pair.primary_key == expected_key

    assert pair.source == (
        f"ECOM_RAW.ANALYTICS_DEV."
        f"{table_name.upper()}_MERGE_LAB_SOURCE"
    )

    assert pair.target == (
        f"ECOM_RAW.ANALYTICS_DEV."
        f"{table_name.upper()}_MERGE_LAB_TARGET"
    )

    assert "THELOOK" not in pair.source
    assert "THELOOK" not in pair.target


def test_sql_is_read_only():

    pair = lab_pair("orders")
    sql = build_reconciliation_sql(pair)

    assert "FULL OUTER JOIN" in sql
    assert "IS DISTINCT FROM" in sql

    assert "MERGE INTO" not in sql
    assert "DELETE FROM" not in sql


def test_reject_unknown_table():

    with pytest.raises(ValueError):
        lab_pair("unknown")


def test_reject_duplicate_keys():

    cursor = MagicMock()
    cursor.fetchone.return_value = (3, 2, 0)

    with pytest.raises(ValueError):
        validate_key(cursor, "TEST_TABLE", "ID")


def test_reconciliation_counts():

    cursor = MagicMock()

    cursor.fetchone.side_effect = [
        (3, 3, 0),
        (3, 3, 0),
    ]

    cursor.fetchall.return_value = [
        ("INSERT", 1),
        ("UPDATE", 1),
        ("UNCHANGED", 1),
        ("MISSING", 1),
    ]

    result = reconcile_pair(
        cursor,
        lab_pair("orders"),
    )

    assert result["INSERT"] == 1
    assert result["UPDATE"] == 1
    assert result["UNCHANGED"] == 1
    assert result["MISSING"] == 1


def test_reject_non_lab_pair():

    pair = lab_pair("orders")

    invalid_pair = TablePair(
        name=pair.name,
        source=pair.source,
        target="ECOM_RAW.THELOOK.ORDERS",
        primary_key=pair.primary_key,
        columns=pair.columns,
    )

    with pytest.raises(ValueError):
        reconcile_pair(MagicMock(), invalid_pair)
