import pytest
from backend.app.semantic.registry import (
    get_semantic_registry,
    METRIC_DEFINITIONS,
    DIMENSION_DEFINITIONS,
    format_metric_value
)

def test_semantic_registry():
    registry = get_semantic_registry()
    metric_names = [m.name for m in registry.metrics]
    assert "revenue" in metric_names
    assert "profit" in metric_names
    assert "profit_margin" in metric_names
    assert "quantity" in metric_names

    dim_names = [d.name for d in registry.dimensions]
    assert "country" in dim_names
    assert "region" in dim_names
    assert "product_name" in dim_names
    assert "category" in dim_names
    assert "month_name" in dim_names

def test_metric_formatting():
    assert format_metric_value(740910750.0, "currency") == "$740.91M"
    assert format_metric_value(26.29, "percentage") == "26.29%"
    assert format_metric_value(24215, "integer") == "24,215"
    assert format_metric_value(None, "currency") == "N/A"
