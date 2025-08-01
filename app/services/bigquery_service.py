"""
BigQuery 服務

負責與 Google BigQuery 交互，執行大數據查詢
"""

from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.logging import log_bigquery_query

# 嘗試導入 BigQuery，如果失敗則使用模擬模式
try:
    from google.cloud import bigquery
    from google.cloud.exceptions import NotFound
    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False
    bigquery = None
    NotFound = Exception

logger = structlog.get_logger()


class BigQueryService:
    """BigQuery 服務類別"""
    
    def __init__(self):
        self.client = None
        self.project_id = settings.GCP_PROJECT_ID
        self.dataset_id = settings.BIGQUERY_DATASET_ID
        self.table_prefix = settings.BIGQUERY_TABLE_PREFIX
        
        # 初始化 BigQuery 客戶端
        if BIGQUERY_AVAILABLE and settings.ENABLE_BIGQUERY_ROUTING and settings.GCP_PROJECT_ID:
            try:
                self.client = bigquery.Client(project=self.project_id)
                logger.info("BigQuery client initialized successfully", project_id=self.project_id)
            except Exception as e:
                logger.error("Failed to initialize BigQuery client", error=str(e))
                self.client = None
        else:
            if not BIGQUERY_AVAILABLE:
                logger.warning("BigQuery dependencies not available, service disabled")
            self.client = None
    
    async def execute_query(
        self, 
        query_params: Dict[str, Any], 
        property_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        執行 BigQuery 查詢
        
        Args:
            query_params: 查詢參數
            property_id: GA4 屬性ID
            
        Returns:
            查詢結果
        """
        try:
            if not self.client:
                raise Exception("BigQuery client not initialized")
            
            # 記錄查詢
            log_bigquery_query(
                query=str(query_params),
                property_id=property_id or "default"
            )
            
            # 構建 SQL 查詢
            sql_query = self._build_sql_query(query_params, property_id)
            
            # 執行查詢
            logger.info("Executing BigQuery query", sql=sql_query[:200] + "...")
            query_job = self.client.query(sql_query)
            
            # 獲取結果
            results = query_job.result()
            
            # 處理結果
            processed_results = self._process_bigquery_results(results, query_params)
            
            logger.info(
                "BigQuery query executed successfully",
                property_id=property_id,
                row_count=len(processed_results.get("rows", []))
            )
            
            return processed_results
            
        except Exception as e:
            logger.error(
                "BigQuery query failed",
                property_id=property_id,
                error=str(e)
            )
            
            return {
                "error": True,
                "message": f"Failed to execute BigQuery query: {str(e)}",
                "rows": [],
                "totals": [],
                "row_count": 0
            }
    
    def _build_sql_query(self, query_params: Dict[str, Any], property_id: Optional[str]) -> str:
        """構建 BigQuery SQL 查詢"""
        
        # 基礎表名
        table_name = f"`{self.project_id}.{self.dataset_id}.events_*`"
        
        # 構建 SELECT 子句
        select_fields = []
        
        # 添加維度
        dimensions = query_params.get("dimensions", [])
        for dim in dimensions:
            dim_name = dim.get("name", "")
            if dim_name == "date":
                select_fields.append("PARSE_DATE('%Y%m%d', event_date) as date")
            elif dim_name == "pageTitle":
                select_fields.append("(SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_title') as pageTitle")
            elif dim_name == "sessionDefaultChannelGrouping":
                select_fields.append("traffic_source.medium as sessionDefaultChannelGrouping")
            else:
                select_fields.append(f"'{dim_name}' as {dim_name}")
        
        # 添加指標
        metrics = query_params.get("metrics", [])
        for metric in metrics:
            metric_name = metric.get("name", "")
            if metric_name == "totalUsers":
                select_fields.append("COUNT(DISTINCT user_pseudo_id) as totalUsers")
            elif metric_name == "sessions":
                select_fields.append("COUNT(DISTINCT CONCAT(user_pseudo_id, (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id'))) as sessions")
            elif metric_name == "screenPageViews":
                select_fields.append("COUNTIF(event_name = 'page_view') as screenPageViews")
            elif metric_name == "conversions":
                select_fields.append("COUNTIF(event_name IN ('purchase', 'conversion')) as conversions")
            elif metric_name == "totalRevenue":
                select_fields.append("SUM(ecommerce.purchase_revenue) as totalRevenue")
            else:
                select_fields.append(f"0 as {metric_name}")
        
        # 如果沒有選擇字段，添加默認字段
        if not select_fields:
            select_fields.append("COUNT(*) as total_events")
        
        # 構建 WHERE 子句
        where_conditions = []
        
        # 添加日期範圍
        date_ranges = query_params.get("date_ranges", [])
        if date_ranges:
            date_range = date_ranges[0]  # 使用第一個日期範圍
            start_date = self._convert_date_string(date_range.get("start_date", "30daysAgo"))
            end_date = self._convert_date_string(date_range.get("end_date", "today"))
            where_conditions.append(f"_TABLE_SUFFIX BETWEEN '{start_date.strftime('%Y%m%d')}' AND '{end_date.strftime('%Y%m%d')}'")
        
        # 添加屬性ID過濾（如果需要）
        if property_id and property_id != "demo_property":
            where_conditions.append(f"stream_id = '{property_id}'")
        
        # 構建完整查詢
        sql_query = f"""
        SELECT
            {', '.join(select_fields)}
        FROM {table_name}
        """
        
        if where_conditions:
            sql_query += f"\nWHERE {' AND '.join(where_conditions)}"
        
        # 添加 GROUP BY（如果有維度）
        if dimensions:
            group_by_fields = []
            for i, dim in enumerate(dimensions, 1):
                group_by_fields.append(str(i))
            sql_query += f"\nGROUP BY {', '.join(group_by_fields)}"
        
        # 添加 ORDER BY 和 LIMIT
        if dimensions:
            sql_query += f"\nORDER BY {len(dimensions) + 1} DESC"
        
        limit = query_params.get("limit", 10)
        sql_query += f"\nLIMIT {limit}"
        
        return sql_query
    
    def _convert_date_string(self, date_str: str) -> datetime:
        """轉換日期字符串為 datetime 對象"""
        
        if date_str == "today":
            return datetime.now()
        elif date_str == "yesterday":
            return datetime.now() - timedelta(days=1)
        elif date_str.endswith("daysAgo"):
            days = int(date_str.replace("daysAgo", ""))
            return datetime.now() - timedelta(days=days)
        else:
            # 嘗試解析 YYYY-MM-DD 格式
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return datetime.now()
    
    def _process_bigquery_results(self, results: Any, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """處理 BigQuery 查詢結果"""
        
        processed_results = {
            "rows": [],
            "totals": [],
            "row_count": 0,
            "query_info": query_params,
            "data_source": "bigquery"
        }
        
        # 轉換結果為標準格式
        rows = []
        for row in results:
            row_dict = dict(row)
            
            # 分離維度值和指標值
            dimensions = query_params.get("dimensions", [])
            metrics = query_params.get("metrics", [])
            
            dimension_values = []
            metric_values = []
            
            for dim in dimensions:
                dim_name = dim.get("name", "")
                value = row_dict.get(dim_name, "")
                dimension_values.append(str(value))
            
            for metric in metrics:
                metric_name = metric.get("name", "")
                value = row_dict.get(metric_name, 0)
                metric_values.append(str(value))
            
            # 如果沒有維度，所有值都是指標
            if not dimensions:
                metric_values = [str(v) for v in row_dict.values()]
            
            rows.append({
                "dimension_values": dimension_values,
                "metric_values": metric_values
            })
        
        processed_results["rows"] = rows
        processed_results["row_count"] = len(rows)
        
        # 計算總計（簡化版本）
        if rows:
            totals_row = {
                "metric_values": []
            }
            
            # 對每個指標計算總和
            num_metrics = len(rows[0]["metric_values"]) if rows else 0
            for i in range(num_metrics):
                total = sum(float(row["metric_values"][i]) for row in rows if row["metric_values"][i].replace('.', '').isdigit())
                totals_row["metric_values"].append(str(total))
            
            processed_results["totals"] = [totals_row]
        
        return processed_results
    
    async def validate_dataset(self) -> bool:
        """
        驗證 BigQuery 數據集是否存在
        
        Returns:
            是否存在
        """
        try:
            if not self.client:
                return False
            
            dataset_ref = bigquery.DatasetReference(self.project_id, self.dataset_id)
            self.client.get_dataset(dataset_ref)
            return True
            
        except NotFound:
            logger.warning("BigQuery dataset not found", dataset_id=self.dataset_id)
            return False
        except Exception as e:
            logger.error("Failed to validate BigQuery dataset", error=str(e))
            return False
    
    async def get_available_tables(self) -> List[str]:
        """
        獲取可用的 GA4 表列表
        
        Returns:
            表名列表
        """
        try:
            if not self.client:
                return []
            
            dataset_ref = bigquery.DatasetReference(self.project_id, self.dataset_id)
            tables = list(self.client.list_tables(dataset_ref))
            
            # 過濾 GA4 事件表
            ga4_tables = [
                table.table_id for table in tables 
                if table.table_id.startswith(self.table_prefix)
            ]
            
            return ga4_tables
            
        except Exception as e:
            logger.error("Failed to get available tables", error=str(e))
            return []
    
    def is_available(self) -> bool:
        """檢查 BigQuery 服務是否可用"""
        return BIGQUERY_AVAILABLE and self.client is not None and settings.ENABLE_BIGQUERY_ROUTING 