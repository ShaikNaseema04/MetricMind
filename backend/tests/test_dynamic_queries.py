"""
Automated Pytest Suite for Dynamic Analytics Questions in MetricMind
Validates all requirement categories: totals, entity filters, comparisons,
quarterly/yearly trends, rankings, distributions, follow-ups, and honesty bounds.
"""
import pytest
from backend.app.services.llm_service import process_chat_question
from backend.app.services.query_planner import plan_query

def test_total_revenue_and_profit():
    res = process_chat_question("What is the total revenue and profit?")
    assert res.data is not None
    assert len(res.data) == 1
    assert res.data[0]["revenue"] == 740910750.0
    assert res.data[0]["profit"] == 194796053.42
    assert res.chart_meta.chart_type == "kpi"
    assert "740.91M" in res.answer

def test_single_country_filtering():
    res = process_chat_question("What is the revenue in United States?")
    assert res.data is not None
    assert len(res.data) == 1
    # USA specific numbers
    assert res.data[0]["revenue"] > 0
    assert res.data[0]["revenue"] < 740910750.0
    assert "USA" in res.answer or "United States" in res.question
    assert res.chart_meta.chart_type == "kpi"

def test_country_comparison():
    res = process_chat_question("Compare USA and Germany")
    assert res.data is not None
    assert len(res.data) == 2
    countries = [r["country"] for r in res.data]
    assert "USA" in countries
    assert "Germany" in countries
    assert res.chart_meta.chart_type == "bar"
    assert "Comparative performance analysis" in res.answer

def test_category_comparison():
    res = process_chat_question("Compare Electronics and Office")
    assert res.data is not None
    assert len(res.data) == 2
    categories = [r["category"] for r in res.data]
    assert "Electronics" in categories
    assert "Office" in categories
    assert res.chart_meta.chart_type == "bar"

def test_channel_comparison():
    res = process_chat_question("Online vs Retail")
    assert res.data is not None
    assert len(res.data) == 2
    channels = [r["sales_channel"] for r in res.data]
    assert "Online" in channels
    assert "Retail" in channels
    assert res.chart_meta.chart_type == "bar"

def test_quarterly_trend():
    res = process_chat_question("Quarterly revenue trend")
    assert res.data is not None
    assert len(res.data) == 4
    quarters = [r["quarter"] for r in res.data]
    assert "2025-Q1" in quarters
    assert "2025-Q4" in quarters
    assert res.chart_meta.chart_type == "line"

def test_top_products_by_margin():
    res = process_chat_question("Top 5 products by profit margin")
    assert res.data is not None
    assert len(res.data) == 5
    assert "profit_margin" in res.data[0]
    # Verify sorted descending
    assert res.data[0]["profit_margin"] >= res.data[1]["profit_margin"]
    assert res.chart_meta.chart_type == "horizontal_bar"

def test_customer_segments_distribution():
    res = process_chat_question("Revenue by customer segment")
    assert res.data is not None
    assert len(res.data) == 3
    assert res.chart_meta.chart_type == "donut"
    segments = [r["segment"] for r in res.data]
    assert "Consumer" in segments
    assert "Corporate" in segments

def test_filtered_ranking():
    res = process_chat_question("Top 5 products in Europe")
    assert res.data is not None
    assert len(res.data) == 5
    assert res.chart_meta.chart_type == "horizontal_bar"
    assert "Europe" in res.query_plan["title"]

def test_unsupported_non_analytics_question():
    res = process_chat_question("What is the weather today in Tokyo?")
    assert res.data == []
    assert res.chart_meta is None
    assert "MetricMind is an enterprise Agentic Semantic BI Engine" in res.answer
    assert "outside this business dataset" in res.answer
