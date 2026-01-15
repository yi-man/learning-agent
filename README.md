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
├── venv/                    # Python 虚拟环境（运行 setup.sh 后生成）
├── requirements.txt         # Python 依赖
├── env.example              # 环境变量示例
├── setup.sh                 # 项目初始化脚本（macOS/Linux）
├── run.sh                   # 应用启动脚本（macOS/Linux）
├── .gitignore
└── README.md                # 项目说明
```

## 快速开始

### 方式一：使用自动化脚本（推荐）

**macOS/Linux:**

```bash
# 1. 初始化项目（创建虚拟环境并安装依赖）
./setup.sh

# 2. 配置环境变量（编辑 .env 文件，填入 API Key）
# 编辑 .env 文件

# 3. 启动应用
./run.sh
```

### 方式二：手动设置

#### 1. 创建虚拟环境

```bash
# 创建 venv 虚拟环境
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件（参考 `.env.example`）：

```env
# 火山引擎 API 配置
DOUBAO_API_KEY=your_api_key_here
DOUBAO_API_ENDPOINT=https://ark.cn-beijing.volces.com/api/v3/chat/completions
DOUBAO_MODEL_NAME=doubao-seed-1-6-lite-251015

# FastAPI 配置
API_HOST=0.0.0.0
API_PORT=8000
```

**注意：** 模型名称 `doubao-seed-1-6-lite-251015` 是示例，请根据你在火山引擎控制台实际可用的模型名称进行配置。

### 4. 运行应用

**重要：运行前必须先激活虚拟环境！**

```bash
# 激活虚拟环境（如果还没激活）
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 方式1：使用 uvicorn 直接运行
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 方式2：使用 Python 运行
python -m app.main
```

**或者使用启动脚本（自动激活虚拟环境）：**

```bash
./run.sh  # macOS/Linux
```

### 5. 访问 API 文档

启动后访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 使用示例

### 标准对话接口

**基础文本对话：**

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ],
    "temperature": 0.7,
    "max_completion_tokens": 2000
  }'
```

**多模态对话（图片+文本）：**

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "image_url",
            "image_url": {
              "url": "https://example.com/image.jpg"
            }
          },
          {
            "type": "text",
            "text": "图片主要讲了什么?"
          }
        ]
      }
    ],
    "max_completion_tokens": 65535,
    "reasoning_effort": "medium"
  }'
```

### 简化对话接口

```bash
curl -X POST "http://localhost:8000/chat/simple?message=你好"
```

### API 参数说明

- `messages`: 消息列表，支持文本或多模态内容
- `temperature`: 温度参数，控制随机性（0.0-2.0）
- `max_completion_tokens`: 最大完成 token 数（火山引擎 API 参数）
- `max_tokens`: 兼容参数，会自动转换为 `max_completion_tokens`
- `reasoning_effort`: 推理努力程度，可选值：`low`, `medium`, `high`
- `stream`: 是否流式返回

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

## 故障排除

### ModuleNotFoundError: No module named 'pydantic_settings'

**原因：** 运行应用时没有激活虚拟环境，或者使用了系统 Python 而不是虚拟环境中的 Python。

**解决方法：**

```bash
# 确保激活虚拟环境
source venv/bin/activate  # macOS/Linux

# 然后运行应用
uvicorn app.main:app --reload
# 或使用启动脚本
./run.sh
```

### 安装依赖失败（pydantic-core 编译错误）

**原因：** Python 版本过新（如 Python 3.14），缺少预编译的 wheel 包。

**解决方法：**

1. 使用 Python 3.11 或 3.12（推荐）
2. 或者安装 Rust 工具链来编译 pydantic-core
3. 或者等待更新的 pydantic 版本支持你的 Python 版本

### 如何检查虚拟环境是否激活

激活虚拟环境后，命令行提示符前会显示 `(venv)`：

```bash
(venv) user@host:~/learning-agent$
```

如果没有看到 `(venv)`，说明虚拟环境未激活。

## 学习资源

这是一个学习 AI Agent 开发的基础框架，你可以在此基础上：

1. 学习 FastAPI 的使用
2. 理解 LLM API 的调用方式
3. 学习抽象层设计模式
4. 逐步添加 Agent 功能（记忆、工具调用、规划等）

## 许可证

MIT
