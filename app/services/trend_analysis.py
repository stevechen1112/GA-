"""
趨勢分析服務

負責時間序列分析、趨勢檢測和變化分析
"""

from typing import Dict, Any, List, Optional, Tuple
import structlog
from datetime import datetime, timedelta
import statistics
from enum import Enum

logger = structlog.get_logger()

# 嘗試導入科學計算庫，如果失敗則使用基礎實現
try:
    import numpy as np
    import scipy.stats as stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    np = None
    stats = None


class TrendDirection(Enum):
    """趨勢方向枚舉"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class TrendStrength(Enum):
    """趨勢強度枚舉"""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class TrendAnalysisService:
    """趨勢分析服務類別"""
    
    def __init__(self):
        self.volatility_threshold = 0.2  # 波動性閾值
        self.trend_threshold = 0.1       # 趨勢閾值
        self.significance_level = 0.05   # 統計顯著性水平
    
    async def analyze_trend(
        self, 
        data: List[Dict[str, Any]], 
        metric_name: str,
        time_dimension: str = "date"
    ) -> Dict[str, Any]:
        """
        分析數據趨勢
        
        Args:
            data: 時間序列數據
            metric_name: 要分析的指標名稱
            time_dimension: 時間維度名稱
            
        Returns:
            趨勢分析結果
        """
        try:
            if not data:
                return self._empty_trend_result()
            
            # 1. 提取和清理時間序列數據
            time_series = self._extract_time_series(data, metric_name, time_dimension)
            
            if len(time_series) < 3:
                return self._insufficient_data_result()
            
            # 2. 計算基本統計指標
            basic_stats = self._calculate_basic_statistics(time_series)
            
            # 3. 檢測趨勢方向和強度
            trend_direction, trend_strength = self._detect_trend(time_series)
            
            # 4. 計算變化率
            change_rates = self._calculate_change_rates(time_series)
            
            # 5. 檢測異常值
            anomalies = self._detect_anomalies(time_series)
            
            # 6. 預測未來趨勢（簡化版）
            forecast = self._simple_forecast(time_series)
            
            # 7. 生成趨勢洞察
            insights = self._generate_trend_insights(
                time_series, trend_direction, trend_strength, change_rates, anomalies
            )
            
            return {
                "metric_name": metric_name,
                "time_period": {
                    "start": time_series[0]["date"] if time_series else None,
                    "end": time_series[-1]["date"] if time_series else None,
                    "data_points": len(time_series)
                },
                "trend": {
                    "direction": trend_direction.value,
                    "strength": trend_strength.value,
                    "confidence": basic_stats.get("trend_confidence", 0.0)
                },
                "statistics": basic_stats,
                "change_analysis": {
                    "overall_change": change_rates.get("overall", 0.0),
                    "average_change": change_rates.get("average", 0.0),
                    "volatility": change_rates.get("volatility", 0.0)
                },
                "anomalies": anomalies,
                "forecast": forecast,
                "insights": insights,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Trend analysis failed", error=str(e))
            return {
                "error": True,
                "message": f"Failed to analyze trend: {str(e)}",
                "metric_name": metric_name
            }
    
    def _extract_time_series(
        self, 
        data: List[Dict[str, Any]], 
        metric_name: str, 
        time_dimension: str
    ) -> List[Dict[str, Any]]:
        """提取時間序列數據"""
        
        time_series = []
        
        for row in data:
            try:
                # 提取時間值
                if "dimension_values" in row and "metric_values" in row:
                    # GA4 格式數據
                    dim_values = row.get("dimension_values", [])
                    metric_values = row.get("metric_values", [])
                    
                    if dim_values and metric_values:
                        date_str = dim_values[0]  # 假設第一個維度是日期
                        metric_value = float(metric_values[0]) if metric_values[0] else 0.0
                        
                        time_series.append({
                            "date": date_str,
                            "value": metric_value
                        })
                else:
                    # 直接格式數據
                    if time_dimension in row and metric_name in row:
                        time_series.append({
                            "date": row[time_dimension],
                            "value": float(row[metric_name])
                        })
            except (ValueError, IndexError, KeyError) as e:
                logger.warning("Failed to parse data row", error=str(e), row=row)
                continue
        
        # 按日期排序
        time_series.sort(key=lambda x: x["date"])
        
        return time_series
    
    def _calculate_basic_statistics(self, time_series: List[Dict[str, Any]]) -> Dict[str, float]:
        """計算基本統計指標"""
        
        values = [point["value"] for point in time_series]
        
        if not values:
            return {}
        
        try:
            basic_stats = {
                "count": len(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "range": max(values) - min(values)
            }
            
            if len(values) > 1:
                basic_stats["std_dev"] = statistics.stdev(values)
                basic_stats["variance"] = statistics.variance(values)
                basic_stats["coefficient_of_variation"] = basic_stats["std_dev"] / basic_stats["mean"] if basic_stats["mean"] != 0 else 0
            
            # 計算趨勢信心度（基於 R² 或簡化方法）
            if SCIPY_AVAILABLE and len(values) > 2:
                x = np.arange(len(values))
                y = np.array(values)
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                basic_stats["trend_confidence"] = abs(r_value)
                basic_stats["trend_p_value"] = p_value
                basic_stats["trend_slope"] = slope
            else:
                # 簡化的趨勢信心度計算
                if len(values) > 2:
                    first_half = values[:len(values)//2]
                    second_half = values[len(values)//2:]
                    
                    first_avg = statistics.mean(first_half)
                    second_avg = statistics.mean(second_half)
                    
                    if first_avg != 0:
                        change_ratio = abs((second_avg - first_avg) / first_avg)
                        basic_stats["trend_confidence"] = min(change_ratio * 2, 1.0)
                    else:
                        basic_stats["trend_confidence"] = 0.0
                else:
                    basic_stats["trend_confidence"] = 0.0
            
            return basic_stats
            
        except Exception as e:
            logger.error("Failed to calculate basic statistics", error=str(e))
            return {"count": len(values), "mean": statistics.mean(values) if values else 0}
    
    def _detect_trend(self, time_series: List[Dict[str, Any]]) -> Tuple[TrendDirection, TrendStrength]:
        """檢測趨勢方向和強度"""
        
        if len(time_series) < 3:
            return TrendDirection.STABLE, TrendStrength.WEAK
        
        values = [point["value"] for point in time_series]
        
        try:
            # 使用線性回歸檢測趨勢
            if SCIPY_AVAILABLE:
                x = np.arange(len(values))
                y = np.array(values)
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                
                # 判斷趨勢方向
                if p_value < self.significance_level:  # 統計顯著
                    if slope > self.trend_threshold:
                        direction = TrendDirection.INCREASING
                    elif slope < -self.trend_threshold:
                        direction = TrendDirection.DECREASING
                    else:
                        direction = TrendDirection.STABLE
                else:
                    direction = TrendDirection.STABLE
                
                # 判斷趨勢強度
                r_squared = r_value ** 2
                if r_squared > 0.7:
                    strength = TrendStrength.STRONG
                elif r_squared > 0.3:
                    strength = TrendStrength.MODERATE
                else:
                    strength = TrendStrength.WEAK
                
            else:
                # 簡化的趨勢檢測
                first_third = values[:len(values)//3]
                last_third = values[-len(values)//3:]
                
                first_avg = statistics.mean(first_third)
                last_avg = statistics.mean(last_third)
                
                if first_avg == 0:
                    change_ratio = 0
                else:
                    change_ratio = (last_avg - first_avg) / first_avg
                
                # 判斷方向
                if change_ratio > self.trend_threshold:
                    direction = TrendDirection.INCREASING
                elif change_ratio < -self.trend_threshold:
                    direction = TrendDirection.DECREASING
                else:
                    direction = TrendDirection.STABLE
                
                # 判斷強度（基於變化幅度）
                abs_change = abs(change_ratio)
                if abs_change > 0.3:
                    strength = TrendStrength.STRONG
                elif abs_change > 0.1:
                    strength = TrendStrength.MODERATE
                else:
                    strength = TrendStrength.WEAK
            
            # 檢查是否為波動性趨勢
            if len(values) > 1:
                cv = statistics.stdev(values) / statistics.mean(values) if statistics.mean(values) != 0 else 0
                if cv > self.volatility_threshold and direction == TrendDirection.STABLE:
                    direction = TrendDirection.VOLATILE
            
            return direction, strength
            
        except Exception as e:
            logger.error("Failed to detect trend", error=str(e))
            return TrendDirection.STABLE, TrendStrength.WEAK
    
    def _calculate_change_rates(self, time_series: List[Dict[str, Any]]) -> Dict[str, float]:
        """計算變化率"""
        
        if len(time_series) < 2:
            return {"overall": 0.0, "average": 0.0, "volatility": 0.0}
        
        values = [point["value"] for point in time_series]
        
        try:
            # 總體變化率
            if values[0] != 0:
                overall_change = (values[-1] - values[0]) / values[0]
            else:
                overall_change = 0.0
            
            # 計算逐期變化率
            period_changes = []
            for i in range(1, len(values)):
                if values[i-1] != 0:
                    change = (values[i] - values[i-1]) / values[i-1]
                    period_changes.append(change)
            
            # 平均變化率
            average_change = statistics.mean(period_changes) if period_changes else 0.0
            
            # 波動性（變化率的標準差）
            volatility = statistics.stdev(period_changes) if len(period_changes) > 1 else 0.0
            
            return {
                "overall": overall_change,
                "average": average_change,
                "volatility": volatility,
                "period_changes": period_changes
            }
            
        except Exception as e:
            logger.error("Failed to calculate change rates", error=str(e))
            return {"overall": 0.0, "average": 0.0, "volatility": 0.0}
    
    def _detect_anomalies(self, time_series: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """檢測異常值"""
        
        if len(time_series) < 5:
            return []
        
        values = [point["value"] for point in time_series]
        anomalies = []
        
        try:
            # 使用 IQR 方法檢測異常值
            q1 = statistics.quantiles(values, n=4)[0]  # 第一四分位數
            q3 = statistics.quantiles(values, n=4)[2]  # 第三四分位數
            iqr = q3 - q1
            
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            for i, point in enumerate(time_series):
                value = point["value"]
                if value < lower_bound or value > upper_bound:
                    anomalies.append({
                        "index": i,
                        "date": point["date"],
                        "value": value,
                        "type": "outlier_high" if value > upper_bound else "outlier_low",
                        "severity": min(abs(value - statistics.median(values)) / statistics.stdev(values), 3.0) if len(values) > 1 else 0
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error("Failed to detect anomalies", error=str(e))
            return []
    
    def _simple_forecast(self, time_series: List[Dict[str, Any]], periods: int = 7) -> Dict[str, Any]:
        """簡單的趨勢預測"""
        
        if len(time_series) < 3:
            return {"error": "Insufficient data for forecasting"}
        
        values = [point["value"] for point in time_series]
        
        try:
            # 使用簡單移動平均和趨勢外推
            window_size = min(7, len(values) // 2)
            recent_values = values[-window_size:]
            recent_avg = statistics.mean(recent_values)
            
            # 計算趨勢斜率
            if len(values) > 1:
                first_half_avg = statistics.mean(values[:len(values)//2])
                second_half_avg = statistics.mean(values[len(values)//2:])
                trend_slope = (second_half_avg - first_half_avg) / (len(values) // 2)
            else:
                trend_slope = 0
            
            # 生成預測值
            forecasted_values = []
            for i in range(1, periods + 1):
                predicted_value = recent_avg + (trend_slope * i)
                forecasted_values.append(max(0, predicted_value))  # 確保非負值
            
            return {
                "method": "simple_trend_extrapolation",
                "periods": periods,
                "forecasted_values": forecasted_values,
                "confidence": "low",  # 簡單預測的信心度較低
                "base_value": recent_avg,
                "trend_slope": trend_slope
            }
            
        except Exception as e:
            logger.error("Failed to generate forecast", error=str(e))
            return {"error": f"Forecasting failed: {str(e)}"}
    
    def _generate_trend_insights(
        self, 
        time_series: List[Dict[str, Any]], 
        direction: TrendDirection, 
        strength: TrendStrength,
        change_rates: Dict[str, float],
        anomalies: List[Dict[str, Any]]
    ) -> List[str]:
        """生成趨勢洞察"""
        
        insights = []
        
        try:
            # 趨勢方向洞察
            if direction == TrendDirection.INCREASING:
                if strength == TrendStrength.STRONG:
                    insights.append("數據顯示強勢上升趨勢，增長動能強勁")
                else:
                    insights.append("數據呈現上升趨勢，但增長相對溫和")
            elif direction == TrendDirection.DECREASING:
                if strength == TrendStrength.STRONG:
                    insights.append("數據顯示明顯下降趨勢，需要關注潛在問題")
                else:
                    insights.append("數據呈現下降趨勢，建議監控後續變化")
            elif direction == TrendDirection.VOLATILE:
                insights.append("數據波動較大，建議分析波動原因")
            else:
                insights.append("數據保持相對穩定")
            
            # 變化率洞察
            overall_change = change_rates.get("overall", 0)
            if abs(overall_change) > 0.2:
                change_direction = "增長" if overall_change > 0 else "下降"
                insights.append(f"整體期間{change_direction}幅度為 {abs(overall_change):.1%}")
            
            # 波動性洞察
            volatility = change_rates.get("volatility", 0)
            if volatility > 0.3:
                insights.append("數據波動性較高，建議關注穩定性")
            elif volatility < 0.1:
                insights.append("數據變化相對穩定")
            
            # 異常值洞察
            if anomalies:
                high_anomalies = [a for a in anomalies if a["type"] == "outlier_high"]
                low_anomalies = [a for a in anomalies if a["type"] == "outlier_low"]
                
                if high_anomalies:
                    insights.append(f"檢測到 {len(high_anomalies)} 個異常高值")
                if low_anomalies:
                    insights.append(f"檢測到 {len(low_anomalies)} 個異常低值")
            
            # 數據質量洞察
            if len(time_series) < 7:
                insights.append("數據點較少，建議收集更多數據以提高分析準確性")
            
            return insights
            
        except Exception as e:
            logger.error("Failed to generate insights", error=str(e))
            return ["趨勢分析完成，但洞察生成遇到問題"]
    
    def _empty_trend_result(self) -> Dict[str, Any]:
        """空數據的趨勢結果"""
        return {
            "error": True,
            "message": "No data available for trend analysis",
            "trend": {
                "direction": TrendDirection.STABLE.value,
                "strength": TrendStrength.WEAK.value,
                "confidence": 0.0
            }
        }
    
    def _insufficient_data_result(self) -> Dict[str, Any]:
        """數據不足的趨勢結果"""
        return {
            "error": True,
            "message": "Insufficient data points for reliable trend analysis (minimum 3 required)",
            "trend": {
                "direction": TrendDirection.STABLE.value,
                "strength": TrendStrength.WEAK.value,
                "confidence": 0.0
            }
        } 