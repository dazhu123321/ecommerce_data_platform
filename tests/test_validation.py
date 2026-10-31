
import pandas as pd
import pytest

from ingestion.validation import validate_orders


def test_valid_orders():
    df = pd.DataFrame({
        "order_id": [1, 2, 3],
        "user_id": [101, 102, 103],
        "num_of_item": [1, 2, 3],
    })

    validate_orders(df)


def test_null_order_id():
    df = pd.DataFrame({
        "order_id": [1, None, 3],
        "user_id": [101, 102, 103],
        "num_of_item": [1, 2, 3],
    })

    with pytest.raises(
        ValueError, match="order_id contains null"
    ):
        validate_orders(df)


def test_duplicate_order_id():
    df = pd.DataFrame({
        "order_id": [1, 1, 3],
        "user_id": [101, 102, 103],
        "num_of_item": [1, 2, 3],
    })

    with pytest.raises(
        ValueError, match="Duplicate order_id"
    ):
        validate_orders(df)


def test_negative_num_of_item():
    df = pd.DataFrame({
        "order_id": [1, 2, 3],
        "user_id": [101, 102, 103],
        "num_of_item": [1, -2, 3],
    })

    with pytest.raises(
        ValueError, match="Negative num_of_item"
    ):
        validate_orders(df)


def test_missing_column():
    df = pd.DataFrame({
        "order_id": [1, 2],
        "user_id": [101, 102],
    })

    with pytest.raises(
        ValueError, match="Missing columns"
    ):
        validate_orders(df)
