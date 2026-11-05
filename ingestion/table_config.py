
"""Configuration for four-table snapshot synchronization."""

from dataclasses import dataclass

from ingestion.load_table import TABLE_CONFIG


@dataclass(frozen=True)
class TableSyncConfig:
    name: str
    primary_key: str
    columns: tuple[str, ...]

    @property
    def compare_columns(self) -> tuple[str, ...]:
        """Columns compared to detect UPDATE."""
        return tuple(
            col for col in self.columns
            if col != self.primary_key
        )


PRIMARY_KEYS = {
    "orders": "ORDER_ID",
    "order_items": "ID",
    "users": "ID",
    "products": "ID",
}


def get_table_config(table_name: str) -> TableSyncConfig:
    """Return a validated table configuration."""

    if table_name not in PRIMARY_KEYS:
        raise ValueError(
            f"Unsupported table: {table_name}"
        )

    columns = tuple(TABLE_CONFIG[table_name]["columns"])
    primary_key = PRIMARY_KEYS[table_name]

    if primary_key not in columns:
        raise ValueError(
            f"Primary key {primary_key} missing in {table_name}"
        )

    if len(columns) != len(set(columns)):
        raise ValueError(
            f"Duplicate column names in {table_name}"
        )

    return TableSyncConfig(
        name=table_name,
        primary_key=primary_key,
        columns=columns,
    )


def get_all_table_configs() -> list[TableSyncConfig]:
    """Return configurations for all supported tables."""

    return [
        get_table_config(name)
        for name in PRIMARY_KEYS
    ]


if __name__ == "__main__":
    for config in get_all_table_configs():
        print(
            f"{config.name:<12} "
            f"PK={config.primary_key:<10} "
            f"Columns={len(config.columns)}"
        )
