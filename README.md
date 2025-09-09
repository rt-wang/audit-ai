# 岗位条件审核代理

基于通义千问大模型的智能招聘条件审核系统，自动解析岗位要求并对候选人信息进行逐条比对审核。

## 🚀 快速开始

```bash
# 设置API密钥
export DASHSCOPE_API_KEY=your_qwen_api_key

# 测试命令行版本
python agent.py

# 启动HTTP API服务
PORT=8080 uv run python app.py
```

## 💻 使用方式

### Python调用
```python
from agent import evaluate

candidate = {
    "name": "张三",
    "birthdate": "1995-06-15", 
    "education": "本科",
    "major": "计算机科学与技术",
    "political_status": "共产党员"
}

summary, result = evaluate(candidate, "年龄30岁以下，本科学历，计算机专业，党员")
print(result["verdict"])  # 通过/未通过/待核验
```

### HTTP API调用
```bash
# 候选人审核
curl -X POST http://localhost:8080/audit \
  -H 'Content-Type: application/json' \
  -d '{
    "candidate": {"name": "张三", "birthdate": "1995-06-15", "education": "本科", "major": "计算机科学与技术"},
    "job_requirements": "年龄30岁以下，本科学历，计算机专业"
  }'

# 专业匹配
curl -X POST http://localhost:8080/major/match \
  -H 'Content-Type: application/json' \
  -d '{"major": "计算机科学与技术", "allowed_categories": ["计算机类"]}'
```

## 🔧 安装配置

```bash
# 安装依赖
pip install -r requirements.txt

# 专业映射表已包含(majors.xlsx)，包含51个专业大类映射
```

## 📋 API接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/audit` | POST | 候选人审核 |
| `/major/match` | POST | 专业匹配 |

## ✨ 核心特性

- **智能解析**: 直接处理自然语言JD，无需预处理
- **专业匹配**: Excel映射表支持专业大类匹配
- **严格审核**: 明确从严、模糊从谨的审核策略
- **合规检查**: 自动识别歧视性条件风险
- **完整输出**: 中文摘要 + 结构化JSON结果

## 📄 输出格式

```json
{
  "success": true,
  "data": {
    "summary": "结论：通过\n关键理由：年龄符合要求...",
    "result": {
      "verdict": "通过",
      "criteria": [{"name": "年龄", "match": "Yes", "rationale": "..."}],
      "missing_data": [],
      "policy_flags": []
    }
  }
}
```

