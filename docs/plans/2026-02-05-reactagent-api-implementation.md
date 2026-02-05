# ReAct JSON API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `/agents/react` 新增 JSON ReAct 端点，复用 `OpenAIClient`，支持受控工具调用与可选 trace。

**Architecture:** 新增 ReAct 运行器与工具注册模块，路由层负责参数解析与历史管理；ReAct 执行循环由运行器模块处理，工具调用通过白名单执行器完成。

**Tech Stack:** FastAPI, Pydantic, OpenAI SDK, pytest

---

### Task 1: 新增 API 测试覆盖

**Files:**
- Create: `tests/api/test_agents_react.py`

**Step 1: Write the failing test**
```python
def test_agents_react_generates_session_id(client):
    payload = {
        "messages": [{"role": "user", "content": "2+2?"}],
        "return_trace": False,
    }
    resp = client.post("/agents/react", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"]
    assert body["content"]
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/api/test_agents_react.py::test_agents_react_generates_session_id -v`
Expected: FAIL (route not found or response missing fields).

**Step 3: Write minimal implementation**
Add stub endpoint returning expected shape (content/session_id/model).

**Step 4: Run test to verify it passes**
Run: `pytest tests/api/test_agents_react.py::test_agents_react_generates_session_id -v`
Expected: PASS

**Step 5: Commit**
```bash
git add tests/api/test_agents_react.py app/api/agents_react.py
git commit -m "feat: add agents react api stub"
```

---

### Task 2: ReAct JSON 执行器与工具白名单

**Files:**
- Create: `app/agents/react_agent.py`
- Create: `app/agents/tools.py`
- Modify: `app/api/agents_react.py`

**Step 1: Write the failing test**
```python
def test_agents_react_returns_trace_when_enabled(client):
    payload = {
        "messages": [{"role": "user", "content": "2+2?"}],
        "return_trace": True,
    }
    resp = client.post("/agents/react", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "trace" in body
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/api/test_agents_react.py::test_agents_react_returns_trace_when_enabled -v`
Expected: FAIL (no trace).

**Step 3: Write minimal implementation**
Implement ReAct JSON loop (parse → tool_call → finish) with工具白名单，返回 trace。

**Step 4: Run test to verify it passes**
Run: `pytest tests/api/test_agents_react.py::test_agents_react_returns_trace_when_enabled -v`
Expected: PASS

**Step 5: Commit**
```bash
git add app/agents/react_agent.py app/agents/tools.py app/api/agents_react.py tests/api/test_agents_react.py
git commit -m "feat: implement react json runner"
```

---

### Task 3: 路由注册与历史集成

**Files:**
- Modify: `app/main.py`
- Modify: `app/api/agents_react.py`

**Step 1: Write the failing test**
```python
def test_agents_react_uses_history(client):
    first = client.post(
        "/agents/react",
        json={"messages": [{"role": "user", "content": "first"}]},
    ).json()
    session_id = first["session_id"]
    second = client.post(
        "/agents/react",
        json={"session_id": session_id, "messages": [{"role": "user", "content": "second"}]},
    )
    assert second.status_code == 200
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/api/test_agents_react.py::test_agents_react_uses_history -v`
Expected: FAIL (history not applied / route not registered).

**Step 3: Write minimal implementation**
接入 `merge_history_and_messages` 与 `add_message`，并在 `app/main.py` 注册路由。

**Step 4: Run test to verify it passes**
Run: `pytest tests/api/test_agents_react.py::test_agents_react_uses_history -v`
Expected: PASS

**Step 5: Commit**
```bash
git add app/main.py app/api/agents_react.py tests/api/test_agents_react.py
git commit -m "feat: integrate react api history"
```

---

### Task 4: 全量测试

**Files:**
- Test: `tests/`

**Step 1: Run test suite**
Run: `pytest -v`
Expected: PASS

**Step 2: Commit**
```bash
git add .
git commit -m "test: verify react api"
```
