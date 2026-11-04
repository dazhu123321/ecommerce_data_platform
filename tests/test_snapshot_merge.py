from unittest.mock import MagicMock
import pytest

from ingestion.reconciliation import (
    SOURCE, TARGET, build_reconciliation_sql, reconcile, validate_snapshot,
)
from ingestion.merge import build_merge_sql, run_merge


def mock_connection(counts=(("INSERT", 1), ("UPDATE", 1),
                            ("UNCHANGED", 1), ("MISSING", 1)),
                    source=(3, 3, 0), target=(3, 3, 0)):
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchone.side_effect = [source, target]
    cursor.fetchall.return_value = counts
    return conn, cursor


def test_reconciliation_sql_uses_null_safe_changes_and_full_outer_join():
    sql = build_reconciliation_sql()
    assert "FULL OUTER JOIN" in sql
    assert "IS DISTINCT FROM" in sql
    assert SOURCE in sql and TARGET in sql


def test_merge_sql_is_explicit_and_no_delete():
    sql = build_merge_sql()
    assert "WHEN NOT MATCHED" in sql
    assert "THEN UPDATE SET" in sql
    assert "INSERT (ORDER_ID" in sql
    assert "DELETE" not in sql.upper()
    assert "UPDATE ALL BY NAME" not in sql
    assert "NUM_OF_ITEM = s.NUM_OF_ITEM" in sql


def test_dry_run_never_writes():
    conn, cursor = mock_connection()
    result = run_merge(conn)
    assert result["applied"] is False
    assert result["before"].inserted == 1
    assert result["before"].missing == 1
    assert not any("MERGE INTO" in c.args[0] for c in cursor.execute.call_args_list)
    conn.commit.assert_not_called()


def test_reject_empty_staging():
    cursor = MagicMock()
    cursor.fetchone.return_value = (0, 0, 0)
    with pytest.raises(ValueError, match="empty"):
        validate_snapshot(cursor, SOURCE)


def test_reject_duplicate_keys():
    cursor = MagicMock()
    cursor.fetchone.return_value = (3, 2, 0)
    with pytest.raises(ValueError, match="primary key"):
        validate_snapshot(cursor, SOURCE)


def test_reject_unknown_table():
    with pytest.raises(ValueError, match="lab tables"):
        validate_snapshot(MagicMock(), "ECOM_RAW.THELOOK.ORDERS")
