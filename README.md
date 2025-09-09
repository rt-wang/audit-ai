# 岗位条件审核代理

基于通义千问大模型的智能招聘条件审核系统，能够自动解析岗位要求并对候选人信息进行逐条比对审核。

## 🚀 快速开始

### 环境设置
```bash
# 设置API密钥
export DASHSCOPE_API_KEY=your_qwen_api_key

# 激活虚拟环境（如使用uv）
source .venv/bin/activate
```

### 快速测试
```bash
# 运行内置示例
python agent.py
```

### 程序化调用
```python
from agent import evaluate

# 候选人信息
candidate = {
    "name": "张三",
    "birthdate": "1995-06-15",
    "education": "本科",
    "degree": "学士",
    "major": "计算机科学与技术",
    "political_status": "共产党员"
}

# 岗位要求
jd_text = """
岗位要求：
1. 年龄30岁以下
2. 本科及以上学历，学士及以上学位
3. 专业：计算机科学与技术、软件工程、信息安全
4. 政治面貌：中共党员或共青团员
"""

# 执行审核
summary, result_json = evaluate(candidate, jd_text)
print("审核摘要:", summary)
print("详细结果:", result_json["verdict"])
```

### HTTP API 调用
```bash
# 启动HTTP服务
python app.py

# local test
PORT=8080 uv run python app.py &

# 单个候选人审核
curl -X POST http://localhost:8080/audit \
  -H 'Content-Type: application/json' \
  -d '{
    "candidate": {
      "name": "张三",
      "birthdate": "1995-06-15",
      "education": "本科",
      "degree": "学士",
      "major": "计算机科学与技术",
      "political_status": "共产党员"
    },
    "job_requirements": "年龄30岁以下，本科学历，计算机专业，党员"
  }'


# 专业匹配
curl -X POST http://localhost:5000/major/match \
  -H 'Content-Type: application/json' \
  -d '{
    "major": "计算机科学与技术",
    "allowed_categories": ["计算机类"]
  }'
```

## 功能特性

- **智能解析**：自动从自然语言JD中提取年龄、学历、专业等关键要求
- **专业匹配**：基于Excel映射表进行专业大类匹配，支持同义词和规范化
- **严格审核**：明确从严、模糊从谨的审核策略
- **合规检查**：自动识别潜在歧视性条件并提示合规风险
- **多重回退**：xlwings → xlcalculator → 纯Python的渐进式Excel处理

## 环境要求

- Python 3.8+
- 通义千问API密钥
- Excel（可选，用于xlwings）

## 安装配置

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 设置环境变量：
```bash
export DASHSCOPE_API_KEY=your_qwen_api_key
```

3. 准备专业映射表：
创建 `majors.xlsx` 文件，包含 `map` 工作表，格式如下：

| A列(子专业) | B列(大类) | C列(同义规范名，可选) |
|------------|----------|---------------------|
| 计算机科学与技术 | 计算机类 | 计算机科学 |
| 软件工程 | 计算机类 | 软件开发 |
| 生物学（古生物学方向） | 学科教学（生物） | 生物学 |
| 中国语言文学 | 中国语言文学类 | 中文 |

## 使用方法

### 基本使用

```python
from agent import evaluate

candidate = {
    "name": "张三",
    "birthdate": "1995-06-15",
    "education": "本科",
    "degree": "学士", 
    "major": "计算机科学与技术",
    "political_status": "共产党员"
}

jd_text = """
岗位要求：
1. 年龄30岁以下
2. 本科及以上学历，学士及以上学位
3. 专业：计算机科学与技术、软件工程、信息安全
4. 政治面貌：中共党员或共青团员
"""

summary, result_json = evaluate(candidate, jd_text)
print(summary)
print(result_json)
```

### 运行示例

```bash
python agent.py
```

## 输出格式

### 摘要示例
```
结论：通过
年龄：候选人29岁，符合30岁以下要求
学历：本科学历符合要求
专业：计算机科学与技术在允许范围内
政治面貌：共产党员符合要求
```

### JSON结果示例
```json
{
  "verdict": "通过",
  "derived_fields": {
    "candidate_age": "29",
    "age_cutoff": {"op": "on_or_before", "date": "1994-12-01"},
    "normalized_major": "计算机科学与技术"
  },
  "criteria": [
    {
      "name": "年龄",
      "job_requirement": "30岁以下",
      "candidate_evidence": "年龄29岁",
      "match": "Yes",
      "rationale": "候选人29岁，要求30岁及以下"
    }
  ],
  "missing_data": [],
  "policy_flags": []
}
```

## 核心组件

### 专业匹配
- `excel_match_major(candidate_major)`: 查找专业对应的大类
- `is_major_acceptable(candidate_major, jd_categories)`: 判断专业是否在允许范围
- `normalize_major(major)`: 专业名称规范化（去括号、空格等）

### 要求解析
- `parse_jd_requirements(text)`: 从JD文本提取结构化要求
- 支持年龄、学历、学位、专业、政治面貌等关键信息提取

### 评估引擎
- `evaluate(candidate, jd_text)`: 执行完整的候选人评估
- 返回中文摘要和结构化JSON结果

## 审核规则

1. **年龄计算**：基于出生日期精确计算周岁，含当日边界
2. **学历学位**：若JD同时要求学历和学位，两者必须都满足
3. **专业匹配**：
   - 先进行字符串规范化
   - 查找Excel映射表获得专业大类
   - 与JD允许的专业列表进行OR逻辑匹配
4. **证据导向**：缺失信息标记为Unknown，不进行推测
5. **合规检查**：自动识别性别、民族等潜在歧视条件

## 注意事项

- xlwings需要本地安装Excel，无Excel环境会自动回退到xlcalculator或pandas
- 通义千问API有调用限制，请合理使用
- 专业匹配依赖映射表质量，建议定期更新维护
- 输出严格按照系统提示格式，确保可审计性

## 🌐 HTTP API 接口

### 可用接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/audit` | POST | 单个候选人审核 |
| `/major/match` | POST | 专业匹配查询 |

### 启动API服务
```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DASHSCOPE_API_KEY=your_api_key

# 启动服务
python app.py
```

### API 响应格式
```json
{
  "success": true,
  "data": {
    "summary": "结论：通过\n关键理由：...",
    "result": {
      "verdict": "通过",
      "derived_fields": {...},
      "criteria": [...],
      "missing_data": [],
      "policy_flags": []
    }
  },
  "metadata": {
    "candidate_name": "张三",
    "verdict": "通过",
    "criteria_count": 5,
    "missing_data_count": 0,
    "policy_flags_count": 0
  }
}
```

### 测试API
```bash
# 运行测试脚本
python test_api.py
```

