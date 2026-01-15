# AI Agent Learning

基于 FastAPI 的 AI Agent 学习项目，集成火山引擎豆包模型（doubao-lite-128k）。

## 项目结构

```
learning-agent/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理（环境变量、模型配置）
│   ├── models/
│   │   ├── __init__.py
│   │   └── llm_client.py    # LLM 客户端抽象层（支持模型切换）
│   └── api/
│       ├── __init__.py
│       └── chat.py          # 对话 API 端点
├── requirements.txt         # Python 依赖
├── .env.example            # 环境变量示例
├── .gitignore
└── README.md               # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件（参考 `.env.example`）：

```env
# 火山引擎 API 配置
DOUBAO_API_KEY=your_api_key_here
DOUBAO_API_ENDPOINT=https://ark.cn-beijing.volces.com/api/v3/chat/completions
DOUBAO_MODEL_NAME=doubao-lite-128k

# FastAPI 配置
API_HOST=0.0.0.0
API_PORT=8000
```

### 3. 运行应用

```bash
# 方式1：使用 uvicorn 直接运行
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 方式2：使用 Python 运行
python -m app.main
```

### 4. 访问 API 文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 使用示例

### 标准对话接口

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ],
    "temperature": 0.7
  }'
```

### 简化对话接口

```bash
curl -X POST "http://localhost:8000/chat/simple?message=你好"
```

## 核心设计

### 1. 配置管理

使用 `pydantic-settings` 管理环境变量，支持从 `.env` 文件加载配置。

### 2. LLM 客户端抽象层

- `BaseLLMClient`: 抽象基类，定义统一的接口
- `DoubaoClient`: 火山引擎豆包模型的具体实现
- 支持未来扩展其他模型（OpenAI、Claude 等）

### 3. 可扩展架构

- 模块化设计，便于添加新功能
- 抽象层设计，支持模型切换
- 清晰的代码结构，便于学习和扩展

## 未来扩展方向

- [ ] 添加对话历史管理
- [ ] 实现工具调用（Function Calling）
- [ ] 添加 Agent 规划能力
- [ ] 支持多模型切换
- [ ] 添加流式响应支持
- [ ] 实现记忆管理
- [ ] 添加向量数据库支持

## 技术栈

- **FastAPI**: 现代、快速的 Web 框架
- **httpx**: 异步 HTTP 客户端
- **pydantic**: 数据验证和设置管理
- **uvicorn**: ASGI 服务器

## 学习资源

这是一个学习 AI Agent 开发的基础框架，你可以在此基础上：

1. 学习 FastAPI 的使用
2. 理解 LLM API 的调用方式
3. 学习抽象层设计模式
4. 逐步添加 Agent 功能（记忆、工具调用、规划等）

## 许可证

MIT
