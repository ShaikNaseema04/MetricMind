import pytest
from backend.app.services.query_planner import plan_query
from backend.app.services.analytical_engine import execute_analytical_plan

def test_query_total_revenue():
    plan = plan_query("What is the total revenue?")
    assert "revenue" in plan.metrics
    res = execute_analytical_plan(plan, "What is the total revenue?")
    assert len(res.data) == 1
    assert res.data[0]["revenue"] == 740910750.0
    assert "740.91M" in res.explanation
    assert res.sql_trace.sql.startswith("SELECT")
    assert res.api_trace.status_code == 200

def test_query_country_highest_revenue():
    plan = plan_query("Which country has the highest revenue?")
    assert "country" in plan.dimensions
    assert "revenue" in plan.metrics
    res = execute_analytical_plan(plan, "Which country has the highest revenue?")
    assert len(res.data) > 0
    # First row is top country
    assert "country" in res.data[0]
    assert res.data[0]["revenue"] > 0
    assert res.chart_meta is not None
    assert res.chart_meta.chart_type in ["bar", "horizontal_bar"]

def test_query_monthly_trends():
    plan = plan_query("Show monthly revenue trends.")
    assert "month_name" in plan.dimensions
    res = execute_analytical_plan(plan, "Show monthly revenue trends.")
    assert len(res.data) == 12  # 12 months in 2025
    assert res.chart_meta.chart_type == "line"

def test_query_why_revenue_decreased():
    plan = plan_query("Why did revenue decrease last month?")
    assert plan.requires_secondary_breakdown is True
    res = execute_analytical_plan(plan, "Why did revenue decrease last month?")
    assert res.secondary_breakdown is not None
    assert len(res.secondary_breakdown.data) > 0
    assert "cannot" in res.explanation or "does not contain" in res.explanation
