# GA+ 真實 GA4 測試指南

> 📅 更新日期：2025-01-24  
> 🎯 目標：協助用戶設置真實的 Google Analytics 4 測試環境  

## 📋 概覽

第一階段完成後，GA+ 系統已具備完整的 GA4 整合能力。您現在可以連接真實的 Google Analytics 4 屬性來測試系統功能。

## ✅ 系統就緒狀態

### 🎯 已完成的功能
- ✅ **GA4 Data API 整合** - 完整的查詢引擎
- ✅ **7種查詢類型支援** - 涵蓋基本指標到複雜分析
- ✅ **智能查詢解析** - 自然語言轉 GA4 查詢
- ✅ **錯誤處理機制** - 完善的異常處理
- ✅ **模擬/真實模式切換** - 靈活的測試環境

### 🔧 技術架構
- **GA4 服務層** (`app/services/ga4_service.py`)
- **查詢解析器** (`app/services/query_parser.py`)
- **配置管理** (`app/core/config.py`)
- **依賴注入** (`app/core/dependencies.py`)

## 🚀 快速開始

### 步驟 1: 運行設置腳本

```bash
python scripts/setup_real_ga4_testing.py
```

這個腳本將：
1. 檢查當前配置
2. 收集您的 GA4 信息
3. 更新環境配置
4. 測試連接
5. 創建專用測試腳本

### 步驟 2: 準備 GA4 信息

您需要準備：
- **GA4 屬性ID** (例如: 123456789)
- **Google Cloud 服務帳戶憑證** (JSON 文件)
- **GA4 屬性的查看權限**

## 📊 GA4 設置詳細步驟

### 1. 創建 Google Cloud 服務帳戶

1. 前往 [Google Cloud Console](https://console.cloud.google.com)
2. 選擇或創建專案
3. 導航到 **IAM & Admin** > **Service Accounts**
4. 點擊 **Create Service Account**
5. 填寫服務帳戶詳細信息
6. 下載 JSON 憑證文件

### 2. 啟用必要的 API

在 Google Cloud Console 中啟用：
- **Google Analytics Data API**
- **Google Analytics Admin API** (可選)

### 3. 設置 GA4 權限

1. 前往 [Google Analytics](https://analytics.google.com)
2. 選擇您的 GA4 屬性
3. 點擊 **Admin** (管理)
4. 在屬性列中選擇 **Property Access Management**
5. 添加服務帳戶電子郵件
6. 設置為 **Viewer** 角色

### 4. 獲取 GA4 屬性ID

1. 在 Google Analytics 中點擊 **Admin**
2. 選擇 **Property Settings**
3. 複製 **Property ID**

## 🔧 環境配置

### 自動配置 (推薦)

使用設置腳本自動配置：

```bash
python scripts/setup_real_ga4_testing.py
```

### 手動配置

編輯 `.env` 文件：

```env
# GA4 配置
USE_MOCK_GA4_API=false
GA4_PROPERTY_ID=你的屬性ID
GOOGLE_APPLICATION_CREDENTIALS=憑證文件路徑.json

# 其他配置保持不變
USE_MOCK_LLM_API=false
OPENAI_API_KEY=你的OpenAI密鑰
```

## 🧪 測試步驟

### 1. 連接測試

重新啟動服務器並檢查日誌：

```bash
# 停止現有服務器
taskkill /f /im python.exe 2>$null

# 啟動服務器
python scripts/run_dev_server.py
```

確認看到：
```
📊 LLM API: 真實模式 (OpenAI)
📈 GA4 API: 真實模式  # 應該顯示真實模式
```

### 2. API 測試

運行自動生成的測試腳本：

```bash
python scripts/test_real_ga4_api.py
```

### 3. 聊天介面測試

通過聊天 API 測試：

```bash
# PowerShell
$body = @{
    message = "過去30天我的網站有多少訪客？"
    property_id = "你的GA4屬性ID"
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/chat/" -Method POST -Body $body -ContentType "application/json"
```

## 📊 支援的查詢類型

### 基本指標查詢
- "過去30天有多少訪客？"
- "今天的會話數是多少？"
- "頁面瀏覽量如何？"

### 頁面分析查詢
- "最熱門的頁面是什麼？"
- "哪些頁面跳出率最高？"
- "頁面表現如何？"

### 流量來源分析
- "主要流量來源有哪些？"
- "搜尋引擎帶來多少流量？"
- "社群媒體表現如何？"

### 用戶行為分析
- "用戶停留時間多長？"
- "平均會話深度是多少？"
- "用戶參與度如何？"

### 轉換分析
- "轉換率是多少？"
- "有多少轉換事件？"
- "收入情況如何？"

### 趨勢分析
- "過去90天的趨勢如何？"
- "流量變化趨勢是什麼？"
- "用戶增長情況如何？"

### 比較分析
- "與上個月相比如何？"
- "今年與去年同期比較？"
- "不同時期的表現差異？"

## 🔍 故障排除

### 常見問題

#### 1. 連接失敗
**症狀**: `GA4 query failed` 或連接超時
**解決方案**:
- 檢查網路連接
- 驗證憑證文件路徑
- 確認 GA4 屬性ID 正確

#### 2. 權限錯誤
**症狀**: `Permission denied` 或 `Access forbidden`
**解決方案**:
- 確認服務帳戶已添加到 GA4 屬性
- 檢查權限角色 (至少需要 Viewer)
- 重新下載憑證文件

#### 3. API 配額限制
**症狀**: `Quota exceeded` 或 `Rate limit`
**解決方案**:
- 等待配額重置
- 減少查詢頻率
- 考慮升級 GA4 配額

#### 4. 數據不匹配
**症狀**: 返回的數據與 GA4 介面不符
**解決方案**:
- 檢查時區設置
- 確認數據處理延遲
- 驗證查詢參數

### 除錯模式

啟用詳細日誌：

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

查看 GA4 查詢詳細信息：

```python
# 在 ga4_service.py 中
logger.debug("GA4 request details", request=request)
```

## 📈 性能優化

### 查詢優化建議

1. **限制日期範圍** - 避免查詢過長的時間段
2. **使用適當的指標** - 只查詢需要的指標
3. **設置合理的 limit** - 控制返回的數據量
4. **快取常用查詢** - 避免重複查詢

### 監控指標

關注以下性能指標：
- **查詢回應時間** - 目標 < 3秒
- **API 錯誤率** - 目標 < 1%
- **查詢成功率** - 目標 > 95%

## 🎯 下一步

### 進階功能測試

1. **複雜查詢** - 測試多維度分析
2. **自定義指標** - 使用您的特定事件
3. **區段分析** - 測試用戶區段功能
4. **實時數據** - 測試實時報告

### 整合測試

1. **完整工作流程** - 從查詢到回應的完整測試
2. **錯誤處理** - 測試各種異常情況
3. **性能測試** - 測試高並發查詢
4. **用戶體驗** - 測試實際使用場景

## 📞 支援

如果遇到問題：

1. **檢查日誌** - 查看詳細錯誤信息
2. **參考文檔** - 查閱 Google Analytics Data API 文檔
3. **社群支援** - 搜尋相關問題解決方案
4. **技術支援** - 聯繫開發團隊

---

**恭喜！** 🎉 您現在可以使用真實的 GA4 數據測試 GA+ 系統了！

> 💡 **提示**: 建議先用測試屬性進行初步測試，確認一切正常後再連接生產環境的 GA4 屬性。 