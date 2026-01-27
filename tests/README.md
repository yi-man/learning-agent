# 测试说明

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定文件
pytest tests/test_config.py

# 运行并显示覆盖率
pytest --cov=app --cov-report=html

# 运行并显示详细输出
pytest -v
```

## 测试结构

测试目录结构镜像应用目录结构，便于定位和维护。
