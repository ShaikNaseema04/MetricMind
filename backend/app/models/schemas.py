from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        description="Natural language business intelligence question",
        examples=["What is the total revenue and profit?"]
    )
    conversation_id: Optional[str] = Field(None, examples=["conv-1"])
    filters: Optional[Dict[str, Any]] = Field(default=None, examples=[{}])

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "What is the total revenue and profit?"
            }
        }
    }

class ChartMeta(BaseModel):
    chart_type: Literal["bar", "line", "donut", "horizontal_bar", "table", "kpi"]
    title: str
    x_key: Optional[str] = None
    y_keys: List[str] = Field(default_factory=list)
    series_names: Optional[List[str]] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None

class KpiItem(BaseModel):
    label: str
    value: Any
    formatted_value: str
    formattedValue: str = ""  # CamelCase alias for existing frontend compatibility
    change_pct: Optional[float] = None
    trend: Optional[str] = None
    description: Optional[str] = None

class SqlTrace(BaseModel):
    sql: str
    params: Dict[str, Any] = Field(default_factory=dict)
    metric_definitions: List[str] = Field(default_factory=list)
    execution_engine: str = "SQLite Analytical Engine"
    rows_returned: int = 0
    is_preview: bool = False

class ApiTrace(BaseModel):
    endpoint: str
    method: str = "POST"
    request_payload: Dict[str, Any] = Field(default_factory=dict)
    status_code: int = 200
    execution_time_ms: float = 0.0
    timestamp: str = ""
    sanitized: bool = True

class SecondaryBreakdown(BaseModel):
    dimension: str
    title: str
    data: List[Dict[str, Any]] = Field(default_factory=list)
    explanation: str

class ChatResponse(BaseModel):
    question: str
    explanation: str
    answer: str = ""  # Alias for existing frontend (e.g. obj.answer)
    response: str = ""  # Alias for existing frontend (e.g. obj.response)
    message: str = ""  # Alias for existing frontend (e.g. obj.message)
    data: List[Dict[str, Any]] = Field(default_factory=list)
    results: List[Dict[str, Any]] = Field(default_factory=list)  # Alias for existing frontend (e.g. obj.results)
    sql: str = ""  # Top-level alias for sql_trace.sql (e.g. obj.sql)
    generated_sql: str = ""  # Alias for existing frontend (e.g. obj.generated_sql)
    chart: Optional[Dict[str, Any]] = None  # Alias matching analyticsUtils.ts ChartMeta
    chart_meta: Optional[ChartMeta] = None
    kpi_items: Optional[List[KpiItem]] = None
    sql_trace: SqlTrace
    api_trace: ApiTrace
    secondary_breakdown: Optional[SecondaryBreakdown] = None
    query_plan: Optional[Dict[str, Any]] = None

class DatasetFileInfo(BaseModel):
    filename: str
    path: str
    row_count: int
    column_count: int
    columns: List[str]
    dtypes: Dict[str, str]
    missing_values: Dict[str, int]
    sample_records: List[Dict[str, Any]]

class DatasetOverview(BaseModel):
    source_directory: str
    is_source_accessible: bool
    total_files: int
    files: List[DatasetFileInfo]
    total_orders: int
    completed_orders: int
    completed_revenue: float
    completed_profit: float
    overall_margin_pct: float
    total_quantity: int
    date_range: Dict[str, str]
    countries: List[str]
    regions: List[str]
    products: List[str]
    categories: List[str]
    sales_channels: List[str]

class MetricDefinition(BaseModel):
    name: str
    display_name: str
    description: str
    formula: str
    aggregation: str
    required_columns: List[str]
    format: str

class DimensionDefinition(BaseModel):
    name: str
    display_name: str
    source_column: str
    data_type: str
    description: str

class SemanticRegistryResponse(BaseModel):
    metrics: List[MetricDefinition]
    dimensions: List[DimensionDefinition]
    governed_rules: List[str]

class AnalyticsQueryRequest(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    category: Optional[str] = None
    order_status: Optional[str] = "Completed"
    sales_channel: Optional[str] = None

class IntegrationStatus(BaseModel):
    name: str
    category: str
    status: Literal["Not Configured", "Configured (Unverified)", "Connected and Verified"]
    description: str
    docs_link: str
    details: Dict[str, Any] = Field(default_factory=dict)
