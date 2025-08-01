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
        """載入意圖識別模式（擴展到20+種查詢類型）"""
        return {
            # 基礎查詢類型
            "basic_metrics": [
                r"有多少.*訪客",
                r".*流量.*",
                r".*用戶.*",
                r".*轉換.*",
                r".*收入.*",
                r"總.*數據",
                r"整體.*表現"
            ],
            "page_analysis": [
                r"最熱門.*頁面",
                r".*頁面.*跳出率",
                r".*頁面.*訪問",
                r"用戶.*訪問.*頁面",
                r"頁面.*效果",
                r"內容.*分析"
            ],
            "traffic_sources": [
                r"流量來源",
                r".*渠道.*",
                r".*廣告.*",
                r".*來源.*",
                r"推廣.*效果",
                r"行銷.*渠道"
            ],
            "user_behavior": [
                r"用戶.*行為",
                r"停留時間",
                r"會話深度",
                r"新用戶.*老用戶",
                r"用戶.*互動",
                r"參與度"
            ],
            "conversion_analysis": [
                r"轉換漏斗",
                r"轉換率",
                r"流失.*",
                r"漏斗.*",
                r"目標.*完成",
                r"轉化.*分析"
            ],
            "trend_analysis": [
                r"趨勢.*",
                r"變化.*",
                r"增長.*",
                r"下降.*",
                r"時間.*序列",
                r"發展.*趨勢"
            ],
            "comparison": [
                r"比較.*",
                r"對比.*",
                r"vs.*",
                r"相比.*",
                r"差異.*",
                r"對照.*"
            ],
            
            # 新增查詢類型
            "demographic_analysis": [
                r"用戶.*年齡",
                r".*性別.*",
                r"地理.*位置",
                r"人口.*統計",
                r"用戶.*畫像",
                r"受眾.*分析"
            ],
            "device_analysis": [
                r"設備.*類型",
                r"行動.*設備",
                r"桌面.*用戶",
                r"瀏覽器.*",
                r"作業系統",
                r"技術.*統計"
            ],
            "ecommerce_analysis": [
                r"購買.*行為",
                r"商品.*銷售",
                r"電商.*數據",
                r"訂單.*分析",
                r"營收.*分析",
                r"購物.*車"
            ],
            "event_analysis": [
                r"事件.*追蹤",
                r"自定義.*事件",
                r"互動.*事件",
                r"點擊.*分析",
                r"下載.*統計",
                r"表單.*提交"
            ],
            "cohort_analysis": [
                r"世代.*分析",
                r"用戶.*留存",
                r"生命週期",
                r"留存.*率",
                r"用戶.*回訪",
                r"忠誠度.*分析"
            ],
            "funnel_analysis": [
                r"漏斗.*分析",
                r"轉換.*路徑",
                r"用戶.*流程",
                r"步驟.*分析",
                r"流程.*優化",
                r"路徑.*分析"
            ],
            "attribution_analysis": [
                r"歸因.*分析",
                r"渠道.*貢獻",
                r"觸點.*分析",
                r"轉換.*路徑",
                r"歸因.*模型",
                r"多渠道.*分析"
            ],
            "real_time_analysis": [
                r"即時.*數據",
                r"實時.*監控",
                r"當前.*活躍",
                r"線上.*用戶",
                r"即時.*流量",
                r"現在.*狀況"
            ],
            "geographic_analysis": [
                r"地區.*分析",
                r"國家.*統計",
                r"城市.*數據",
                r"地理.*分布",
                r"區域.*表現",
                r"位置.*分析"
            ],
            "time_analysis": [
                r"時間.*分析",
                r"小時.*統計",
                r"一天.*中",
                r"週.*分析",
                r"月.*統計",
                r"季節.*性"
            ],
            "search_analysis": [
                r"搜索.*關鍵字",
                r"站內.*搜索",
                r"搜索.*行為",
                r"關鍵詞.*分析",
                r"搜索.*結果",
                r"查詢.*統計"
            ],
            "social_analysis": [
                r"社交.*媒體",
                r"社群.*流量",
                r"分享.*統計",
                r"社交.*互動",
                r"社群.*分析",
                r"病毒.*傳播"
            ],
            "content_analysis": [
                r"內容.*效果",
                r"文章.*分析",
                r"媒體.*統計",
                r"內容.*互動",
                r"閱讀.*行為",
                r"內容.*優化"
            ],
            "performance_analysis": [
                r"網站.*速度",
                r"載入.*時間",
                r"性能.*分析",
                r"技術.*指標",
                r"用戶.*體驗",
                r"網站.*健康"
            ],
            "campaign_analysis": [
                r"廣告.*活動",
                r"推廣.*效果",
                r"行銷.*活動",
                r"廣告.*ROI",
                r"活動.*分析",
                r"推廣.*統計"
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
            
            # 解析 LLM 回應
            try:
                import json
                # 嘗試解析 JSON 回應
                parsed_response = json.loads(response)
                return {
                    "intent": parsed_response.get("intent", "basic_metrics"),
                    "confidence": parsed_response.get("confidence", 0.8),
                    "entities": parsed_response.get("entities", {}),
                    "parameters": parsed_response.get("parameters", {})
                }
            except (json.JSONDecodeError, KeyError):
                # 如果 JSON 解析失敗，使用簡單的文本解析
                return self._parse_llm_text_response(response)
            
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
    
    def _parse_llm_text_response(self, response: str) -> Dict[str, Any]:
        """
        解析 LLM 的文本回應（當 JSON 解析失敗時使用）
        
        Args:
            response: LLM 的文本回應
            
        Returns:
            解析後的意圖資訊
        """
        response_lower = response.lower()
        
        # 根據回應內容推斷意圖
        intent = "basic_metrics"  # 默認
        confidence = 0.7
        
        if any(keyword in response_lower for keyword in ["頁面", "page", "熱門"]):
            intent = "page_analysis"
            confidence = 0.8
        elif any(keyword in response_lower for keyword in ["來源", "渠道", "source", "channel"]):
            intent = "traffic_sources"
            confidence = 0.8
        elif any(keyword in response_lower for keyword in ["行為", "停留", "behavior", "session"]):
            intent = "user_behavior"
            confidence = 0.8
        elif any(keyword in response_lower for keyword in ["轉換", "conversion", "漏斗"]):
            intent = "conversion_analysis"
            confidence = 0.8
        elif any(keyword in response_lower for keyword in ["趨勢", "變化", "trend", "change"]):
            intent = "trend_analysis"
            confidence = 0.8
        elif any(keyword in response_lower for keyword in ["比較", "對比", "compare", "vs"]):
            intent = "comparison"
            confidence = 0.8
        
        return {
            "intent": intent,
            "confidence": confidence,
            "entities": {},
            "parameters": {}
        }
    
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
        根據意圖生成 GA4 查詢（支援20+種查詢類型）
        
        Args:
            intent: 查詢意圖
            property_id: GA4 屬性ID
            
        Returns:
            GA4 查詢參數
        """
        try:
            # 查詢生成方法映射
            query_generators = {
                # 基礎查詢類型
                "basic_metrics": self._generate_basic_metrics_query,
                "page_analysis": self._generate_page_analysis_query,
                "traffic_sources": self._generate_traffic_sources_query,
                "user_behavior": self._generate_user_behavior_query,
                "conversion_analysis": self._generate_conversion_analysis_query,
                "trend_analysis": self._generate_trend_analysis_query,
                "comparison": self._generate_comparison_query,
                
                # 新增查詢類型
                "demographic_analysis": self._generate_demographic_analysis_query,
                "device_analysis": self._generate_device_analysis_query,
                "ecommerce_analysis": self._generate_ecommerce_analysis_query,
                "event_analysis": self._generate_event_analysis_query,
                "cohort_analysis": self._generate_cohort_analysis_query,
                "funnel_analysis": self._generate_funnel_analysis_query,
                "attribution_analysis": self._generate_attribution_analysis_query,
                "real_time_analysis": self._generate_real_time_analysis_query,
                "geographic_analysis": self._generate_geographic_analysis_query,
                "time_analysis": self._generate_time_analysis_query,
                "search_analysis": self._generate_search_analysis_query,
                "social_analysis": self._generate_social_analysis_query,
                "content_analysis": self._generate_content_analysis_query,
                "performance_analysis": self._generate_performance_analysis_query,
                "campaign_analysis": self._generate_campaign_analysis_query
            }
            
            # 獲取對應的查詢生成器
            generator = query_generators.get(intent.intent, self._generate_basic_metrics_query)
            return generator(intent, property_id)
                
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
    
    # 新增查詢類型生成方法
    
    def _generate_demographic_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成人口統計分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "sessions"},
                {"name": "conversions"}
            ],
            "dimensions": [
                {"name": "userAgeBracket"},
                {"name": "userGender"}
            ],
            "limit": 20
        }
    
    def _generate_device_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成設備分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "sessions"},
                {"name": "bounceRate"}
            ],
            "dimensions": [
                {"name": "deviceCategory"},
                {"name": "operatingSystem"},
                {"name": "browser"}
            ],
            "limit": 15
        }
    
    def _generate_ecommerce_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成電商分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalRevenue"},
                {"name": "transactions"},
                {"name": "averageOrderValue"},
                {"name": "ecommercePurchases"}
            ],
            "dimensions": [
                {"name": "itemName"},
                {"name": "itemCategory"}
            ],
            "limit": 20
        }
    
    def _generate_event_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成事件分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "eventCount"},
                {"name": "totalUsers"},
                {"name": "eventsPerSession"}
            ],
            "dimensions": [
                {"name": "eventName"},
                {"name": "customEvent:event_category"}
            ],
            "limit": 25
        }
    
    def _generate_cohort_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成世代分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "90daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "newUsers"},
                {"name": "returningUsers"}
            ],
            "dimensions": [
                {"name": "cohort"},
                {"name": "cohortNthDay"}
            ],
            "limit": 30
        }
    
    def _generate_funnel_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成漏斗分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "conversions"},
                {"name": "conversionRate"}
            ],
            "dimensions": [
                {"name": "eventName"},
                {"name": "funnelStep"}
            ],
            "limit": 10
        }
    
    def _generate_attribution_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成歸因分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "conversions"},
                {"name": "totalRevenue"},
                {"name": "attributedConversions"}
            ],
            "dimensions": [
                {"name": "sessionDefaultChannelGrouping"},
                {"name": "attributionModel"}
            ],
            "limit": 15
        }
    
    def _generate_real_time_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成即時分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "today", "end_date": "today"}],
            "metrics": [
                {"name": "activeUsers"},
                {"name": "screenPageViews"},
                {"name": "eventCount"}
            ],
            "dimensions": [
                {"name": "unifiedScreenName"},
                {"name": "deviceCategory"}
            ],
            "limit": 10
        }
    
    def _generate_geographic_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成地理分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "sessions"},
                {"name": "conversions"}
            ],
            "dimensions": [
                {"name": "country"},
                {"name": "region"},
                {"name": "city"}
            ],
            "limit": 25
        }
    
    def _generate_time_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成時間分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "sessions"},
                {"name": "screenPageViews"}
            ],
            "dimensions": [
                {"name": "hour"},
                {"name": "dayOfWeek"},
                {"name": "date"}
            ],
            "limit": 24
        }
    
    def _generate_search_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成搜索分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "eventCount"},
                {"name": "conversions"}
            ],
            "dimensions": [
                {"name": "searchTerm"},
                {"name": "unifiedScreenName"}
            ],
            "limit": 20
        }
    
    def _generate_social_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成社交分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "sessions"},
                {"name": "socialInteractions"}
            ],
            "dimensions": [
                {"name": "socialNetwork"},
                {"name": "sessionDefaultChannelGrouping"}
            ],
            "limit": 15
        }
    
    def _generate_content_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成內容分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "screenPageViews"},
                {"name": "totalUsers"},
                {"name": "averageSessionDuration"}
            ],
            "dimensions": [
                {"name": "pageTitle"},
                {"name": "contentGroup1"},
                {"name": "unifiedScreenName"}
            ],
            "limit": 20
        }
    
    def _generate_performance_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成性能分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "7daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "bounceRate"},
                {"name": "averageSessionDuration"}
            ],
            "dimensions": [
                {"name": "pageLoadTime"},
                {"name": "unifiedScreenName"}
            ],
            "limit": 15
        }
    
    def _generate_campaign_analysis_query(self, intent: QueryIntent, property_id: Optional[str]) -> Dict[str, Any]:
        """生成廣告活動分析查詢"""
        return {
            "property_id": property_id or settings.GA4_PROPERTY_ID,
            "date_ranges": [{"start_date": "30daysAgo", "end_date": "today"}],
            "metrics": [
                {"name": "totalUsers"},
                {"name": "sessions"},
                {"name": "conversions"},
                {"name": "totalRevenue"}
            ],
            "dimensions": [
                {"name": "campaignName"},
                {"name": "sourceMedium"},
                {"name": "googleAdsAdGroupName"}
            ],
            "limit": 20
        } 