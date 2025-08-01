"""
GA4 服務

負責與 Google Analytics 4 API 交互，執行數據查詢
"""

from typing import Dict, Any, List, Optional
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

from app.core.config import settings
from app.core.logging import log_ga4_query

logger = structlog.get_logger()


class GA4Service:
    """GA4 服務類別"""
    
    def __init__(self):
        self.client = None
        self.property_id = settings.GA4_PROPERTY_ID
        
        # 初始化 GA4 客戶端
        if not settings.USE_MOCK_GA4_API:
            try:
                self.client = BetaAnalyticsDataClient()
                logger.info("GA4 client initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize GA4 client", error=str(e))
                # 如果初始化失敗，設置為模擬模式
                self.client = None
    
    async def execute_query(
        self, 
        query_params: Dict[str, Any], 
        property_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        執行 GA4 查詢
        
        Args:
            query_params: 查詢參數
            property_id: GA4 屬性ID
            
        Returns:
            查詢結果
        """
        try:
            # 使用提供的屬性ID或默認屬性ID
            target_property_id = property_id or self.property_id
            
            if not target_property_id:
                raise ValueError("GA4 property ID is required")
            
            # 記錄查詢
            log_ga4_query(
                query=str(query_params),
                property_id=target_property_id
            )
            
            # 如果是模擬模式或客戶端未初始化，返回模擬數據
            if settings.USE_MOCK_GA4_API or self.client is None:
                return self._get_mock_data(query_params)
            
            # 構建 GA4 請求
            request = self._build_ga4_request(query_params, target_property_id)
            
            # 執行查詢
            response = self.client.run_report(request)
            
            # 處理回應
            result = self._process_ga4_response(response, query_params)
            
            logger.info(
                "GA4 query executed successfully",
                property_id=target_property_id,
                row_count=len(result.get("rows", []))
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "GA4 query failed",
                property_id=property_id or self.property_id,
                error=str(e)
            )
            
            # 返回錯誤信息
            return {
                "error": True,
                "message": f"Failed to execute GA4 query: {str(e)}",
                "rows": [],
                "totals": [],
                "row_count": 0
            }
    
    def _build_ga4_request(self, query_params: Dict[str, Any], property_id: str) -> RunReportRequest:
        """構建 GA4 API 請求"""
        
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
        filters = None
        if "filters" in query_params:
            filters = self._build_filters(query_params["filters"])
        
        return RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=date_ranges,
            metrics=metrics,
            dimensions=dimensions,
            dimension_filter=filters,
            limit=query_params.get("limit", 10)
        )
    
    def _build_filters(self, filter_config: Dict[str, Any]) -> FilterExpression:
        """構建過濾器表達式"""
        # TODO: 實現複雜的過濾器構建邏輯
        return None
    
    def _process_ga4_response(self, response: Any, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """處理 GA4 API 回應"""
        
        result = {
            "rows": [],
            "totals": [],
            "row_count": 0,
            "query_info": query_params
        }
        
        # 處理行數據
        for row in response.rows:
            row_data = {
                "dimension_values": [dim.value for dim in row.dimension_values],
                "metric_values": [metric.value for metric in row.metric_values]
            }
            result["rows"].append(row_data)
        
        # 處理總計數據
        if response.totals:
            for total in response.totals:
                total_data = {
                    "metric_values": [metric.value for metric in total.metric_values]
                }
                result["totals"].append(total_data)
        
        result["row_count"] = len(result["rows"])
        
        return result
    
    def _get_mock_data(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """獲取模擬數據（用於開發和測試）"""
        
        # 根據查詢的維度和指標推斷意圖
        intent = "basic_metrics"  # 默認
        
        dimensions = query_params.get("dimensions", [])
        metrics = query_params.get("metrics", [])
        
        if dimensions:
            dim_names = [d.get("name", "") for d in dimensions]
            if "pageTitle" in dim_names:
                intent = "page_analysis"
            elif "sessionDefaultChannelGrouping" in dim_names:
                intent = "traffic_sources"
            elif "date" in dim_names:
                intent = "trend_analysis"
        
        if intent == "basic_metrics":
            return {
                "rows": [
                    {
                        "dimension_values": [],
                        "metric_values": ["1250", "2100", "4500", "45"]
                    }
                ],
                "totals": [
                    {
                        "metric_values": ["1250", "2100", "4500", "45"]
                    }
                ],
                "row_count": 1,
                "query_info": query_params,
                "mock_data": True
            }
        
        elif intent == "page_analysis":
            return {
                "rows": [
                    {
                        "dimension_values": ["首頁"],
                        "metric_values": ["1200", "800", "0.35"]
                    },
                    {
                        "dimension_values": ["產品頁面"],
                        "metric_values": ["800", "600", "0.25"]
                    },
                    {
                        "dimension_values": ["關於我們"],
                        "metric_values": ["300", "200", "0.67"]
                    }
                ],
                "totals": [
                    {
                        "metric_values": ["2300", "1600", "0.30"]
                    }
                ],
                "row_count": 3,
                "query_info": query_params,
                "mock_data": True
            }
        
        elif intent == "traffic_sources":
            return {
                "rows": [
                    {
                        "dimension_values": ["Organic Search"],
                        "metric_values": ["800", "600", "25"]
                    },
                    {
                        "dimension_values": ["Direct"],
                        "metric_values": ["500", "400", "15"]
                    },
                    {
                        "dimension_values": ["Social"],
                        "metric_values": ["300", "200", "10"]
                    }
                ],
                "totals": [
                    {
                        "metric_values": ["1600", "1200", "50"]
                    }
                ],
                "row_count": 3,
                "query_info": query_params,
                "mock_data": True
            }
        
        else:
            return {
                "rows": [
                    {
                        "dimension_values": [],
                        "metric_values": ["1000"]
                    }
                ],
                "totals": [
                    {
                        "metric_values": ["1000"]
                    }
                ],
                "row_count": 1,
                "query_info": query_params,
                "mock_data": True
            }
    
    async def get_properties(self) -> List[Dict[str, Any]]:
        """
        獲取可用的 GA4 屬性列表
        
        Returns:
            屬性列表
        """
        try:
            # TODO: 實現從 GA4 Admin API 獲取屬性列表
            return [
                {
                    "id": "123456789",
                    "name": "Example Website",
                    "account_id": "987654321",
                    "account_name": "Example Account"
                }
            ]
        except Exception as e:
            logger.error("Failed to get GA4 properties", error=str(e))
            return []
    
    async def validate_property(self, property_id: str) -> bool:
        """
        驗證 GA4 屬性ID是否有效
        
        Args:
            property_id: GA4 屬性ID
            
        Returns:
            是否有效
        """
        try:
            # 執行一個簡單的查詢來驗證屬性ID
            test_query = {
                "date_ranges": [{"start_date": "today", "end_date": "today"}],
                "metrics": [{"name": "totalUsers"}],
                "dimensions": [],
                "limit": 1
            }
            
            result = await self.execute_query(test_query, property_id)
            return not result.get("error", False)
            
        except Exception as e:
            logger.error("Property validation failed", property_id=property_id, error=str(e))
            return False
    
    async def get_available_metrics(self) -> Dict[str, List[str]]:
        """
        獲取可用的 GA4 指標列表
        
        Returns:
            指標分類列表
        """
        return {
            "user_metrics": [
                "totalUsers",
                "newUsers",
                "activeUsers",
                "sessionsPerUser"
            ],
            "session_metrics": [
                "sessions",
                "engagedSessions",
                "bounceRate",
                "sessionDuration"
            ],
            "traffic_metrics": [
                "screenPageViews",
                "pageViews",
                "screenPageViewsPerSession"
            ],
            "conversion_metrics": [
                "conversions",
                "conversionRate",
                "totalRevenue",
                "averageSessionDuration"
            ]
        }
    
    async def get_available_dimensions(self) -> Dict[str, List[str]]:
        """
        獲取可用的 GA4 維度列表
        
        Returns:
            維度分類列表
        """
        return {
            "user_dimensions": [
                "userType",
                "userId",
                "userPseudoId"
            ],
            "session_dimensions": [
                "sessionDefaultChannelGrouping",
                "sessionSource",
                "sessionMedium",
                "sessionCampaignName"
            ],
            "page_dimensions": [
                "pageTitle",
                "pagePath",
                "pageLocation",
                "pageReferrer"
            ],
            "event_dimensions": [
                "eventName",
                "eventCategory",
                "eventAction",
                "eventLabel"
            ]
        } 