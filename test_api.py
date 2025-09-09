import requests
import json

API_BASE = "http://localhost:5000"

def test_health():
    """测试健康检查接口"""
    print("=== 测试健康检查 ===")
    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_single_audit():
    """测试单个候选人审核"""
    print("=== 测试单个候选人审核 ===")
    
    data = {
        "candidate": {
            "name": "张三",
            "birthdate": "1995-06-15",
            "education": "本科",
            "degree": "学士",
            "major": "计算机科学与技术",
            "political_status": "共产党员",
            "location": "北京市",
            "certificates": ["计算机二级"],
            "experience": "3年软件开发经验"
        },
        "job_requirements": """
        岗位要求：
        1. 年龄30岁以下
        2. 本科及以上学历，学士及以上学位
        3. 专业：计算机科学与技术、软件工程、信息安全、网络工程
        4. 政治面貌：中共党员或共青团员
        5. 具有相关工作经验者优先
        """
    }
    
    response = requests.post(f"{API_BASE}/audit", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    
    if result.get('success'):
        print(f"Verdict: {result['data']['result']['verdict']}")
        print(f"Summary: {result['data']['summary'][:100]}...")
        print(f"Criteria count: {result['metadata']['criteria_count']}")
    else:
        print(f"Error: {result.get('error')}")
    print()


def test_major_matching():
    """测试专业匹配"""
    print("=== 测试专业匹配 ===")
    
    data = {
        "major": "计算机科学与技术",
        "allowed_categories": ["计算机类", "电子信息类"]
    }
    
    response = requests.post(f"{API_BASE}/major/match", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    
    if result.get('success'):
        data = result['data']
        print(f"Original: {data['original_major']}")
        print(f"Mapped to: {data['mapped_category']}")
        print(f"Is acceptable: {data['is_acceptable']}")
    else:
        print(f"Error: {result.get('error')}")
    print()

def test_curl_examples():
    """生成curl命令示例"""
    print("=== CURL 命令示例 ===")
    
    print("1. 健康检查:")
    print(f"curl -X GET {API_BASE}/health")
    print()
    
    print("2. 单个审核:")
    audit_data = {
        "candidate": {
            "name": "张三",
            "birthdate": "1995-06-15",
            "education": "本科",
            "major": "计算机科学与技术"
        },
        "job_requirements": "年龄30岁以下，本科学历，计算机专业"
    }
    print(f"curl -X POST {API_BASE}/audit \\")
    print("  -H 'Content-Type: application/json' \\")
    print(f"  -d '{json.dumps(audit_data, ensure_ascii=False)}'")
    print()
    
    print("3. 专业匹配:")
    major_data = {
        "major": "软件工程",
        "allowed_categories": ["计算机类"]
    }
    print(f"curl -X POST {API_BASE}/major/match \\")
    print("  -H 'Content-Type: application/json' \\")
    print(f"  -d '{json.dumps(major_data, ensure_ascii=False)}'")
    print()

if __name__ == "__main__":
    print("岗位条件审核代理 HTTP API 测试")
    print("=" * 50)
    
    try:
        test_health()
        test_single_audit()
        test_major_matching()    
        test_curl_examples()
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务器")
        print("请先启动服务器: python app.py")
        print()
        test_curl_examples()
    except Exception as e:
        print(f"❌ 测试出错: {e}")
