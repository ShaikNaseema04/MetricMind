import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_get_dataset():
    res = client.get("/api/dataset")
    assert res.status_code == 200
    data = res.json()
    assert data["total_orders"] == 10000
    assert data["completed_revenue"] == 740910750.0

def test_get_metrics():
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.json()
    assert len(data["metrics"]) >= 4

def test_post_chat():
    res = client.post("/api/chat", json={"question": "What is the total revenue?"})
    assert res.status_code == 200
    data = res.json()
    assert "explanation" in data
    assert "answer" in data
    assert data["answer"] == data["explanation"]
    assert "response" in data
    assert data["response"] == data["explanation"]
    assert "message" in data
    assert "sql" in data
    assert data["sql"].startswith("SELECT")
    assert "generated_sql" in data
    assert "sql_trace" in data
    assert "api_trace" in data
    assert len(data["data"]) == 1
    assert "results" in data
    assert len(data["results"]) == 1
    if "kpi_items" in data and len(data["kpi_items"]) > 0:
        assert "formattedValue" in data["kpi_items"][0]
        assert data["kpi_items"][0]["formattedValue"] == data["kpi_items"][0]["formatted_value"]

def test_analytics_query():
    res = client.post("/api/analytics/query", json={"order_status": "Completed"})
    assert res.status_code == 200
    data = res.json()
    assert "kpis" in data
    assert data["kpis"]["total_revenue"] == 740910750.0
    assert "monthly_trend" in data
    assert len(data["monthly_trend"]) == 12

def test_integrations():
    res = client.get("/api/integrations")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 4
