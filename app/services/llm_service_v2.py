"""
優化版 LLM 服務

添加並發控制、重試機制和成本追蹤
"""

from typing import Dict, Any, List, Optional
import structlog
import json
import asyncio
from asyncio import Semaphore
import time
from functools import wraps
from openai import AsyncOpenAI
import backoff

from app.core.config import settings
from app.core.logging import log_llm_request

logger = structlog.get_logger()


class LLMServiceError(Exception):
    """LLM 服務專用異常"""
    pass


class LLMRateLimitError(LLMServiceError):
    """LLM 速率限制異常"""
    pass


class LLMResponseError(LLMServiceError):
    """LLM 回應錯誤異常"""
    pass


class OptimizedLLMService:
    """優化的 LLM 服務類別"""
    
    def __init__(self, max_concurrent_requests: int = 5):
        self.use_mock = settings.USE_MOCK_LLM_API
        
        # 並發控制
        self.semaphore = Semaphore(max_concurrent_requests)
        self.active_requests = 0
        self.total_requests = 0
        
        # 成本追蹤
        self.total_tokens_used = 0
        self.total_cost = 0.0
        
        # 性能統計
        self.response_times = []
        self.error_count = 0
        
        # 初始化客戶端
        if not self.use_mock:
            self.client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                max_retries=3,
                timeout=30.0
            )
        
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE
        
        # Token 成本（每1000 tokens）
        self.token_costs = {
            "gpt-4o": {"input": 0.01, "output": 0.03},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002}
        }
    
    @backoff.on_exception(
        backoff.expo,
        (LLMRateLimitError, asyncio.TimeoutError),
        max_tries=3,
        max_time=60
    )
    async def generate_completion(self, prompt: str, **kwargs) -> str:
        """
        生成 LLM 回應（帶並發控制和重試）
        
        Args:
            prompt: 提示詞
            **kwargs: 額外參數
            
        Returns:
            LLM 回應
        """
        start_time = time.time()
        
        async with self.semaphore:  # 並發控制
            self.active_requests += 1
            self.total_requests += 1
            
            try:
                log_llm_request(prompt=prompt, model=self.model)
                
                # 如果使用模擬模式
                if self.use_mock:
                    await asyncio.sleep(0.5)  # 模擬延遲
                    return self._get_mock_response(prompt)
                
                # 合併參數
                params = {
                    "model": kwargs.get("model", self.model),
                    "messages": [
                        {"role": "system", "content": "你是一個專業的數據分析助手，專門幫助用戶理解 Google Analytics 4 數據。請用繁體中文回答。"},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                    "temperature": kwargs.get("temperature", self.temperature),
                    "stream": False
                }
                
                # 調用 OpenAI API
                response = await self.client.chat.completions.create(**params)
                
                # 追蹤使用情況
                self._track_usage(response)
                
                # 記錄響應時間
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                
                logger.info(
                    "LLM completion successful",
                    model=params["model"],
                    response_time=f"{response_time:.2f}s",
                    tokens_used=response.usage.total_tokens if hasattr(response, 'usage') else 0
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                self.error_count += 1
                
                # 處理特定錯誤類型
                if "rate_limit_exceeded" in str(e).lower():
                    logger.warning("LLM rate limit exceeded, will retry")
                    raise LLMRateLimitError(f"Rate limit exceeded: {e}")
                elif "timeout" in str(e).lower():
                    logger.warning("LLM request timeout")
                    raise asyncio.TimeoutError(f"Request timeout: {e}")
                else:
                    logger.error("LLM completion failed", error=str(e))
                    raise LLMResponseError(f"LLM error: {e}")
            
            finally:
                self.active_requests -= 1
    
    async def generate_response(
        self, 
        user_query: str, 
        ga4_data: Dict[str, Any], 
        intent: Any
    ) -> Dict[str, Any]:
        """
        根據 GA4 數據生成自然語言回應（優化版）
        
        Args:
            user_query: 用戶原始查詢
            ga4_data: GA4 查詢結果
            intent: 查詢意圖
            
        Returns:
            包含回應和信心度的字典
        """
        try:
            # 構建優化的提示詞
            prompt = self._build_optimized_prompt(user_query, ga4_data, intent)
            
            # 生成回應
            response = await self.generate_completion(prompt)
            
            # 計算信心度
            confidence = self._calculate_confidence(ga4_data, intent)
            
            return {
                "response": response,
                "confidence": confidence,
                "model": self.model,
                "active_requests": self.active_requests
            }
            
        except LLMServiceError as e:
            logger.error("Failed to generate response", error=str(e))
            return {
                "response": "抱歉，我暫時無法分析這些數據。請稍後再試。",
                "confidence": 0.3,
                "error": str(e)
            }
    
    async def generate_suggestions(
        self, 
        user_query: str, 
        ga4_data: Dict[str, Any]
    ) -> List[str]:
        """
        生成後續建議查詢（帶快取）
        
        Args:
            user_query: 用戶查詢
            ga4_data: GA4 數據
            
        Returns:
            建議查詢列表
        """
        try:
            # 簡化的提示詞以節省 tokens
            prompt = f"""基於用戶查詢「{user_query}」和數據分析結果，
請提供3個相關的後續問題建議。
只需要列出問題，每個問題一行，不需要其他說明。"""
            
            response = await self.generate_completion(
                prompt,
                max_tokens=200,
                temperature=0.5
            )
            
            # 解析建議
            suggestions = [
                line.strip().lstrip("- •123456789.")
                for line in response.strip().split("\n")
                if line.strip() and len(line.strip()) > 5
            ][:3]
            
            return suggestions
            
        except Exception as e:
            logger.error("Failed to generate suggestions", error=str(e))
            return []
    
    def _build_optimized_prompt(
        self, 
        user_query: str, 
        ga4_data: Dict[str, Any], 
        intent: Any
    ) -> str:
        """構建優化的提示詞"""
        
        # 根據意圖類型選擇模板
        templates = {
            "basic_metrics": "請分析這些基本指標數據，重點說明{metric_focus}的表現。",
            "trend_analysis": "請分析這些趨勢數據，說明{time_period}的變化情況和可能原因。",
            "comparison": "請比較這些數據，突出{comparison_items}之間的差異和洞察。",
            "page_analysis": "請分析這些頁面數據，找出表現最好和需要改進的頁面。",
            "traffic_sources": "請分析流量來源數據，說明各渠道的貢獻和優化建議。"
        }
        
        template = templates.get(intent.intent, "請分析這些數據並提供有價值的洞察。")
        
        # 準備數據摘要
        data_summary = self._summarize_data(ga4_data)
        
        prompt = f"""用戶問題：{user_query}

相關數據：
{data_summary}

{template}

請用簡潔、專業的語言回答，包含：
1. 數據的主要發現
2. 可能的原因或解釋
3. 可行的優化建議（如適用）
"""
        
        return prompt
    
    def _summarize_data(self, ga4_data: Dict[str, Any]) -> str:
        """摘要數據以減少 token 使用"""
        if not ga4_data or "rows" not in ga4_data:
            return "無數據"
        
        rows = ga4_data.get("rows", [])
        if not rows:
            return "查詢結果為空"
        
        # 限制數據量
        max_rows = 10
        if len(rows) > max_rows:
            summary = f"顯示前 {max_rows} 筆數據（共 {len(rows)} 筆）：\n"
            rows = rows[:max_rows]
        else:
            summary = f"共 {len(rows)} 筆數據：\n"
        
        # 格式化數據
        for row in rows:
            summary += f"- {', '.join(str(v) for v in row.values())}\n"
        
        return summary
    
    def _calculate_confidence(self, ga4_data: Dict[str, Any], intent: Any) -> float:
        """計算回應信心度"""
        confidence = 0.5
        
        # 有數據則增加信心度
        if ga4_data and "rows" in ga4_data and ga4_data["rows"]:
            confidence += 0.3
        
        # 意圖清晰則增加信心度
        if hasattr(intent, "confidence") and intent.confidence > 0.8:
            confidence += 0.2
        
        return min(confidence, 0.95)
    
    def _track_usage(self, response: Any):
        """追蹤 API 使用情況和成本"""
        if hasattr(response, 'usage'):
            usage = response.usage
            self.total_tokens_used += usage.total_tokens
            
            # 計算成本
            model_costs = self.token_costs.get(self.model, {"input": 0.01, "output": 0.03})
            input_cost = (usage.prompt_tokens / 1000) * model_costs["input"]
            output_cost = (usage.completion_tokens / 1000) * model_costs["output"]
            self.total_cost += input_cost + output_cost
    
    def _get_mock_response(self, prompt: str) -> str:
        """獲取模擬回應"""
        mock_responses = {
            "訪客": "根據數據顯示，您的網站昨天有 1,234 位訪客，比前一天增長了 15%。主要流量來自搜尋引擎(45%)和社交媒體(30%)。",
            "頁面": "最受歡迎的頁面是首頁，佔總瀏覽量的 35%。產品頁面的平均停留時間為 2分30秒，顯示用戶參與度良好。",
            "轉換": "本月轉換率為 3.5%，高於行業平均水平。購物車放棄率為 68%，建議優化結帳流程。",
            "default": "根據分析結果，您的網站表現良好。建議持續監控關鍵指標並進行 A/B 測試以持續優化。"
        }
        
        # 根據提示詞選擇適當的模擬回應
        for key, response in mock_responses.items():
            if key in prompt:
                return response
        
        return mock_responses["default"]
    
    async def get_stats(self) -> Dict[str, Any]:
        """獲取服務統計信息"""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        return {
            "total_requests": self.total_requests,
            "active_requests": self.active_requests,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.total_requests if self.total_requests > 0 else 0,
            "avg_response_time": f"{avg_response_time:.2f}s",
            "total_tokens_used": self.total_tokens_used,
            "total_cost": f"${self.total_cost:.4f}",
            "model": self.model
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
            
            # 測試 API 連接
            test_response = await self.generate_completion(
                "Test",
                max_tokens=10
            )
            
            return {
                "status": "healthy",
                "mode": "production",
                "model": self.model,
                "active_requests": self.active_requests,
                "api_responsive": bool(test_response)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "mode": "production" if not self.use_mock else "mock"
            }


# 創建單例實例
llm_service = OptimizedLLMService()