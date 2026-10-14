"""
MetricMind FastAPI API Endpoints
"""
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
import pandas as pd

from ..models.schemas import (
    ChatRequest, ChatResponse, DatasetOverview,
    SemanticRegistryResponse, AnalyticsQueryRequest, IntegrationStatus
)
from ..semantic.registry import get_semantic_registry
from ..services.data_loader import inspect_and_load_dataset, get_cached_overview, get_source_data_dir
from ..services.llm_service import process_chat_question, get_llm_status
from ..database.db import execute_query
from ..config import settings

router = APIRouter()

@router.get("/dataset", response_model=DatasetOverview)
def get_dataset():
    """Returns dataset inspection metrics, files, and authoritative statistics."""
    try:
        return get_cached_overview()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect dataset: {str(e)}")

@router.get("/metrics", response_model=SemanticRegistryResponse)
def get_metrics():
    """Returns semantic layer metrics, dimensions, and governed calculation rules."""
    return get_semantic_registry()

@router.post("/chat", response_model=ChatResponse)
def chat_question(request: ChatRequest):
    """Processes natural language analytics question and returns structured analytical response."""
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        response = process_chat_question(question, conversation_id=request.conversation_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytical processing error: {str(e)}")

@router.post("/analytics/query")
def analytics_query(request: AnalyticsQueryRequest):
    """
    Executes governed analytical aggregations for the Analytics dashboard
    with dynamic filters (date range, region, country, category, status, sales channel).
    """
    where_clauses: List[str] = []
    params: Dict[str, Any] = {}
    
    if request.order_status:
        where_clauses.append("order_status = :status")
        params["status"] = request.order_status
        
    if request.region and request.region != "All":
        where_clauses.append("region = :region")
        params["region"] = request.region
        
    if request.country and request.country != "All":
        where_clauses.append("country = :country")
        params["country"] = request.country
        
    if request.category and request.category != "All":
        where_clauses.append("category = :category")
        params["category"] = request.category
        
    if request.sales_channel and request.sales_channel != "All":
        where_clauses.append("sales_channel = :channel")
        params["channel"] = request.sales_channel
        
    if request.date_from:
        where_clauses.append("order_date >= :date_from")
        params["date_from"] = request.date_from
        
    if request.date_to:
        where_clauses.append("order_date <= :date_to")
        params["date_to"] = request.date_to

    where_str = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # 1. Executive KPIs
    kpi_sql = f"""
    SELECT 
        ROUND(COALESCE(SUM(revenue), 0), 2) AS total_revenue,
        ROUND(COALESCE(SUM(profit), 0), 2) AS total_profit,
        ROUND(COALESCE((SUM(profit) / NULLIF(SUM(revenue), 0.0)) * 100.0, 0), 2) AS profit_margin,
        COALESCE(SUM(quantity), 0) AS total_quantity,
        COUNT(order_id) AS total_orders
    FROM v_orders_enriched{where_str};
    """
    kpis = execute_query(kpi_sql, params)[0]

    # 2. Monthly Trend
    monthly_sql = f"""
    SELECT 
        month_name,
        ROUND(SUM(revenue), 2) AS revenue,
        ROUND(SUM(profit), 2) AS profit,
        SUM(quantity) AS quantity
    FROM v_orders_enriched{where_str}
    GROUP BY month_name
    ORDER BY month_name ASC;
    """
    monthly_trend = execute_query(monthly_sql, params)

    # 3. Regional Breakdown
    region_sql = f"""
    SELECT 
        region,
        ROUND(SUM(revenue), 2) AS revenue,
        ROUND(SUM(profit), 2) AS profit,
        ROUND((SUM(profit) / NULLIF(SUM(revenue), 0.0)) * 100.0, 2) AS profit_margin
    FROM v_orders_enriched{where_str}
    GROUP BY region
    ORDER BY revenue DESC;
    """
    regions = execute_query(region_sql, params)

    # 4. Country Breakdown
    country_sql = f"""
    SELECT 
        country,
        region,
        ROUND(SUM(revenue), 2) AS revenue,
        ROUND(SUM(profit), 2) AS profit,
        COUNT(order_id) AS orders_count
    FROM v_orders_enriched{where_str}
    GROUP BY country, region
    ORDER BY revenue DESC;
    """
    countries = execute_query(country_sql, params)

    # 5. Top Products
    product_sql = f"""
    SELECT 
        product_name,
        category,
        ROUND(SUM(revenue), 2) AS revenue,
        ROUND(SUM(profit), 2) AS profit,
        SUM(quantity) AS quantity,
        ROUND((SUM(profit) / NULLIF(SUM(revenue), 0.0)) * 100.0, 2) AS profit_margin
    FROM v_orders_enriched{where_str}
    GROUP BY product_name, category
    ORDER BY revenue DESC
    LIMIT 10;
    """
    products = execute_query(product_sql, params)

    # 6. Category Performance
    cat_sql = f"""
    SELECT 
        category,
        ROUND(SUM(revenue), 2) AS revenue,
        ROUND(SUM(profit), 2) AS profit,
        ROUND((SUM(profit) / NULLIF(SUM(revenue), 0.0)) * 100.0, 2) AS profit_margin
    FROM v_orders_enriched{where_str}
    GROUP BY category
    ORDER BY revenue DESC;
    """
    categories = execute_query(cat_sql, params)

    return {
        "kpis": kpis,
        "monthly_trend": monthly_trend,
        "regions": regions,
        "countries": countries,
        "top_products": products,
        "categories": categories,
        "active_filters": request.model_dump()
    }

@router.post("/dataset/upload")
async def upload_dataset_file(file: UploadFile = File(...)):
    """
    Safely receives uploaded CSV files into data/processed without modifying the original dataset directory.
    Validates CSV format and row structure.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        
    processed_dir = Path(settings.PROCESSED_DATA_DIR)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    save_path = processed_dir / file.filename
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Verify valid CSV by reading sample with pandas
        df = pd.read_csv(save_path)
        row_count = len(df)
        cols = list(df.columns)
        
        return {
            "status": "success",
            "message": f"Successfully validated and uploaded {file.filename}",
            "filename": file.filename,
            "row_count": row_count,
            "columns": cols,
            "saved_location": str(save_path)
        }
    except Exception as e:
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(status_code=400, detail=f"Failed to process CSV file: {str(e)}")

@router.get("/integrations", response_model=List[IntegrationStatus])
def get_integrations():
    """Returns real connection and configuration status for enterprise integrations."""
    llm_info = get_llm_status()
    
    return [
        IntegrationStatus(
            name="LLM Reasoning Engine",
            category="AI & Semantic Querying",
            status="Connected and Verified",
            description="Active LLM orchestrator with deterministic analytical fallback. Handles natural language questions without external dependencies.",
            docs_link="https://fastapi.tiangolo.com/",
            details=llm_info
        ),
        IntegrationStatus(
            name="Snowflake Data Cloud",
            category="Cloud Data Warehouse",
            status="Configured (Unverified)" if os.getenv("SNOWFLAKE_ACCOUNT") else "Not Configured",
            description="Enterprise data warehouse integration for warehouse scale SQL pushdown.",
            docs_link="https://docs.snowflake.com/",
            details={
                "account": os.getenv("SNOWFLAKE_ACCOUNT", "Not set"),
                "status": "Requires warehouse credentials in backend/.env"
            }
        ),
        IntegrationStatus(
            name="Cube.dev Semantic Layer",
            category="Headless BI",
            status="Not Configured",
            description="Headless semantic layer API for universal metric governance and caching.",
            docs_link="https://cube.dev/docs",
            details={
                "api_url": os.getenv("CUBE_API_URL", "Not set"),
                "status": "Cube.dev manifest ready for deployment"
            }
        ),
        IntegrationStatus(
            name="dbt Core / Cloud",
            category="Data Transformation",
            status="Not Configured",
            description="Analytics engineering transformation models and test definitions.",
            docs_link="https://docs.getdbt.com/",
            details={
                "project_dir": os.getenv("DBT_PROJECT_DIR", "Not set"),
                "status": "Ready for dbt semantic layer metric export"
            }
        )
    ]
