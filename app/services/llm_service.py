"""
LLM 服務

負責與大型語言模型交互，生成自然語言回應
"""

from typing import Dict, Any, List, Optional
import structlog
import json
import openai
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import log_llm_request

logger = structlog.get_logger()


class LLMService:
    """LLM 服務類別"""
    
    def __init__(self):
        self.use_mock = settings.USE_MOCK_LLM_API
        if not self.use_mock:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE
    
    async def generate_completion(self, prompt: str) -> str:
        """
        生成 LLM 回應
        
        Args:
            prompt: 提示詞
            
        Returns:
            LLM 回應
        """
        try:
            log_llm_request(prompt=prompt, model=self.model)
            
            # 如果使用模擬模式，返回模擬回應
            if self.use_mock:
                return self._get_mock_response(prompt)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一個專業的數據分析助手，專門幫助用戶理解 Google Analytics 4 數據。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("LLM completion failed", error=str(e))
            return "抱歉，我無法處理您的請求。請稍後再試。"
    
    async def generate_response(
        self, 
        user_query: str, 
        ga4_data: Dict[str, Any], 
        intent: Any
    ) -> Dict[str, Any]:
        """
        根據 GA4 數據生成自然語言回應
        
        Args:
            user_query: 用戶原始查詢
            ga4_data: GA4 查詢結果
            intent: 查詢意圖
            
        Returns:
            包含回應和信心度的字典
        """
        try:
            # 構建提示詞
            prompt = self._build_response_prompt(user_query, ga4_data, intent)
            
            # 生成回應
            response = await self.generate_completion(prompt)
            
            # 計算信心度
            confidence = self._calculate_confidence(ga4_data, intent)
            
            return {
                "response": response,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error("Failed to generate response", error=str(e))
            return {
                "response": "抱歉，我無法分析這些數據。請檢查您的查詢或稍後再試。",
                "confidence": 0.3
            }
    
    async def generate_suggestions(
        self, 
        user_query: str, 
        ga4_data: Dict[str, Any]
    ) -> List[str]:
        """
        生成建議查詢
        
        Args:
            user_query: 用戶原始查詢
            ga4_data: GA4 查詢結果
            
        Returns:
            建議查詢列表
        """
        try:
            prompt = f"""
            基於用戶的查詢和數據結果，生成3個相關的後續查詢建議。
            
            用戶查詢：{user_query}
            數據結果：{json.dumps(ga4_data, ensure_ascii=False, indent=2)}
            
            請返回3個自然語言的查詢建議，用中文回答，格式如下：
            1. [建議查詢1]
            2. [建議查詢2]
            3. [建議查詢3]
            """
            
            response = await self.generate_completion(prompt)
            
            # 解析回應中的建議
            suggestions = self._parse_suggestions(response)
            
            return suggestions[:3]  # 最多返回3個建議
            
        except Exception as e:
            logger.error("Failed to generate suggestions", error=str(e))
            return [
                "這些數據的趨勢如何？",
                "與上個月相比有什麼變化？",
                "哪些頁面表現最好？"
            ]
    
    def _build_response_prompt(self, user_query: str, ga4_data: Dict[str, Any], intent: Any) -> str:
        """構建回應提示詞"""
        
        # 根據意圖類型構建不同的提示詞
        if intent.intent == "basic_metrics":
            return self._build_basic_metrics_prompt(user_query, ga4_data)
        elif intent.intent == "page_analysis":
            return self._build_page_analysis_prompt(user_query, ga4_data)
        elif intent.intent == "traffic_sources":
            return self._build_traffic_sources_prompt(user_query, ga4_data)
        elif intent.intent == "trend_analysis":
            return self._build_trend_analysis_prompt(user_query, ga4_data)
        else:
            return self._build_general_prompt(user_query, ga4_data)
    
    def _build_basic_metrics_prompt(self, user_query: str, ga4_data: Dict[str, Any]) -> str:
        """構建基本指標分析提示詞"""
        return f"""
        你是一個專業的數據分析師，請根據以下 GA4 數據回答用戶的問題。
        
        用戶問題：{user_query}
        
        GA4 數據：
        {json.dumps(ga4_data, ensure_ascii=False, indent=2)}
        
        請用自然、易懂的中文回答，包含以下要點：
        1. 直接回答用戶的問題
        2. 提供關鍵數據的具體數值
        3. 簡要解釋數據的含義
        4. 如果有異常或值得注意的點，請指出
        
        回答要簡潔明瞭，適合非技術人員理解。
        """
    
    def _build_page_analysis_prompt(self, user_query: str, ga4_data: Dict[str, Any]) -> str:
        """構建頁面分析提示詞"""
        return f"""
        你是一個專業的網站分析師，請分析以下頁面數據並回答用戶的問題。
        
        用戶問題：{user_query}
        
        頁面數據：
        {json.dumps(ga4_data, ensure_ascii=False, indent=2)}
        
        請用自然、易懂的中文回答，包含以下要點：
        1. 識別表現最好和最差的頁面
        2. 分析頁面的用戶行為指標
        3. 提供改進建議
        4. 指出需要關注的異常情況
        
        回答要具體且實用，幫助用戶理解頁面表現。
        """
    
    def _build_traffic_sources_prompt(self, user_query: str, ga4_data: Dict[str, Any]) -> str:
        """構建流量來源分析提示詞"""
        return f"""
        你是一個專業的數位行銷分析師，請分析以下流量來源數據並回答用戶的問題。
        
        用戶問題：{user_query}
        
        流量來源數據：
        {json.dumps(ga4_data, ensure_ascii=False, indent=2)}
        
        請用自然、易懂的中文回答，包含以下要點：
        1. 識別主要的流量來源
        2. 分析各渠道的表現
        3. 比較不同渠道的效果
        4. 提供優化建議
        
        回答要專業且實用，幫助用戶優化行銷策略。
        """
    
    def _build_trend_analysis_prompt(self, user_query: str, ga4_data: Dict[str, Any]) -> str:
        """構建趨勢分析提示詞"""
        return f"""
        你是一個專業的趨勢分析師，請分析以下時間序列數據並回答用戶的問題。
        
        用戶問題：{user_query}
        
        趨勢數據：
        {json.dumps(ga4_data, ensure_ascii=False, indent=2)}
        
        請用自然、易懂的中文回答，包含以下要點：
        1. 識別整體趨勢方向
        2. 指出關鍵的變化點
        3. 分析趨勢的原因
        4. 預測未來可能的發展
        
        回答要深入且有洞察力，幫助用戶理解數據趨勢。
        """
    
    def _build_general_prompt(self, user_query: str, ga4_data: Dict[str, Any]) -> str:
        """構建通用分析提示詞"""
        return f"""
        你是一個專業的數據分析師，請根據以下 GA4 數據回答用戶的問題。
        
        用戶問題：{user_query}
        
        GA4 數據：
        {json.dumps(ga4_data, ensure_ascii=False, indent=2)}
        
        請用自然、易懂的中文回答，要求：
        1. 直接回答用戶的問題
        2. 提供具體的數據支持
        3. 解釋數據的含義
        4. 提供實用的見解
        
        回答要專業、準確且易於理解。
        """
    
    def _calculate_confidence(self, ga4_data: Dict[str, Any], intent: Any) -> float:
        """計算回應的信心度"""
        base_confidence = intent.confidence
        
        # 根據數據質量調整信心度
        if not ga4_data or "rows" not in ga4_data:
            return base_confidence * 0.5
        
        # 數據行數越多，信心度越高
        row_count = len(ga4_data.get("rows", []))
        if row_count > 0:
            data_quality_factor = min(1.0, row_count / 10.0)
            return min(0.95, base_confidence * (0.7 + 0.3 * data_quality_factor))
        
        return base_confidence * 0.7
    
    def _parse_suggestions(self, response: str) -> List[str]:
        """解析建議查詢"""
        suggestions = []
        
        # 簡單的解析邏輯
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                suggestion = line.split('.', 1)[1].strip()
                if suggestion:
                    suggestions.append(suggestion)
        
        # 如果解析失敗，返回默認建議
        if not suggestions:
            suggestions = [
                "這些數據的趨勢如何？",
                "與上個月相比有什麼變化？",
                "哪些頁面表現最好？"
            ]
        
        return suggestions
    
    def _get_mock_response(self, prompt: str) -> str:
        """
        生成模擬 LLM 回應（用於開發和測試）
        
        Args:
            prompt: 提示詞
            
        Returns:
            模擬回應
        """
        # 根據提示詞關鍵字生成不同的模擬回應
        prompt_lower = prompt.lower()
        
        if "訪客" in prompt_lower or "用戶" in prompt_lower or "users" in prompt_lower:
            return """根據您的 GA4 數據分析，以下是關於訪客的洞察：

📊 **訪客概況**
- 總訪客數：12,456 人
- 新訪客：8,234 人 (66.1%)
- 回訪者：4,222 人 (33.9%)

📈 **趨勢分析**
- 與上週相比增長 15.3%
- 移動端訪客占 68.2%
- 桌面端訪客占 31.8%

💡 **建議**
1. 繼續優化移動端體驗
2. 加強回訪者的留存策略
3. 分析新訪客的來源渠道"""

        elif "頁面" in prompt_lower or "page" in prompt_lower:
            return """根據您的 GA4 頁面分析數據：

🏃 **熱門頁面排行**
1. 首頁 - 3,456 次瀏覽
2. 產品頁面 - 2,134 次瀏覽  
3. 關於我們 - 1,567 次瀏覽
4. 聯絡我們 - 987 次瀏覽
5. 部落格 - 765 次瀏覽

⏱️ **頁面表現**
- 平均停留時間：2分34秒
- 跳出率：45.2%
- 頁面載入速度：1.8秒

🎯 **優化建議**
1. 提升載入速度較慢的頁面
2. 優化跳出率較高的頁面內容
3. 增加內部連結提升頁面深度"""

        elif "流量" in prompt_lower or "來源" in prompt_lower or "source" in prompt_lower:
            return """根據您的 GA4 流量來源分析：

🌐 **主要流量來源**
1. 直接流量 - 45.2% (5,634 次會話)
2. 搜尋引擎 - 32.1% (4,002 次會話)
3. 社群媒體 - 15.7% (1,956 次會話)
4. 推薦網站 - 4.8% (598 次會話)
5. 電子郵件 - 2.2% (274 次會話)

🔍 **搜尋引擎詳細**
- Google: 89.3%
- Bing: 7.2%
- Yahoo: 3.5%

📱 **社群媒體詳細**
- Facebook: 52.1%
- Instagram: 28.7%
- LinkedIn: 19.2%

💡 **行銷建議**
1. 加強 SEO 優化提升搜尋排名
2. 增加社群媒體互動
3. 建立更多優質的外部連結"""

        else:
            return """感謝您使用 GA+ 進行數據分析！

📊 **數據概覽**
基於您的 GA4 數據，我為您整理了以下關鍵指標：

- 總會話數：15,678 次
- 總用戶數：12,456 人  
- 平均會話時長：3分42秒
- 轉換率：2.8%

📈 **主要發現**
1. 移動端流量持續增長，占總流量的 68%
2. 週末的用戶參與度比平日高 23%
3. 產品頁面的停留時間較長，顯示用戶興趣度高

🎯 **建議行動**
1. 優化移動端用戶體驗
2. 在週末投放更多行銷活動
3. 加強產品頁面的轉換漏斗優化

需要更詳細的分析嗎？您可以問我具體的問題！"""