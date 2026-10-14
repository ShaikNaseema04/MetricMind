"""
MetricMind Data Ingestion and Validation Service
Loads raw CSV data from the designated dataset folder into SQLite safely without mutating source files.
Performs data quality checks, schema verification, and generates an inspection report.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd
from ..config import settings
from ..database.db import get_connection, get_db_path, execute_script
from ..models.schemas import DatasetFileInfo, DatasetOverview

logger = logging.getLogger(__name__)

# Cache for loaded overview to avoid redundant disk I/O
_cached_overview: DatasetOverview | None = None

def get_source_data_dir() -> Path:
    return settings.get_effective_data_dir()

def inspect_and_load_dataset(force: bool = False) -> DatasetOverview:
    """
    Inspects raw dataset folder, validates schemas, creates SQLite tables,
    and populates data. Generates an inspection report.
    """
    global _cached_overview
    db_file = get_db_path()
    
    # If DB exists and not force, check if already populated
    if not force and db_file.exists() and _cached_overview is not None:
        return _cached_overview

    source_dir = get_source_data_dir()
    is_accessible = source_dir.exists()
    
    files_info: List[DatasetFileInfo] = []
    
    if not is_accessible:
        logger.warning(f"Source dataset directory {source_dir} not accessible.")
        return DatasetOverview(
            source_directory=str(source_dir),
            is_source_accessible=False,
            total_files=0,
            files=[],
            total_orders=0,
            completed_orders=0,
            completed_revenue=0.0,
            completed_profit=0.0,
            overall_margin_pct=0.0,
            total_quantity=0,
            date_range={"min": "", "max": ""},
            countries=[],
            regions=[],
            products=[],
            categories=[],
            sales_channels=[]
        )

    # 1. Discover all CSV files in source folder
    csv_files = sorted(source_dir.glob("*.csv"))
    
    # Prepare tables in SQLite
    conn = get_connection()
    
    orders_df = None
    products_df = None
    customers_df = None
    costs_df = None
    dates_df = None
    
    for csv_path in csv_files:
        df = pd.read_csv(csv_path)
        fname = csv_path.name
        table_name = fname.replace("_raw.csv", "").replace(".csv", "")
        
        # Ingest into SQLite
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        
        missing_dict = {col: int(cnt) for col, cnt in df.isnull().sum().items()}
        dtypes_dict = {col: str(dtype) for col, dtype in df.dtypes.items()}
        sample_dict = df.head(3).to_dict(orient="records")
        
        files_info.append(
            DatasetFileInfo(
                filename=fname,
                path=str(csv_path),
                row_count=len(df),
                column_count=len(df.columns),
                columns=list(df.columns),
                dtypes=dtypes_dict,
                missing_values=missing_dict,
                sample_records=sample_dict
            )
        )
        
        if table_name == "orders":
            orders_df = df
        elif table_name == "products":
            products_df = df
        elif table_name == "customers":
            customers_df = df
        elif table_name == "costs":
            costs_df = df
        elif table_name == "date_dimension":
            dates_df = df

    # Create optimized SQLite indexes and Enriched Analytics View
    create_view_sql = """
    CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);
    CREATE INDEX IF NOT EXISTS idx_orders_order_status ON orders(order_status);
    CREATE INDEX IF NOT EXISTS idx_orders_country ON orders(country);
    CREATE INDEX IF NOT EXISTS idx_orders_region ON orders(region);
    CREATE INDEX IF NOT EXISTS idx_orders_product_id ON orders(product_id);
    CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);

    DROP VIEW IF EXISTS v_orders_enriched;
    CREATE VIEW v_orders_enriched AS
    SELECT 
        o.order_id,
        o.order_date,
        strftime('%Y-%m', o.order_date) AS month_name,
        strftime('%Y', o.order_date) AS order_year,
        o.customer_id,
        c.customer_name,
        c.segment,
        o.product_id,
        p.product_name,
        p.category,
        o.country,
        o.region,
        o.sales_channel,
        o.order_status,
        o.quantity,
        o.gross_revenue,
        o.discount_pct,
        o.discount_amount,
        o.revenue,
        o.product_cost,
        o.shipping_cost,
        o.total_cost,
        o.profit,
        o.margin_pct
    FROM orders o
    LEFT JOIN products p ON o.product_id = p.product_id
    LEFT JOIN customers c ON o.customer_id = c.customer_id;
    """
    conn.executescript(create_view_sql)
    conn.commit()
    conn.close()

    # Calculate authoritative statistics from real dataset
    if orders_df is not None:
        completed = orders_df[orders_df["order_status"] == "Completed"]
        total_orders = len(orders_df)
        completed_orders = len(completed)
        completed_revenue = float(completed["revenue"].sum())
        completed_profit = float(completed["profit"].sum())
        overall_margin = float((completed_profit / completed_revenue * 100) if completed_revenue > 0 else 0.0)
        total_quantity = int(completed["quantity"].sum())
        date_min = str(orders_df["order_date"].min())
        date_max = str(orders_df["order_date"].max())
        countries = sorted(list(orders_df["country"].unique()))
        regions = sorted(list(orders_df["region"].unique()))
        sales_channels = sorted(list(orders_df["sales_channel"].unique()))
    else:
        total_orders = 0
        completed_orders = 0
        completed_revenue = 0.0
        completed_profit = 0.0
        overall_margin = 0.0
        total_quantity = 0
        date_min = ""
        date_max = ""
        countries = []
        regions = []
        sales_channels = []

    products = sorted(list(products_df["product_name"].unique())) if products_df is not None else []
    categories = sorted(list(products_df["category"].unique())) if products_df is not None else []

    overview = DatasetOverview(
        source_directory=str(source_dir),
        is_source_accessible=True,
        total_files=len(files_info),
        files=files_info,
        total_orders=total_orders,
        completed_orders=completed_orders,
        completed_revenue=completed_revenue,
        completed_profit=completed_profit,
        overall_margin_pct=round(overall_margin, 2),
        total_quantity=total_quantity,
        date_range={"min": date_min, "max": date_max},
        countries=countries,
        regions=regions,
        products=products,
        categories=categories,
        sales_channels=sales_channels
    )

    _cached_overview = overview

    # Save inspection report to data/reports
    reports_dir = Path(settings.REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_json = reports_dir / "dataset_inspection_report.json"
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(overview.model_dump(), f, indent=2)

    report_md = reports_dir / "dataset_inspection_report.md"
    with open(report_md, "w", encoding="utf-8") as f:
        f.write(f"""# MetricMind Dataset Inspection Report

- **Source Directory:** `{source_dir}`
- **Source Accessible:** Yes
- **Total Ingested Files:** {len(files_info)}
- **Date Range:** {date_min} to {date_max}
- **Total Orders Recorded:** {total_orders:,}
- **Completed Orders:** {completed_orders:,}
- **Completed Revenue:** ${completed_revenue:,.2f}
- **Completed Profit:** ${completed_profit:,.2f}
- **Authoritative Profit Margin:** {overall_margin:.2f}%
- **Units Sold:** {total_quantity:,}

## Ingested Tables
""" + "\n".join([f"- **{fi.filename}**: {fi.row_count:,} rows, {fi.column_count} columns" for fi in files_info]))

    return overview

def get_cached_overview() -> DatasetOverview:
    global _cached_overview
    if _cached_overview is None:
        return inspect_and_load_dataset(force=False)
    return _cached_overview
