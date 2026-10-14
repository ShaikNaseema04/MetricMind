import pytest
from pathlib import Path
from backend.app.services.data_loader import inspect_and_load_dataset, get_cached_overview
from backend.app.database.db import execute_query

def test_dataset_ingestion():
    overview = inspect_and_load_dataset(force=False)
    assert overview.is_source_accessible is True
    assert overview.total_files >= 5
    assert overview.total_orders == 10000
    assert overview.completed_orders == 5996
    assert overview.completed_revenue == 740910750.0
    assert overview.completed_profit == 194796053.42
    assert overview.overall_margin_pct == 26.29
    assert overview.total_quantity == 24215

def test_database_tables_and_view():
    orders = execute_query("SELECT COUNT(*) AS cnt FROM orders;")
    assert orders[0]["cnt"] == 10000

    products = execute_query("SELECT COUNT(*) AS cnt FROM products;")
    assert products[0]["cnt"] == 12

    customers = execute_query("SELECT COUNT(*) AS cnt FROM customers;")
    assert customers[0]["cnt"] == 500

    enriched = execute_query("SELECT COUNT(*) AS cnt FROM v_orders_enriched WHERE order_status = 'Completed';")
    assert enriched[0]["cnt"] == 5996
