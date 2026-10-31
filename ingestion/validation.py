
import pandas as pd


def validate_orders(df: pd.DataFrame) -> None:
    """Validate essential rules before loading orders."""

    required_columns = [
        "order_id",
        "user_id",
        "num_of_item",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    if df["order_id"].isna().any():
        raise ValueError("order_id contains null values")

    if df["order_id"].duplicated().any():
        raise ValueError("Duplicate order_id found")

    if df["num_of_item"].isna().any():
        raise ValueError("num_of_item contains null values")

    if (df["num_of_item"] < 0).any():
        raise ValueError("Negative num_of_item found")
