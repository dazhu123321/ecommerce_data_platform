
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# 兼容当前 publish_tables.py 的导入方式
INGESTION_DIR = Path(__file__).resolve().parents[1] / "ingestion"
sys.path.insert(0, str(INGESTION_DIR))

import publish_tables as publisher


def test_publish_success():
    # Arrange：准备假的 Snowflake 连接
    conn = MagicMock()
    cursor = MagicMock()

    # 支持 with conn.cursor() as cursor
    conn.cursor.return_value.__enter__.return_value = cursor

    # 模拟所有 COUNT 查询都返回 100 行
    cursor.fetchone.return_value = (100,)

    # Act：替换真实数据库连接，运行真实函数
    with patch.object(
        publisher, "get_connection", return_value=conn
    ):
        publisher.publish_tables()

    # Assert：检查程序是否按预期执行
    conn.autocommit.assert_called_once_with(False)
    cursor.execute.assert_any_call("BEGIN")

    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()
    conn.close.assert_called_once()


    
def test_row_count_mismatch_rollback():
    # Arrange：准备假的 Snowflake 连接
    conn = MagicMock()
    cursor = MagicMock()

    conn.cursor.return_value.__enter__.return_value = cursor

    # 模拟 STG 有 100 行，正式表只有 99 行
    cursor.fetchone.side_effect = [
        (100,),
        (99,),
    ]

    # Act：运行真实函数，并预期抛出 RuntimeError
    with patch.object(
        publisher, "get_connection", return_value=conn
    ):
        with pytest.raises(
            RuntimeError,
            match="行数不匹配"
        ):
            publisher.publish_tables()

    # Assert：检查异常发生后的事务处理
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()
    conn.close.assert_called_once()


    
def test_delete_order():
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()

    conn.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchone.return_value = (100,)

    # Act
    with patch.object(
        publisher, "get_connection", return_value=conn
    ):
        publisher.publish_tables()

    # Assert：提取执行过的 DELETE SQL
    delete_sql = [
        call.args[0]
        for call in cursor.execute.call_args_list
        if call.args[0].startswith("DELETE FROM")
    ]

    expected_sql = [
        "DELETE FROM ECOM_RAW.THELOOK.ORDER_ITEMS",
        "DELETE FROM ECOM_RAW.THELOOK.ORDERS",
        "DELETE FROM ECOM_RAW.THELOOK.PRODUCTS",
        "DELETE FROM ECOM_RAW.THELOOK.USERS",
    ]

    assert delete_sql == expected_sql



    
def test_insert_order():
    # Arrange
    conn = MagicMock()
    cursor = MagicMock()

    conn.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchone.return_value = (100,)

    # Act
    with patch.object(
        publisher, "get_connection", return_value=conn
    ):
        publisher.publish_tables()

    # Assert：提取执行过的 INSERT SQL
    insert_sql = [
        call.args[0]
        for call in cursor.execute.call_args_list
        if "INSERT INTO" in call.args[0]
    ]

    expected_tables = [
        "USERS",
        "PRODUCTS",
        "ORDERS",
        "ORDER_ITEMS",
    ]

    assert len(insert_sql) == 4

    for sql, table in zip(insert_sql, expected_tables):
        assert (
            f"INSERT INTO ECOM_RAW.THELOOK.{table}"
            in sql
        )


def test_sql_failure_rollback():
    # Arrange：准备 Mock
    conn = MagicMock()
    cursor = MagicMock()

    conn.cursor.return_value.__enter__.return_value = cursor

    # 模拟 Snowflake 执行 SQL 时发生错误
    cursor.execute.side_effect = RuntimeError(
        "Simulated Snowflake SQL error"
    )

    # Act：执行真实 publish_tables()
    with patch.object(
        publisher, "get_connection", return_value=conn
    ):
        with pytest.raises(
            RuntimeError,
            match="Simulated Snowflake SQL error"
        ):
            publisher.publish_tables()

    # Assert：验证异常后的程序行为
    conn.commit.assert_not_called()
    conn.close.assert_called_once()
    conn.rollback.assert_not_called()


