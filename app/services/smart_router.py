"""
智能路由器服務

負責在 GA4 API 和 BigQuery 之間智能選擇最佳數據源
"""

from typing import Dict, Any, Optional, Tuple
import structlog
from datetime import datetime, timedelta
from enum import Enum

from app.core.config import settings
from app.services.ga4_service import GA4Service
from app.services.bigquery_service import BigQueryService
from app.services.cache_service import CacheService
from app.services.trend_analysis import TrendAnalysisService

logger = structlog.get_logger()


class DataSource(Enum):
    """數據源枚舉"""
    GA4_API = "ga4_api"
    BIGQUERY = "bigquery"
    MOCK = "mock"


class QueryComplexity(Enum):
    """查詢複雜度枚舉"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class SmartRouter:
    """智能路由器類別"""
    
    def __init__(self):
        self.ga4_service = GA4Service()
        self.bigquery_service = BigQueryService()
        self.cache_service = CacheService()
        self.trend_analysis = TrendAnalysisService()
        
        # 路由決策權重
        self.routing_weights = {
            "data_volume": 0.3,      # 數據量大小
            "query_complexity": 0.25, # 查詢複雜度
            "date_range": 0.2,       # 日期範圍
            "performance": 0.15,     # 性能考量
            "availability": 0.1      # 服務可用性
        }
    
    async def execute_query(
        self, 
        query_params: Dict[str, Any], 
        property_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        智能執行查詢
        
        Args:
            query_params: 查詢參數
            property_id: GA4 屬性ID
            
        Returns:
            查詢結果，包含數據源信息
        """
        try:
            # 1. 檢查快取
            query_with_property = {**query_params, "property_id": property_id}
            cached_result = await self.cache_service.get_cached_query_result(query_with_property)
            
            if cached_result:
                logger.info("Query served from cache", property_id=property_id)
                return cached_result
            
            # 2. 分析查詢並選擇最佳數據源
            selected_source, reasoning = await self._select_data_source(query_params, property_id)
            
            logger.info(
                "Smart router selected data source",
                source=selected_source.value,
                reasoning=reasoning,
                query_type=self._get_query_type(query_params)
            )
            
            # 3. 根據選擇的數據源執行查詢
            if selected_source == DataSource.BIGQUERY:
                result = await self.bigquery_service.execute_query(query_params, property_id)
                result["data_source"] = "bigquery"
                result["routing_reasoning"] = reasoning
            
            elif selected_source == DataSource.GA4_API:
                result = await self.ga4_service.execute_query(query_params, property_id)
                result["data_source"] = "ga4_api"
                result["routing_reasoning"] = reasoning
            
            else:  # MOCK
                result = await self.ga4_service.execute_query(query_params, property_id)
                result["data_source"] = "mock"
                result["routing_reasoning"] = reasoning
            
            # 4. 如果主要數據源失敗，嘗試備用數據源
            if result.get("error", False):
                backup_result = await self._try_backup_source(
                    query_params, property_id, selected_source
                )
                if backup_result and not backup_result.get("error", False):
                    backup_result["routing_reasoning"] = f"{reasoning} (fallback from {selected_source.value})"
                    result = backup_result
            
            # 5. 執行趨勢分析（如果適用）
            if not result.get("error", False) and self._should_perform_trend_analysis(query_params, result):
                try:
                    metric_name = query_params.get("metrics", ["sessions"])[0]
                    trend_analysis_result = await self.trend_analysis.analyze_trend(
                        result.get("rows", []), 
                        metric_name
                    )
                    result["trend_analysis"] = trend_analysis_result
                    logger.info("Trend analysis completed", property_id=property_id)
                except Exception as e:
                    logger.error("Trend analysis failed", error=str(e))
            
            # 6. 快取結果
            if not result.get("error", False):
                cache_ttl = self._determine_cache_ttl(query_params)
                await self.cache_service.cache_query_result(
                    query_with_property, 
                    result, 
                    cache_ttl
                )
            
            return result
            
        except Exception as e:
            logger.error("Smart router execution failed", error=str(e))
            
            # 降級到 GA4 API 或模擬數據
            try:
                result = await self.ga4_service.execute_query(query_params, property_id)
                result["data_source"] = "ga4_api_fallback"
                result["routing_reasoning"] = f"Emergency fallback due to router error: {str(e)}"
                return result
            except Exception as fallback_error:
                logger.error("Fallback also failed", error=str(fallback_error))
                return {
                    "error": True,
                    "message": f"All data sources failed: {str(e)}",
                    "rows": [],
                    "totals": [],
                    "row_count": 0,
                    "data_source": "error",
                    "routing_reasoning": "All sources failed"
                }
    
    async def _select_data_source(
        self, 
        query_params: Dict[str, Any], 
        property_id: Optional[str]
    ) -> Tuple[DataSource, str]:
        """
        選擇最佳數據源
        
        Args:
            query_params: 查詢參數
            property_id: GA4 屬性ID
            
        Returns:
            選擇的數據源和原因
        """
        
        # 如果禁用了 BigQuery 路由，直接使用 GA4 API
        if not settings.ENABLE_BIGQUERY_ROUTING:
            return DataSource.GA4_API, "BigQuery routing disabled in settings"
        
        # 如果 BigQuery 服務不可用，使用 GA4 API
        if not self.bigquery_service.is_available():
            return DataSource.GA4_API, "BigQuery service not available"
        
        # 如果是模擬模式，使用模擬數據
        if settings.USE_MOCK_GA4_API:
            return DataSource.MOCK, "Mock mode enabled"
        
        # 計算各種因素的分數
        scores = {
            DataSource.GA4_API: 0.0,
            DataSource.BIGQUERY: 0.0
        }
        
        reasoning_parts = []
        
        # 1. 分析數據量需求
        data_volume_score = self._analyze_data_volume(query_params)
        scores[DataSource.BIGQUERY] += data_volume_score * self.routing_weights["data_volume"]
        scores[DataSource.GA4_API] += (1 - data_volume_score) * self.routing_weights["data_volume"]
        
        if data_volume_score > 0.7:
            reasoning_parts.append("large data volume favors BigQuery")
        elif data_volume_score < 0.3:
            reasoning_parts.append("small data volume favors GA4 API")
        
        # 2. 分析查詢複雜度
        complexity_score = self._analyze_query_complexity(query_params)
        scores[DataSource.BIGQUERY] += complexity_score * self.routing_weights["query_complexity"]
        scores[DataSource.GA4_API] += (1 - complexity_score) * self.routing_weights["query_complexity"]
        
        if complexity_score > 0.7:
            reasoning_parts.append("complex query favors BigQuery")
        elif complexity_score < 0.3:
            reasoning_parts.append("simple query favors GA4 API")
        
        # 3. 分析日期範圍
        date_range_score = self._analyze_date_range(query_params)
        scores[DataSource.BIGQUERY] += date_range_score * self.routing_weights["date_range"]
        scores[DataSource.GA4_API] += (1 - date_range_score) * self.routing_weights["date_range"]
        
        if date_range_score > 0.7:
            reasoning_parts.append("historical data favors BigQuery")
        elif date_range_score < 0.3:
            reasoning_parts.append("recent data favors GA4 API")
        
        # 4. 性能考量（GA4 API 通常更快）
        scores[DataSource.GA4_API] += 0.6 * self.routing_weights["performance"]
        scores[DataSource.BIGQUERY] += 0.4 * self.routing_weights["performance"]
        reasoning_parts.append("GA4 API generally faster")
        
        # 5. 服務可用性（假設都可用）
        scores[DataSource.GA4_API] += 0.5 * self.routing_weights["availability"]
        scores[DataSource.BIGQUERY] += 0.5 * self.routing_weights["availability"]
        
        # 選擇得分最高的數據源
        selected_source = max(scores.items(), key=lambda x: x[1])[0]
        
        reasoning = f"Selected {selected_source.value} (score: {scores[selected_source]:.3f}). Factors: {', '.join(reasoning_parts)}"
        
        return selected_source, reasoning
    
    def _analyze_data_volume(self, query_params: Dict[str, Any]) -> float:
        """
        分析數據量需求
        
        Returns:
            0.0-1.0，值越高越適合 BigQuery
        """
        score = 0.0
        
        # 檢查日期範圍長度
        date_ranges = query_params.get("date_ranges", [])
        if date_ranges:
            date_range = date_ranges[0]
            start_str = date_range.get("start_date", "30daysAgo")
            
            if "daysAgo" in start_str:
                days = int(start_str.replace("daysAgo", ""))
                if days > 90:
                    score += 0.4
                elif days > 30:
                    score += 0.2
        
        # 檢查維度數量（更多維度通常需要更多數據處理）
        dimensions = query_params.get("dimensions", [])
        if len(dimensions) > 2:
            score += 0.3
        elif len(dimensions) > 1:
            score += 0.1
        
        # 檢查指標數量
        metrics = query_params.get("metrics", [])
        if len(metrics) > 4:
            score += 0.2
        elif len(metrics) > 2:
            score += 0.1
        
        # 檢查限制數量
        limit = query_params.get("limit", 10)
        if limit > 100:
            score += 0.1
        
        return min(score, 1.0)
    
    def _analyze_query_complexity(self, query_params: Dict[str, Any]) -> float:
        """
        分析查詢複雜度
        
        Returns:
            0.0-1.0，值越高越適合 BigQuery
        """
        score = 0.0
        
        # 檢查是否有過濾器
        if query_params.get("filters"):
            score += 0.3
        
        # 檢查維度組合複雜度
        dimensions = query_params.get("dimensions", [])
        dim_names = [d.get("name", "") for d in dimensions]
        
        complex_dimensions = ["pageTitle", "eventName", "customDimension"]
        if any(dim in str(dim_names) for dim in complex_dimensions):
            score += 0.3
        
        # 檢查是否需要多個日期範圍比較
        date_ranges = query_params.get("date_ranges", [])
        if len(date_ranges) > 1:
            score += 0.4
        
        return min(score, 1.0)
    
    def _analyze_date_range(self, query_params: Dict[str, Any]) -> float:
        """
        分析日期範圍
        
        Returns:
            0.0-1.0，值越高越適合 BigQuery（歷史數據）
        """
        score = 0.0
        
        date_ranges = query_params.get("date_ranges", [])
        if not date_ranges:
            return 0.0
        
        date_range = date_ranges[0]
        start_str = date_range.get("start_date", "30daysAgo")
        
        if start_str == "today" or start_str == "yesterday":
            score = 0.1  # 非常新的數據，GA4 API 更好
        elif "daysAgo" in start_str:
            days = int(start_str.replace("daysAgo", ""))
            if days > 365:
                score = 1.0  # 超過一年的歷史數據，BigQuery 更好
            elif days > 90:
                score = 0.8  # 3個月以上，BigQuery 較好
            elif days > 30:
                score = 0.5  # 1-3個月，兩者都可以
            else:
                score = 0.2  # 30天內，GA4 API 較好
        
        return score
    
    def _get_query_type(self, query_params: Dict[str, Any]) -> str:
        """獲取查詢類型描述"""
        dimensions = query_params.get("dimensions", [])
        metrics = query_params.get("metrics", [])
        
        if not dimensions:
            return "aggregated_metrics"
        elif len(dimensions) == 1:
            return f"single_dimension_{dimensions[0].get('name', 'unknown')}"
        else:
            return f"multi_dimension_{len(dimensions)}_dims"
    
    async def _try_backup_source(
        self, 
        query_params: Dict[str, Any], 
        property_id: Optional[str], 
        failed_source: DataSource
    ) -> Optional[Dict[str, Any]]:
        """
        嘗試備用數據源
        
        Args:
            query_params: 查詢參數
            property_id: GA4 屬性ID
            failed_source: 失敗的數據源
            
        Returns:
            備用查詢結果或 None
        """
        try:
            if failed_source == DataSource.BIGQUERY:
                logger.info("Trying GA4 API as backup for failed BigQuery query")
                return await self.ga4_service.execute_query(query_params, property_id)
            
            elif failed_source == DataSource.GA4_API:
                if self.bigquery_service.is_available():
                    logger.info("Trying BigQuery as backup for failed GA4 API query")
                    return await self.bigquery_service.execute_query(query_params, property_id)
            
            return None
            
        except Exception as e:
            logger.error("Backup source also failed", error=str(e))
            return None
    
    async def get_routing_stats(self) -> Dict[str, Any]:
        """
        獲取路由統計信息
        
        Returns:
            路由統計
        """
        return {
            "bigquery_available": self.bigquery_service.is_available(),
            "ga4_api_available": self.ga4_service.client is not None,
            "routing_enabled": settings.ENABLE_BIGQUERY_ROUTING,
            "routing_weights": self.routing_weights,
            "mock_mode": settings.USE_MOCK_GA4_API
        }
    
    def _should_perform_trend_analysis(self, query_params: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """判斷是否應該執行趨勢分析"""
        
        # 檢查是否有時間維度
        dimensions = query_params.get("dimensions", [])
        has_time_dimension = any(dim in ["date", "dateHour", "week", "month"] for dim in dimensions)
        
        # 檢查是否有足夠的數據點
        rows = result.get("rows", [])
        has_sufficient_data = len(rows) >= 3
        
        return has_time_dimension and has_sufficient_data
    
    def _determine_cache_ttl(self, query_params: Dict[str, Any]) -> int:
        """根據查詢參數決定快取時間"""
        
        # 基礎 TTL：5 分鐘
        base_ttl = 300
        
        # 如果是實時數據查詢，縮短快取時間
        date_ranges = query_params.get("date_ranges", [])
        if date_ranges:
            for date_range in date_ranges:
                if isinstance(date_range, dict) and date_range.get("end_date") == "today":
                    return 60  # 實時數據快取 1 分鐘
        
        # 複雜查詢延長快取時間
        metrics = query_params.get("metrics", [])
        dimensions = query_params.get("dimensions", [])
        
        if len(metrics) > 3 or len(dimensions) > 2:
            return base_ttl * 2  # 複雜查詢快取 10 分鐘
        
        return base_ttl 