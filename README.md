# GA+ - Google Analytics 4 對話式AI分析平台

> 讓GA4像聊天一樣簡單，10分鐘獲得原本需要1小時的洞察

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)

## 🎯 專案概述

GA+ 是一個創新的SaaS產品，讓用戶可以用自然語言與Google Analytics 4數據對話，獲得智能洞察和建議。我們的目標是將GA4從複雜的專業工具轉化為人人可用的對話式分析平台。

### 產品特色

- 🗣️ **自然語言查詢**：用中文對話方式查詢GA4數據
- 🧠 **智能洞察**：AI驅動的異常檢測和根因分析
- ⚡ **即時回應**：平均查詢響應時間 <2秒
- 📊 **多維分析**：趨勢分析、比較分析、關聯分析
- 🔄 **智能路由**：GA4 API + BigQuery 無縫切換
- 🏢 **企業級**：多用戶權限管理和安全控制

## 🏗️ 技術架構

```
[用戶介面] ↔ [API Gateway] ↔ [對話服務] 
                                    ↓
[LLM整合層] ↔ [意圖識別] ↔ [查詢生成器]
    ↓                           ↓
[向量資料庫] ←→ [GA4/BigQuery路由器] ↔ [數據服務層]
                                    ↓
[快取層Redis] ←→ [GA4 API] + [BigQuery] + [數據庫]
```

### 核心技術棧

**後端框架**
- Python 3.11 + FastAPI
- PostgreSQL (用戶數據) + Redis (快取)
- Docker容器化部署

**AI/ML組件**
- OpenAI GPT-4o 或 Claude 3.5 Sonnet
- Weaviate向量資料庫 (語義搜尋)
- 自研異常檢測算法

**數據整合**
- Google Analytics Data API v1
- Google BigQuery API
- 智能路由器 (GA4 API ↔ BigQuery)

**基礎設施**
- AWS ECS 或 Google Cloud Run
- AWS RDS/CloudSQL + Redis Cache
- CloudWatch/Cloud Monitoring

## 🚀 快速開始

### 環境需求

- Python 3.11+
- Node.js 18+ (前端開發)
- Docker & Docker Compose
- Google Cloud Platform 帳號
- OpenAI API 金鑰

### 安裝步驟

1. **克隆專案**
```bash
git clone https://github.com/stevechen1112/GA-.git
cd GA-
```

2. **設置環境變數**
```bash
cp .env.example .env
# 編輯 .env 文件，填入必要的API金鑰和配置
```

3. **啟動開發環境**
```bash
# 使用 Docker Compose 啟動所有服務
docker-compose up -d

# 或者手動啟動
pip install -r requirements.txt
uvicorn app.main:app --reload
```

4. **初始化資料庫**
```bash
python scripts/init_db.py
```

5. **訪問應用**
- 前端介面: http://localhost:3000
- API文檔: http://localhost:8000/docs
- 管理後台: http://localhost:8000/admin

## 📋 功能特色

### 🎯 核心功能 (已實現)

1. **基礎數據查詢**
   - 支援10+種常見查詢類型
   - 自然語言意圖識別
   - 即時數據回應

2. **趨勢分析與比較**
   - 多維度數據分析
   - 時間序列比較
   - 排名和關聯分析

3. **智能洞察與建議**
   - 異常檢測和預警
   - 根因分析引擎
   - 個性化行動建議

### 🔮 未來擴展功能

4. **預測分析與策略建議**
   - 未來趨勢預測
   - ROI優化建議
   - 策略規劃輔助

5. **主動監控與自動化決策**
   - 即時警報系統
   - 自動報告生成
   - 智能決策支援

## 💰 定價方案

| 方案 | 價格 | 查詢次數 | 功能 |
|------|------|----------|------|
| **起步版** | $39/月 | 1,000次 | 基礎分析功能 |
| **成長版** | $129/月 | 10,000次 | 趨勢分析 + 異常檢測 |
| **企業版** | $399/月 | 無限制 | 完整功能 + 專屬支援 |

## 🛠️ 開發指南

### 專案結構

```
GA+/
├── app/                    # 後端應用程式
│   ├── api/               # API路由
│   ├── core/              # 核心配置
│   ├── models/            # 數據模型
│   ├── services/          # 業務邏輯
│   └── utils/             # 工具函數
├── frontend/              # 前端應用程式
├── docs/                  # 文檔
├── scripts/               # 部署腳本
├── tests/                 # 測試文件
└── docker-compose.yml     # Docker配置
```

### 開發流程

1. **功能開發**：基於功能分支開發
2. **代碼審查**：所有PR需要代碼審查
3. **自動化測試**：CI/CD自動運行測試
4. **部署流程**：通過GitHub Actions自動部署

### 貢獻指南

1. Fork 專案
2. 創建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 📊 專案狀態

- **當前版本**: v0.1.0 (MVP階段)
- **開發進度**: 第一階段 - MVP基礎版開發中
- **團隊規模**: 6人核心團隊
- **預計發布**: 2024年Q2

## 📈 里程碑

- [x] 專案啟動和團隊組建
- [x] 技術架構設計完成
- [ ] MVP版本開發 (週1-6)
- [ ] 智能分析版本 (週7-12)
- [ ] 企業智能版本 (週13-18)

## 🤝 團隊

- **產品經理/技術主管**: 產品規劃、技術決策
- **AI/ML工程師**: LLM整合、異常檢測算法
- **數據工程師**: GA4/BigQuery整合、數據管道
- **後端工程師**: API開發、系統架構
- **前端工程師**: 用戶介面、對話體驗
- **DevOps工程師**: 部署自動化、監控

## 📞 聯絡方式

- **專案維護者**: [stevechen1112](https://github.com/stevechen1112)
- **問題回報**: [GitHub Issues](https://github.com/stevechen1112/GA-/issues)
- **功能建議**: [GitHub Discussions](https://github.com/stevechen1112/GA-/discussions)

## 📄 授權

本專案採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 文件

## 🙏 致謝

感謝所有貢獻者和支持者，讓這個專案得以實現。

---

**讓GA4分析變得像聊天一樣簡單！** 🚀 