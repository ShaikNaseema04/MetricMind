export type Row = Record<string, unknown>;

export type ChartType = "bar" | "grouped_bar" | "line" | "pie" | "kpi" | "none";

export interface ChartMeta {
  type: ChartType;
  xKey?: string;
  yKeys?: string[];
  title?: string;
}

export interface KpiItem {
  label: string;
  value: unknown;
  formattedValue: string;
  subtext?: string;
}

export interface NormalizedApiResponse {
  answer: string;
  data: Row[];
  sql?: string;
  chart?: ChartMeta;
  raw: unknown;
}

/**
 * Format a column label into readable title case
 * e.g., "total_revenue" -> "Total Revenue"
 */
export function formatColumnLabel(key: string): string {
  if (!key) return "";
  return key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

/**
 * Checks if a key name suggests monetary values
 */
function isCurrencyKey(key: string): boolean {
  const lower = key.toLowerCase();
  return (
    lower.includes("revenue") ||
    lower.includes("profit") ||
    lower.includes("cost") ||
    lower.includes("sales") ||
    lower.includes("price") ||
    lower.includes("amount") ||
    lower.includes("spend") ||
    lower.includes("budget") ||
    lower.includes("gmv")
  );
}

/**
 * Checks if a key name suggests percentage values
 */
function isPercentKey(key: string): boolean {
  const lower = key.toLowerCase();
  return (
    lower.includes("margin") ||
    lower.includes("percent") ||
    lower.includes("pct") ||
    lower.includes("rate") ||
    lower.includes("ratio") ||
    lower.includes("growth") ||
    lower.includes("share")
  );
}

/**
 * Format numeric values intelligently according to column context
 */
export function formatMetricValue(value: unknown, keyName = ""): string {
  if (value === null || value === undefined) return "—";

  // If already string formatted with currency or percentage
  if (typeof value === "string") {
    const num = Number(value.replace(/[^0-9.-]+/g, ""));
    if (!Number.isNaN(num) && value.length < 25 && /^[0-9.,-]+$/.test(value.trim())) {
      return formatNumericNumber(num, keyName);
    }
    return value;
  }

  if (typeof value === "number") {
    return formatNumericNumber(value, keyName);
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function formatNumericNumber(num: number, keyName: string): string {
  if (Number.isNaN(num)) return "—";

  const isPercent = isPercentKey(keyName);
  const isCurrency = isCurrencyKey(keyName);

  if (isPercent) {
    // If it's a small decimal (e.g. 0.185), multiply by 100
    const displayVal = Math.abs(num) <= 1 && num !== 0 ? num * 100 : num;
    return `${displayVal.toLocaleString("en-US", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 2,
    })}%`;
  }

  if (isCurrency) {
    return `$${num.toLocaleString("en-US", {
      minimumFractionDigits: Number.isInteger(num) ? 0 : 2,
      maximumFractionDigits: 2,
    })}`;
  }

  // Standard numbers
  if (Number.isInteger(num)) {
    return num.toLocaleString("en-US");
  }

  return num.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

/**
 * Checks if key represents a date or time dimension
 */
export function isDateKey(key: string): boolean {
  const lower = key.toLowerCase();
  return (
    lower.includes("date") ||
    lower.includes("month") ||
    lower.includes("year") ||
    lower.includes("quarter") ||
    lower.includes("day") ||
    lower.includes("period") ||
    lower.includes("time") ||
    lower === "dt" ||
    lower === "timestamp"
  );
}

/**
 * Identify numeric keys in dataset
 */
export function getNumericKeys(data: Row[]): string[] {
  if (!data || data.length === 0) return [];
  const first = data[0];
  const keys = Object.keys(first);

  return keys.filter((key) => {
    // Exclude IDs or primary keys if they look like row identifiers
    const lower = key.toLowerCase();
    if (lower === "id" || lower.endsWith("_id")) return false;

    // Check if values in first few rows are numeric
    return data.slice(0, 5).some((row) => {
      const val = row[key];
      return typeof val === "number" || (!Number.isNaN(Number(val)) && typeof val === "string" && val.trim() !== "");
    });
  });
}

/**
 * Identify category/label keys in dataset
 */
export function getCategoryKeys(data: Row[]): string[] {
  if (!data || data.length === 0) return [];
  const first = data[0];
  const keys = Object.keys(first);

  return keys.filter((key) => {
    const val = first[key];
    return typeof val === "string" || typeof val === "boolean";
  });
}

/**
 * Extract KPI items for single-row or aggregate responses
 */
export function extractKpis(data: Row[]): KpiItem[] {
  if (!data || data.length !== 1) return [];
  const row = data[0];
  const keys = Object.keys(row);
  const items: KpiItem[] = [];

  for (const key of keys) {
    const val = row[key];
    const isNum = typeof val === "number" || (!Number.isNaN(Number(val)) && typeof val === "string" && val.trim() !== "");
    if (isNum) {
      items.push({
        label: formatColumnLabel(key),
        value: val,
        formattedValue: formatMetricValue(val, key),
      });
    }
  }

  return items;
}

/**
 * Infer visualization configuration from question and actual data
 */
export function inferVisualization(
  question: string,
  data: Row[],
  explicitChart?: ChartMeta
): ChartMeta | null {
  if (!data || data.length === 0) return null;

  // If backend provided explicit chart metadata and it has valid fields
  if (explicitChart && explicitChart.type && explicitChart.type !== "none") {
    const validX = explicitChart.xKey && Object.prototype.hasOwnProperty.call(data[0], explicitChart.xKey)
      ? explicitChart.xKey
      : undefined;
    const validY = explicitChart.yKeys?.filter((k) => Object.prototype.hasOwnProperty.call(data[0], k));

    return {
      type: explicitChart.type,
      xKey: validX,
      yKeys: validY && validY.length > 0 ? validY : undefined,
      title: explicitChart.title || formatChartTitle(question, explicitChart.type),
    };
  }

  // Single row with 1 to 3 numeric values -> KPI Card
  const kpis = extractKpis(data);
  if (data.length === 1 && kpis.length > 0 && kpis.length <= 4) {
    return {
      type: "kpi",
      title: question.trim() ? question : "Key Metric",
    };
  }

  // Must have at least 2 rows for charting
  if (data.length < 2) return null;

  const numericKeys = getNumericKeys(data);
  const categoryKeys = getCategoryKeys(data);
  const q = question.toLowerCase();

  if (numericKeys.length === 0) return null;

  // Determine xKey (prefer date/time keys, then first string key, then first non-numeric key)
  let xKey: string | undefined = categoryKeys.find((k) => isDateKey(k));
  if (!xKey) {
    xKey = categoryKeys[0];
  }
  if (!xKey) {
    // If no category key, find any key that is not in numericKeys
    const allKeys = Object.keys(data[0]);
    xKey = allKeys.find((k) => !numericKeys.includes(k)) || allKeys[0];
  }

  const isTimeDimension = xKey ? isDateKey(xKey) : false;
  const asksTimeTrend = q.includes("over time") || q.includes("trend") || q.includes("monthly") || q.includes("by month") || q.includes("daily") || q.includes("yearly") || q.includes("timeline");

  // 1. Time Series Line Chart
  if ((isTimeDimension || asksTimeTrend) && numericKeys.length > 0) {
    return {
      type: "line",
      xKey,
      yKeys: numericKeys.slice(0, 3), // max 3 lines for clarity
      title: formatChartTitle(question, "line"),
    };
  }

  // 2. Comparison / Grouped Bar Chart (multiple metrics like revenue & profit)
  const isComparison = q.includes("compare") || q.includes("versus") || q.includes(" vs ") || (numericKeys.length >= 2 && (q.includes("revenue and profit") || q.includes("profit and revenue")));
  if (isComparison && numericKeys.length >= 2) {
    return {
      type: "grouped_bar",
      xKey,
      yKeys: numericKeys.slice(0, 4),
      title: formatChartTitle(question, "grouped_bar"),
    };
  }

  // 3. Pie / Donut Chart (contribution/breakdown/share and <= 7 items)
  const asksDistribution = q.includes("share") || q.includes("contribution") || q.includes("split") || q.includes("distribution") || q.includes("percentage") || q.includes("proportion");
  if (asksDistribution && data.length >= 2 && data.length <= 7 && numericKeys.length === 1) {
    return {
      type: "pie",
      xKey,
      yKeys: [numericKeys[0]],
      title: formatChartTitle(question, "pie"),
    };
  }

  // 4. Bar Chart (default for categorical aggregation like top products, country, region)
  return {
    type: "bar",
    xKey,
    yKeys: [numericKeys[0]],
    title: formatChartTitle(question, "bar"),
  };
}

function formatChartTitle(question: string, type: ChartType): string {
  if (question && question.trim().length > 3) {
    // Clean up question mark if present
    const clean = question.trim().replace(/\?+$/, "");
    return clean.charAt(0).toUpperCase() + clean.slice(1);
  }

  switch (type) {
    case "line":
      return "Trend Analysis";
    case "grouped_bar":
      return "Metric Comparison";
    case "pie":
      return "Contribution Breakdown";
    case "bar":
    default:
      return "Data Visualization";
  }
}
