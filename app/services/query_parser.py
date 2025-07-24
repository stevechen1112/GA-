"""
查詢解析器服務

負責解析自然語言查詢並轉換為 GA4 API 查詢
"""

from typing import Dict, Any, List, Optional
import structlog
import re
from datetime import datetime, timedelta

from app.core.config import settings
from app.services.llm_service import LLMService

logger = structlog.get_logger()


class QueryIntent:
    """查詢意圖類別"""
    
    def __init__(self, intent: str, confidence: float, entities: Dict[str, Any], parameters: Dict[str, Any]):
        self.intent = intent
        self.confidence = confidence
        self.entities = entities
        self.parameters = parameters
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "entities": self.entities,
            "parameters": self.parameters
        }


class QueryParser:
    """查詢解析器"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.intent_patterns = self._load_intent_patterns()
        self.metric_mappings = self._load_metric_mappings()
    
    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        """載入意圖識別模式"""
        return {
            "basic_metrics": [
                r"有多少.*訪客",
                r".*流量.*",
                r".*用戶.*",
                r".*轉換.*",
                r".*收入.*"
            ],
            "page_analysis": [
                r"最熱門.*頁面",
                r".*頁面.*跳出率",
                r".*頁面.*訪問",
                r"用戶.*訪問.*頁面"
            ],
            "traffic_sources": [
                r"流量來源",
                r".*渠道.*",
                r".*廣告.*",
                r".*來源.*"
            ],
            "user_behavior": [
                r"用戶.*行為",
                r"停留時間",
                r"會話深度",
                r"新用戶.*老用戶"
            ],
            "conversion_analysis": [
                r"轉換漏斗",
                r"轉換率",
                r"流失.*",
                r"漏斗.*"
            ],
            "trend_analysis": [
                r"趨勢.*",
                r"變化.*",
                r"增長.*",
                r"下降.*"
            ],
            "comparison": [
                r"比較.*",
                r"對比.*",
                r"vs.*",
                r"相比.*"
            ]
        }
    
    def _load_metric_mappings(self) -> Dict[str, List[str]]:
        """載入指標映射"""
        return {
            "visitors": ["totalUsers", "newUsers", "activeUsers"],
            "traffic": ["sessions", "screenPageViews", "pageViews"],
            "conversion": ["conversions", "conversionRate", "totalRevenue"],
            "engagement": ["engagedSessions", "bounceRate", "sessionDuration"],
            "pages": ["screenPageViews", "pageViews", "screenPageViewsPerSession"],
            "sources": ["sessions", "totalUsers", "conversions"]
        }
    
    async def parse_query(self, query: str) -> QueryIntent:
        """
        解析自然語言查詢
        
        Args:
            query: 用戶查詢
            
        Returns:
            查詢意圖
        """
        try:
            # 1. 使用規則基礎的意圖識別
            intent = self._rule_based_intent_recognition(query)
            
            # 2. 使用 LLM 進行更精確的意圖識別
            llm_intent = await self._llm_intent_recognition(query)
            
            # 3. 合併結果
            final_intent = self._merge_intents(intent, llm_intent)
            
            # 4. 提取實體和參數
            entities = self._extract_entities(query)
            parameters = self._extract_parameters(query)
            
            logger.info(
                "Query parsed successfully",
                original_query=query,
                intent=final_intent,
                confidence=llm_intent.get("confidence", 0.8)
            )
            
            return QueryIntent(
                intent=final_intent,
                confidence=llm_intent.get("confidence", 0.8),
                entities=entities,
                parameters=parameters
            )
            
        except Exception as e:
            logger.error("Query parsing failed", query=query, error=str(e))
            # 返回默認意圖
            return QueryIntent(
                intent="basic_metrics",
                confidence=0.5,
                entities={},
                parameters={"date_range": "last_30_days"}
            )
    
    def _rule_based_intent_recognition(self, query: str) -> str:
        """規則基礎的意圖識別"""
        query_lower = query.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent
        
        return "basic_metrics"  # 默認意圖
    
    async def _llm_intent_recognition(self, query: str) -> Dict[str, Any]:
        """使用 LLM 進行意圖識別"""
        try:
            prompt = f"""
            請分析以下查詢的意圖，並返回 JSON 格式的結果：
            
            查詢：{query}
            
            請返回以下格式：
            {{
                "intent": "意圖類型",
                "confidence": 0.95,
                "entities": {{
                    "metrics": ["指標列表"],
                    "dimensions": ["維度列表"],
                    "date_range": "時間範圍"
                }},
                "parameters": {{
                    "comparison": "是否比較查詢",
                    "trend": "是否趨勢查詢"
                }}
            }}
            
            支援的意圖類型：
            - basic_metrics: 基本指標查詢
            - page_analysis: 頁面分析
            - traffic_sources: 流量來源分析
            - user_behavior: 用戶行為分析
            - conversion_analysis: 轉換分析
            - trend_analysis: 趨勢分析
            - comparison: 比較分析
            """
            
            response = await self.llm_service.generate_completion(prompt)
            
            # TODO: 解析 LLM 回應
            return {
                "intent": "basic_metrics",
                "confidence": 0.9,
                "entities": {},
                "parameters": {}
            }
            
        except Exception as e:
            logger.error("LLM intent recognition failed", error=str(e))
            return {
                "intent": "basic_metrics",
                "confidence": 0.5,
                "entities": {},
                "parameters": {}
            }
    
    def _merge_intents(self, rule_intent: str, llm_intent: Dict[str, Any]) -> str:
        """合併規則和 LLM 的意圖識別結果"""
        llm_intent_type = llm_intent.get("intent", rule_intent)
        
        # 如果 LLM 信心度較高，使用 LLM 結果
        if llm_intent.get("confidence", 0) > 0.8:
            return llm_intent_type
        
        return rule_intent
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """提取查詢中的實體"""
        entities = {
            "metrics": [],
            "dimensions": [],
            "date_range": "last_30_days"
        }
        
        # 提取時間範圍
        time_patterns = {
            r"昨天": "yesterday",
            r"今天": "today",
            r"本週": "last_7_days",
            r"本月": "last_30_days",
            r"上個月": "last_month",
            r"去年": "last_year"
        }
        
        for pattern, value in time_patterns.items():
            if re.search(pattern, query):
                entities["date_range"] = value
                break
        
        # 提取指標
        for metric_type, metrics in self.metric_mappings.items():
            if any(metric in query for metric in metrics):
                entities["metrics"].extend(metrics)
        
        return entities
    
    def _extract_parameters(self, query: str) -> Dict[str, Any]:
        """提取查詢參數"""
        parameters = {
            "comparison": False,
            "trend": False,
            "limit": 10
        }
        
        # 檢查是否為比較查詢
        if re.search(r"比較|對比|vs|相比", query):
            parameters["comparison"] = True
        
        # 檢查是否為趨勢查詢
        if re.search(r"趨勢|變化|增長|下降", query):
            parameters["trend"] = True
        
        return parameters
    
    async def generate_ga4_query(self, intent: QueryIntent, property_id: Optional[str] = None) -> Dict[str, Any]:
        """
        根據意圖生成 GA4 查詢
        
        Args:
            intent: 查詢意圖
            property_id: GA4 屬性ID
            
        Returns:
            GA4 查詢參數
        """
        try:
            # 根據意圖類型生成不同的查詢
            if intent.intent == "basic_metrics":
                return self._generate_basic_metrics_query(intent, property_id)
            elif intent.intent == "page_analysis":
                return self._generate_page_analysis_query(intent, property_id)
            elif intent.intent == "traffic_sources":
                return self._generate_traffic_sources_query(intent, property_id)
            elif intent.intent == "user_behavior":
                return self._generate_user_behavior_query(intent, property_id)
            elif intent.intent == "conversion_analysis":
                return self._generate_conversion_analysis_query(intent, property_id)
            elif intent.intent == "trend_analysis":
                return self._generate_trend_analysis_query(intent, property_id)
            elif intent.intent == "comparison":
                return self._generate_comparison_query(intent, property_id)
            else:
                return self._generate_basic_metrics_query(intent, property_id)
                
        except Exception as e:
            logger.error("Failed to generate GA4 query", intent=intent.intent, error=str(e))
            return self._generate_default_query(property_id)
    
    def _generate_basic_metrics_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成基本指標查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "sessions"},
                {"name": "screenPageViews"},
                {"name": "conversions"}
            ],
            "dimensions": [],
            "limit": 10
        }
    
    def _generate_page_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成頁面分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "screenPageViews"},
                {"name": "totalUsers"},
                {"name": "bounceRate"}
            ],
            "dimensions": [{"name": "pageTitle"}],
            "limit": 10
        }
    
    def _generate_traffic_sources_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成流量來源查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "sessions"},
                {"name": "totalUsers"},
                {"name": "conversions"}
            ],
            "dimensions": [{"name": "sessionDefaultChannelGrouping"}],
            "limit": 10
        }
    
    def _generate_user_behavior_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成用戶行為查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "sessionDuration"},
                {"name": "sessionsPerUser"},
                {"name": "screenPageViewsPerSession"}
            ],
            "dimensions": [],
            "limit": 10
        }
    
    def _generate_conversion_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成轉換分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "conversions"},
                {"name": "conversionRate"},
                {"name": "totalRevenue"}
            ],
            "dimensions": [],
            "limit": 10
        }
    
    def _generate_trend_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成趨勢分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "90daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "sessions"}
            ],
            "dimensions": [{"name": "date"}],
            "limit": 90
        }
    
    def _generate_comparison_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成比較查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [
                {"start_date": "60daysAgo", "end_date": "31daysAgo"},
                {"start_date": "30daysAgo", "end_date": "today"}
            ],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "sessions"}
            ],
            "dimensions": [],
            "limit": 10
        }
    
    def _generate_default_query(self, property_id: Optional[str]) -> Dict[str, Any]:
        """生成默認查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [{"name": "totalUsers"}],
            "dimensions": [],
            "limit": 10
        } 