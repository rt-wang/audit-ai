import os
import json
import re
from datetime import datetime, date
from typing import Dict, List, Tuple, Any, Optional
import dashscope
from dashscope import Generation
import pandas as pd
from dateutil.parser import parse as parse_date

try:
    import xlwings as xw
    XLWINGS_AVAILABLE = True
except ImportError:
    XLWINGS_AVAILABLE = False

try:
    import xlcalculator
    from xlcalculator import ModelCompiler
    from xlcalculator.xlfunctions import xl
    XLCALCULATOR_AVAILABLE = True
except ImportError:
    XLCALCULATOR_AVAILABLE = False

SYSTEM_PROMPT = """你是一名用于招聘场景的"岗位条件审核"AI。你的唯一任务：给定（A）候选人信息与（B）岗位要求，逐条判断候选人是否满足要求，并输出简洁、可审计的结论。

输入：候选人信息（学历、学位、专业、出生日期、所在地/户籍、政治面貌、证书、健康、经历等）；岗位要求（地点/单位、岗位类型、年龄、学历与学位、专业清单、证书、政治面貌、经历及其他限制）。

规则：

1. 逐条对照：每项要求输出「要求 → 候选人证据 → 匹配 = Yes/No/Unknown + 一行理由」。
2. 明确从严，模糊从谨：
   * 年龄："以后/及以后"=含当日（on_or_after）；"之前/及以前"=含当日（on_or_before）；展示年龄与对比。
   * 学历&学位：若同时出现，两者都需满足。
   * 专业：JD列举的为**或**逻辑；做字符串规范化（去括号/方向）；仅当与列明或明确等同时判定 Yes；若仅相关且JD未写"相关/相近可"，判定 No。
   * 证书/经验/政治面貌/户籍/健康：严格证据化判定。
   * 地点/单位级别：据文本核验。
3. 证据缺失记 Unknown，并加入 `missing_data`；禁止臆测。
4. 合规提示：如出现潜在歧视性条件，在 `policy_flags` 提示"潜在合规风险：{项}"。
5. 语言与单位：保留原文；日期用 ISO；展示派生字段（年龄、归一化专业名等）。
6. 禁止外部检索，仅基于给定文本。
7. 简洁输出：每条理由一行。

输出格式（必须同时返回摘要与JSON）：

* 摘要（3–6行）：结论：通过/未通过/待核验；关键理由2–5条。
* JSON：
{
"verdict": "通过|未通过|待核验",
"derived_fields": {
"candidate_age": "<years>",
"age_cutoff": {"op": "on_or_after|on_or_before", "date": "YYYY-MM-DD"},
"normalized_major": "<string>"
},
"criteria": [
{"name":"<如：年龄>","job_requirement":"<原文>","candidate_evidence":"<原文或'无'>","match":"Yes|No|Unknown","rationale":"<一句话理由>"}
],
"missing_data": ["<字段>", "..."],
"policy_flags": ["<风险提示>", "..."]
}"""

def call_qwen(messages: List[Dict], model: str = "qwen-plus") -> str:
    response = dashscope.Generation.call(
        api_key=os.getenv('DASHSCOPE_API_KEY'),
        model=model,
        messages=messages,
        result_format='message'
    )
    
    if response.status_code == 200:
        return response.output.choices[0]['message']['content']
    else:
        raise Exception(f"Qwen API call failed: {response.message}")

def normalize_major(major: str) -> str:
    if not major:
        return ""
    
    major = major.strip()
    major = re.sub(r'[（）()【】\[\]「」『』].*?[（）()【】\[\]「」『』]', '', major)
    major = re.sub(r'[(（].*?[)）]', '', major)
    major = re.sub(r'\s+', '', major)
    
    major = major.replace('（', '').replace('）', '').replace('(', '').replace(')', '')
    
    return major.strip()

def excel_match_major(candidate_major: str, workbook_path: str = "majors.xlsx", sheet: str = "map") -> str:
    normalized_major = normalize_major(candidate_major)
    
    if XLWINGS_AVAILABLE:
        try:
            with xw.App(visible=False) as app:
                wb = app.books.open(workbook_path)
                ws = wb.sheets[sheet]
                
                lookup_range = ws.range('A:A')
                return_range = ws.range('B:B')
                
                temp_cell = ws.range('Z1')
                formula = f'=IFERROR(XLOOKUP("{normalized_major}",A:A,B:B,"未匹配"),IFERROR(VLOOKUP("{normalized_major}",A:B,2,0),"未匹配"))'
                temp_cell.formula = formula
                result = temp_cell.value
                
                wb.close()
                return result if result else "未匹配"
        except Exception:
            pass
    
    try:
        df = pd.read_excel(workbook_path, sheet_name=sheet)
        df.columns = ['子专业', '大类'] if len(df.columns) >= 2 else df.columns
        
        if '同义规范名' in df.columns:
            synonym_match = df[df['同义规范名'].str.contains(normalized_major, na=False)]
            if not synonym_match.empty:
                return synonym_match.iloc[0]['大类']
        
        exact_match = df[df['子专业'].str.contains(normalized_major, na=False)]
        if not exact_match.empty:
            return exact_match.iloc[0]['大类']
        
        return "未匹配"
    except Exception:
        return "未匹配"

def is_major_acceptable(candidate_major: str, jd_allowed_categories: List[str]) -> bool:
    mapped_category = excel_match_major(candidate_major)
    normalized_candidate = normalize_major(candidate_major)
    
    for allowed in jd_allowed_categories:
        allowed_normalized = normalize_major(allowed)
        if (mapped_category != "未匹配" and mapped_category == allowed_normalized) or \
           normalized_candidate == allowed_normalized:
            return True
    
    return False


def calculate_age(birthdate: str) -> int:
    try:
        birth_date = parse_date(birthdate).date()
        today = date.today()
        age = today.year - birth_date.year
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            age -= 1
        return age
    except:
        return None

def evaluate(candidate: Dict, jd_text: str) -> Tuple[str, Dict]:
    derived_fields = {}
    missing_data = []
    
    candidate_age = None
    if 'birthdate' in candidate and candidate['birthdate']:
        candidate_age = calculate_age(candidate['birthdate'])
        derived_fields['candidate_age'] = str(candidate_age) if candidate_age else "未知"
    else:
        missing_data.append('出生日期')
        derived_fields['candidate_age'] = "未知"
    
    if 'major' in candidate:
        derived_fields['normalized_major'] = normalize_major(candidate['major'])
    else:
        missing_data.append('专业')
        derived_fields['normalized_major'] = "未知"
    
    # Enhanced candidate info for LLM
    enhanced_candidate_info = dict(candidate)
    if candidate_age:
        enhanced_candidate_info['calculated_age'] = candidate_age
    if 'major' in candidate:
        major_category = excel_match_major(candidate['major'])
        enhanced_candidate_info['major_category'] = major_category
    
    # Prepare prompt for Qwen
    user_prompt = f"""
请根据以下候选人信息和岗位要求，进行逐条比对审核：

候选人信息：
{json.dumps(enhanced_candidate_info, ensure_ascii=False, indent=2)}

岗位要求：
{jd_text}

请严格按照系统提示的规则和输出格式进行审核。特别注意：
1. 年龄计算基于出生日期，候选人当前年龄为{candidate_age}岁（如有）
2. 专业匹配时，候选人专业"{candidate.get('major', '未知')}"对应的大类为"{excel_match_major(candidate.get('major', ''))}"（如适用）
3. 每项要求都要明确输出匹配结果：Yes/No/Unknown
4. 缺失信息标记为Unknown，不要推测
"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response = call_qwen(messages)
        
        # Parse the response to extract summary and JSON
        # The response format is: ```json + JSON + ``` + summary
        if '```json' in response and '```' in response:
            # Extract JSON block
            json_start = response.find('```json') + 7
            json_end = response.find('```', json_start)
            json_text = response[json_start:json_end].strip()
            
            # Extract summary (everything after the JSON block)
            summary_part = response[json_end + 3:].strip()
            # Clean up summary (remove markdown markers, extra newlines)
            summary_lines = []
            for line in summary_part.split('\n'):
                line = line.strip()
                if line and not line.startswith('**') and not line.startswith('#'):
                    if line.startswith('摘要：') or line.startswith('结论：'):
                        summary_lines.append(line)
                    elif line.startswith('- ') or line.startswith('关键理由') or ('符合' in line or '不符合' in line):
                        summary_lines.append(line)
            
            summary = '\n'.join(summary_lines) if summary_lines else "AI审核完成"
        else:
            # Fallback parsing if format is different
            lines = response.strip().split('\n')
            summary_lines = []
            json_started = False
            json_lines = []
            
            for line in lines:
                if line.strip().startswith('{') or json_started:
                    if not json_started and line.strip().startswith('{'):
                        json_started = True
                    json_lines.append(line)
                elif not json_started and line.strip():
                    summary_lines.append(line.strip())
            
            summary = '\n'.join(summary_lines) if summary_lines else "AI审核完成"
            json_text = '\n'.join(json_lines)
        
        # Try to parse JSON result
        try:
            result_json = json.loads(json_text)
            
            # Ensure required fields exist
            if 'derived_fields' not in result_json:
                result_json['derived_fields'] = derived_fields
            else:
                result_json['derived_fields'].update(derived_fields)
            
            if 'missing_data' not in result_json:
                result_json['missing_data'] = missing_data
            else:
                result_json['missing_data'].extend(missing_data)
                result_json['missing_data'] = list(set(result_json['missing_data']))
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            result_json = {
                "verdict": "待核验",
                "derived_fields": derived_fields,
                "criteria": [
                    {
                        "name": "AI解析",
                        "job_requirement": "完整岗位要求",
                        "candidate_evidence": "候选人完整信息",
                        "match": "Unknown",
                        "rationale": "AI解析结果格式异常，需人工审核"
                    }
                ],
                "missing_data": missing_data,
                "policy_flags": []
            }
            summary = "AI解析异常，需人工审核"
        
        return summary, result_json
        
    except Exception as e:
        # Fallback on API failure
        result_json = {
            "verdict": "待核验",
            "derived_fields": derived_fields,
            "criteria": [
                {
                    "name": "系统错误",
                    "job_requirement": "API调用",
                    "candidate_evidence": "无法获取",
                    "match": "Unknown",
                    "rationale": f"API调用失败：{str(e)}"
                }
            ],
            "missing_data": missing_data,
            "policy_flags": []
        }
        summary = f"API调用失败，需人工审核：{str(e)}"
        
        return summary, result_json

def main():
    sample_candidate = {
        "name": "张三",
        "birthdate": "1995-06-15",
        "education": "本科",
        "degree": "学士",
        "major": "计算机科学与技术",
        "political_status": "共产党员",
        "location": "北京市",
        "certificates": ["计算机二级"],
        "experience": "3年软件开发经验"
    }
    
    sample_jd = """
    岗位要求：
    1. 年龄30岁以下
    2. 本科及以上学历，学士及以上学位
    3. 专业：计算机科学与技术、软件工程、信息安全、网络工程
    4. 政治面貌：中共党员或共青团员
    5. 具有相关工作经验者优先
    """
    
    print("候选人信息审核系统")
    print("=" * 50)
    print("候选人信息:")
    print(json.dumps(sample_candidate, ensure_ascii=False, indent=2))
    print("\n岗位要求:")
    print(sample_jd)
    print("\n审核结果:")
    print("=" * 50)
    
    try:
        summary, result_json = evaluate(sample_candidate, sample_jd)
        print(summary)
        print("\nJSON结果:")
        print(json.dumps(result_json, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"评估过程中出现错误: {e}")

if __name__ == "__main__":
    main()
