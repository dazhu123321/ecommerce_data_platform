
import pytest

from ingestion.table_config import (
    PRIMARY_KEYS,
    get_table_config,
    get_all_table_configs,
)


@pytest.mark.parametrize(
    "table_name,expected_pk",
    [
        ("orders", "ORDER_ID"),
        ("order_items", "ID"),
        ("users", "ID"),
        ("products", "ID"),
    ],
)
def test_primary_key(table_name, expected_pk):
    config = get_table_config(table_name)

    assert config.primary_key == expected_pk
    assert expected_pk in config.columns


def test_four_tables_supported():
    configs = get_all_table_configs()

    assert len(configs) == 4
    assert {c.name for c in configs} == set(PRIMARY_KEYS)


def test_primary_key_excluded_from_comparison():
    for config in get_all_table_configs():
        assert config.primary_key not in config.compare_columns


def test_users_geography_column():
    config = get_table_config("users")

    assert "USER_GEOM" in config.columns


def test_unsupported_table_rejected():
    with pytest.raises(ValueError):
        get_table_config("unknown_table")
