# GA+ 快速開始指南

> 🚀 5分鐘內啟動 GA+ 開發環境

## 📋 前置需求

- Python 3.11+
- Git
- Docker (可選，用於容器化部署)

## 🛠️ 安裝步驟

### 1. 克隆專案

```bash
git clone https://github.com/stevechen1112/GA-.git
cd GA+
```

### 2. 安裝依賴項目

```bash
pip install -r requirements.txt
```

### 3. 設置環境變數

```bash
# 創建環境變數文件
python scripts/start_dev.py --create-env

# 編輯 .env 文件，設置您的 API 金鑰
# 至少需要設置：
# - OPENAI_API_KEY
# - GA4_PROPERTY_ID (可選，開發時使用模擬數據)
```

### 4. 啟動開發服務器

```bash
# 方式一：直接啟動
python scripts/start_dev.py

# 方式二：使用 Docker
python scripts/start_dev.py --docker

# 方式三：手動啟動
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 測試 API

```bash
# 運行 API 測試
python scripts/test_api.py

# 或訪問 Swagger 文檔
# http://localhost:8000/docs
```

## 🎯 快速測試

### 測試聊天功能

```bash
curl -X POST "http://localhost:8000/api/v1/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "昨天有多少訪客？",
    "property_id": "test_property",
    "date_range": "last_30_days"
  }'
```

### 測試健康檢查

```bash
curl http://localhost:8000/health
```

### 查看支援的查詢類型

```bash
curl http://localhost:8000/api/v1/chat/supported-queries
```

## 📊 API 端點概覽

| 端點 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 應用程式資訊 |
| `/health` | GET | 健康檢查 |
| `/api/v1/status` | GET | API 狀態 |
| `/api/v1/chat/` | POST | 聊天對話 |
| `/api/v1/chat/supported-queries` | GET | 支援的查詢類型 |
| `/api/v1/analytics/properties` | GET | GA4 屬性列表 |
| `/api/v1/analytics/metrics` | GET | 可用指標 |
| `/api/v1/analytics/dimensions` | GET | 可用維度 |
| `/api/v1/users/register` | POST | 用戶註冊 |
| `/api/v1/users/login` | POST | 用戶登入 |

## 🔧 開發模式

### 環境變數配置

開發模式下，以下設置會啟用模擬數據：

```env
USE_MOCK_GA4_API=true
USE_MOCK_LLM_API=false  # 需要真實的 OpenAI API 金鑰
```

### 日誌配置

```env
LOG_LEVEL=INFO
LOG_FORMAT=json  # 或 "console" 用於開發
```

### 調試模式

```env
DEBUG=true
ENVIRONMENT=development
```

## 🐳 Docker 部署

### 使用 Docker Compose

```bash
# 啟動所有服務
docker-compose up -d

# 查看日誌
docker-compose logs -f app

# 停止服務
docker-compose down
```

### 單獨構建應用程式

```bash
# 構建映像
docker build -t ga-plus .

# 運行容器
docker run -p 8000:8000 ga-plus
```

## 📝 開發工作流程

### 1. 功能開發

```bash
# 創建新分支
git checkout -b feature/new-feature

# 開發功能
# ...

# 提交變更
git add .
git commit -m "feat: 添加新功能"

# 推送分支
git push origin feature/new-feature
```

### 2. 測試

```bash
# 運行 API 測試
python scripts/test_api.py

# 運行單元測試 (待實現)
# pytest tests/

# 運行整合測試 (待實現)
# pytest tests/integration/
```

### 3. 代碼品質

```bash
# 格式化代碼 (待實現)
# black app/
# isort app/

# 檢查代碼品質 (待實現)
# flake8 app/
# mypy app/
```

## 🚨 常見問題

### Q: 啟動時出現模組找不到錯誤

**A:** 確保已安裝所有依賴項目：
```bash
pip install -r requirements.txt
```

### Q: OpenAI API 錯誤

**A:** 檢查 API 金鑰是否正確設置：
```bash
echo $OPENAI_API_KEY
```

### Q: GA4 連接失敗

**A:** 開發模式下使用模擬數據，設置：
```env
USE_MOCK_GA4_API=true
```

### Q: 端口被佔用

**A:** 更改端口或停止佔用端口的服務：
```bash
uvicorn app.main:app --port 8001
```

## 📚 下一步

1. **閱讀文檔**: 查看 `README.md` 了解完整功能
2. **探索 API**: 訪問 `http://localhost:8000/docs`
3. **查看進度**: 查看 `DEVELOPMENT_PROGRESS.md`
4. **貢獻代碼**: 查看開發指南和代碼規範

## 🆘 需要幫助？

- 📖 查看 [README.md](README.md) 完整文檔
- 🐛 報告問題: [GitHub Issues](https://github.com/stevechen1112/GA-/issues)
- 💬 討論功能: [GitHub Discussions](https://github.com/stevechen1112/GA-/discussions)

---

🎉 **恭喜！您已成功啟動 GA+ 開發環境！** 