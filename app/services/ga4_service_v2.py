"""
優化版 GA4 服務

使用連接池管理和具體異常處理
"""

from typing import Dict, Any, List, Optional, ClassVar
import structlog
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Metric,
    Dimension,
    Filter,
    FilterExpression
)
from google.api_core import exceptions as google_exceptions
import asyncio
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.logging import log_ga4_query
from app.core.exceptions import (
    GA4APIError,
    ValidationError,
    ConfigurationError,
    QuotaExceededError
)

logger = structlog.get_logger()


class OptimizedGA4Service:
    """優化的 GA4 服務類別"""
    
    # 類級別的客戶端實例（共享連接）
    _client: ClassVar[Optional[BetaAnalyticsDataClient]] = None
    _client_lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    
    def __init__(self):
        self.property_id = settings.GA4_PROPERTY_ID
        self.use_mock = settings.USE_MOCK_GA4_API
        
        # 查詢統計
        self.query_count = 0
        self.error_count = 0
        self.total_rows_fetched = 0
        
        # 初始化客戶端
        if not self.use_mock and not self._client:
            asyncio.create_task(self._init_client())
    
    @classmethod
    async def _init_client(cls):
        """初始化共享客戶端實例"""
        async with cls._client_lock:
            if cls._client is None:
                try:
                    cls._client = BetaAnalyticsDataClient()
                    logger.info("GA4 client initialized successfully")
                except Exception as e:
                    logger.error("Failed to initialize GA4 client", error=str(e))
                    raise ConfigurationError(
                        "Failed to initialize GA4 client",
                        details={"error": str(e)}
                    )
    
    async def execute_query(
        self, 
        query_params: Dict[str, Any], 
        property_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        執行 GA4 查詢（優化版）
        
        Args:
            query_params: 查詢參數
            property_id: GA4 屬性ID
            
        Returns:
            查詢結果
            
        Raises:
            ValidationError: 參數驗證失敗
            GA4APIError: GA4 API 錯誤
            QuotaExceededError: 配額超出
        """
        # 驗證參數
        self._validate_query_params(query_params)
        
        # 使用提供的屬性ID或默認屬性ID
        target_property_id = property_id or self.property_id
        
        if not target_property_id:
            raise ValidationError(
                "GA4 property ID is required",
                details={"provided_id": property_id, "default_id": self.property_id}
            )
        
        try:
            # 記錄查詢
            log_ga4_query(
                query=str(query_params),
                property_id=target_property_id
            )
            
            self.query_count += 1
            
            # 如果是模擬模式或客戶端未初始化
            if self.use_mock or self._client is None:
                return self._get_mock_data(query_params)
            
            # 構建 GA4 請求
            request = self._build_ga4_request(query_params, target_property_id)
            
            # 執行查詢（帶重試）
            response = await self._execute_with_retry(request)
            
            # 處理回應
            result = self._process_ga4_response(response, query_params)
            
            # 更新統計
            self.total_rows_fetched += len(result.get("rows", []))
            
            logger.info(
                "GA4 query executed successfully",
                property_id=target_property_id,
                row_count=len(result.get("rows", []))
            )
            
            return result
            
        except google_exceptions.InvalidArgument as e:
            self.error_count += 1
            raise ValidationError(
                "Invalid GA4 query parameters",
                details={"error": str(e), "query": query_params}
            )
            
        except google_exceptions.ResourceExhausted as e:
            self.error_count += 1
            raise QuotaExceededError(
                "GA4 API quota exceeded",
                details={"error": str(e), "property_id": target_property_id}
            )
            
        except google_exceptions.PermissionDenied as e:
            self.error_count += 1
            raise GA4APIError(
                "Permission denied for GA4 property",
                details={"error": str(e), "property_id": target_property_id}
            )
            
        except Exception as e:
            self.error_count += 1
            logger.error(
                "GA4 query failed",
                property_id=target_property_id,
                error=str(e)
            )
            raise GA4APIError(
                "Failed to execute GA4 query",
                details={"error": str(e), "query": query_params}
            )
    
    def _validate_query_params(self, query_params: Dict[str, Any]):
        """驗證查詢參數"""
        # 必需參數
        if not query_params.get("metrics"):
            raise ValidationError(
                "Metrics are required",
                details={"query_params": query_params}
            )
        
        if not query_params.get("date_ranges"):
            raise ValidationError(
                "Date ranges are required",
                details={"query_params": query_params}
            )
        
        # 驗證日期範圍
        for date_range in query_params["date_ranges"]:
            if "start_date" not in date_range or "end_date" not in date_range:
                raise ValidationError(
                    "Invalid date range format",
                    details={"date_range": date_range}
                )
        
        # 驗證指標
        for metric in query_params["metrics"]:
            if not isinstance(metric, dict) or "name" not in metric:
                raise ValidationError(
                    "Invalid metric format",
                    details={"metric": metric}
                )
    
    async def _execute_with_retry(
        self, 
        request: RunReportRequest, 
        max_retries: int = 3
    ):
        """執行查詢並自動重試"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # 指數退避
                    await asyncio.sleep(2 ** attempt)
                
                return self._client.run_report(request)
                
            except google_exceptions.DeadlineExceeded as e:
                last_error = e
                logger.warning(
                    "GA4 request timeout, retrying",
                    attempt=attempt + 1,
                    max_retries=max_retries
                )
                continue
                
            except google_exceptions.ServiceUnavailable as e:
                last_error = e
                logger.warning(
                    "GA4 service unavailable, retrying",
                    attempt=attempt + 1,
                    max_retries=max_retries
                )
                continue
                
            except Exception as e:
                # 不重試其他錯誤
                raise
        
        # 所有重試都失敗
        raise GA4APIError(
            "GA4 query failed after retries",
            details={"last_error": str(last_error), "retries": max_retries}
        )
    
    def _build_ga4_request(self, query_params: Dict[str, Any], property_id: str) -> RunReportRequest:
        """構建 GA4 API 請求（優化版）"""
        
        # 構建日期範圍
        date_ranges = []
        for date_range in query_params.get("date_ranges", []):
            date_ranges.append(
                DateRange(
                    start_date=date_range["start_date"],
                    end_date=date_range["end_date"]
                )
            )
        
        # 構建指標
        metrics = []
        for metric in query_params.get("metrics", []):
            metrics.append(Metric(name=metric["name"]))
        
        # 構建維度
        dimensions = []
        for dimension in query_params.get("dimensions", []):
            dimensions.append(Dimension(name=dimension["name"]))
        
        # 構建過濾器
        dimension_filter = None
        if "filters" in query_params:
            dimension_filter = self._build_filters(query_params["filters"])
        
        # 排序
        order_bys = []
        if "order_by" in query_params:
            order_bys = self._build_order_by(query_params["order_by"])
        
        return RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=date_ranges,
            metrics=metrics,
            dimensions=dimensions,
            dimension_filter=dimension_filter,
            order_bys=order_bys,
            limit=query_params.get("limit", 10),
            offset=query_params.get("offset", 0)
        )
    
    def _build_filters(self, filter_config: Dict[str, Any]) -> Optional[FilterExpression]:
        """構建過濾器表達式"""
        # TODO: 實現複雜的過濾器構建邏輯
        return None
    
    def _build_order_by(self, order_config: List[Dict[str, Any]]) -> List[Any]:
        """構建排序規則"""
        # TODO: 實現排序規則構建
        return []
    
    def _process_ga4_response(self, response: Any, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """處理 GA4 API 回應（優化版）"""
        
        rows = []
        
        # 處理每一行數據
        for row in response.rows:
            row_data = {}
            
            # 處理維度值
            for i, dimension_value in enumerate(row.dimension_values):
                dimension_name = query_params["dimensions"][i]["name"] if i < len(query_params.get("dimensions", [])) else f"dimension_{i}"
                row_data[dimension_name] = dimension_value.value
            
            # 處理指標值
            for i, metric_value in enumerate(row.metric_values):
                metric_name = query_params["metrics"][i]["name"] if i < len(query_params["metrics"]) else f"metric_{i}"
                row_data[metric_name] = self._parse_metric_value(metric_value)
            
            rows.append(row_data)
        
        # 處理總計
        totals = []
        if hasattr(response, 'totals') and response.totals:
            for total_row in response.totals:
                total_data = {}
                for i, metric_value in enumerate(total_row.metric_values):
                    metric_name = query_params["metrics"][i]["name"] if i < len(query_params["metrics"]) else f"metric_{i}"
                    total_data[metric_name] = self._parse_metric_value(metric_value)
                totals.append(total_data)
        
        # 元數據
        metadata = {
            "row_count": response.row_count if hasattr(response, 'row_count') else len(rows),
            "property_id": response.property if hasattr(response, 'property') else None,
            "query_time": datetime.now().isoformat()
        }
        
        return {
            "rows": rows,
            "totals": totals,
            "metadata": metadata,
            "row_count": len(rows)
        }
    
    def _parse_metric_value(self, metric_value) -> Any:
        """解析指標值"""
        if hasattr(metric_value, 'value'):
            try:
                # 嘗試轉換為數字
                if '.' in metric_value.value:
                    return float(metric_value.value)
                else:
                    return int(metric_value.value)
            except ValueError:
                return metric_value.value
        return metric_value
    
    def _get_mock_data(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """獲取模擬數據（優化版）"""
        
        # 根據查詢類型生成不同的模擬數據
        mock_data_templates = {
            "sessions": lambda: {"sessions": 1234, "date": "2024-01-21"},
            "users": lambda: {"users": 890, "date": "2024-01-21"},
            "pageviews": lambda: {"pageviews": 5678, "date": "2024-01-21"},
            "conversions": lambda: {"conversions": 45, "conversionRate": 0.035}
        }
        
        rows = []
        
        # 根據請求的指標生成數據
        for i in range(min(10, query_params.get("limit", 10))):
            row_data = {"index": i}
            
            # 添加維度數據
            for dimension in query_params.get("dimensions", []):
                if dimension["name"] == "date":
                    row_data["date"] = f"2024-01-{21-i:02d}"
                elif dimension["name"] == "pagePath":
                    row_data["pagePath"] = f"/page-{i+1}"
                else:
                    row_data[dimension["name"]] = f"value-{i+1}"
            
            # 添加指標數據
            for metric in query_params.get("metrics", []):
                metric_name = metric["name"]
                if metric_name in mock_data_templates:
                    row_data.update(mock_data_templates[metric_name]())
                else:
                    row_data[metric_name] = 100 + i * 10
            
            rows.append(row_data)
        
        return {
            "rows": rows,
            "totals": [{"sessions": 12340, "users": 8900}],
            "metadata": {
                "row_count": len(rows),
                "is_mock": True
            },
            "row_count": len(rows)
        }
    
    async def get_available_metrics(self) -> List[Dict[str, str]]:
        """獲取可用的指標列表"""
        return [
            {"name": "sessions", "description": "會話數"},
            {"name": "users", "description": "用戶數"},
            {"name": "newUsers", "description": "新用戶數"},
            {"name": "pageviews", "description": "瀏覽量"},
            {"name": "bounceRate", "description": "跳出率"},
            {"name": "averageSessionDuration", "description": "平均會話時長"}
        ]
    
    async def get_available_dimensions(self) -> List[Dict[str, str]]:
        """獲取可用的維度列表"""
        return [
            {"name": "date", "description": "日期"},
            {"name": "pagePath", "description": "頁面路徑"},
            {"name": "sessionSource", "description": "會話來源"},
            {"name": "deviceCategory", "description": "設備類別"},
            {"name": "country", "description": "國家/地區"},
            {"name": "city", "description": "城市"}
        ]
    
    async def get_stats(self) -> Dict[str, Any]:
        """獲取服務統計信息"""
        return {
            "query_count": self.query_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.query_count if self.query_count > 0 else 0,
            "total_rows_fetched": self.total_rows_fetched,
            "is_mock_mode": self.use_mock,
            "client_initialized": self._client is not None
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        try:
            if self.use_mock:
                return {
                    "status": "healthy",
                    "mode": "mock",
                    "message": "Mock mode active"
                }
            
            # 檢查客戶端狀態
            if self._client is None:
                return {
                    "status": "unhealthy",
                    "mode": "production",
                    "message": "GA4 client not initialized"
                }
            
            # 可以執行一個簡單的查詢來測試連接
            # 但這可能會消耗配額，所以只檢查客戶端狀態
            
            return {
                "status": "healthy",
                "mode": "production",
                "property_id": self.property_id,
                "query_stats": await self.get_stats()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# 創建單例實例
ga4_service = OptimizedGA4Service()