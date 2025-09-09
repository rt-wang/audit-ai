from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import logging
from agent import evaluate

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "service": "recruitment-audit-agent",
        "version": "1.0.0"
    })

@app.route('/audit', methods=['POST'])
def audit_candidate():
    """
    候选人审核接口
    
    请求格式:
    {
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
        "job_requirements": "岗位要求：1. 年龄30岁以下..."
    }
    
    响应格式:
    {
        "success": true,
        "data": {
            "summary": "结论：通过...",
            "result": {...}
        }
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                "success": False,
                "error": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Invalid JSON data"
            }), 400
        
        candidate = data.get('candidate')
        job_requirements = data.get('job_requirements')
        
        if not candidate:
            return jsonify({
                "success": False,
                "error": "Missing 'candidate' field"
            }), 400
        
        if not job_requirements:
            return jsonify({
                "success": False,
                "error": "Missing 'job_requirements' field"
            }), 400
        
        if not isinstance(candidate, dict):
            return jsonify({
                "success": False,
                "error": "'candidate' must be an object"
            }), 400
        
        if not isinstance(job_requirements, str):
            return jsonify({
                "success": False,
                "error": "'job_requirements' must be a string"
            }), 400
        
        logger.info(f"Processing audit for candidate: {candidate.get('name', 'Unknown')}")
        
        summary, result = evaluate(candidate, job_requirements)
        
        response_data = {
            "success": True,
            "data": {
                "summary": summary,
                "result": result
            },
            "metadata": {
                "candidate_name": candidate.get('name', 'Unknown'),
                "verdict": result.get('verdict', 'Unknown'),
                "criteria_count": len(result.get('criteria', [])),
                "missing_data_count": len(result.get('missing_data', [])),
                "policy_flags_count": len(result.get('policy_flags', []))
            }
        }
        
        logger.info(f"Audit completed for {candidate.get('name', 'Unknown')}: {result.get('verdict', 'Unknown')}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error processing audit request: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@app.route('/major/match', methods=['POST'])
def match_major():
    """
    专业匹配接口
    
    请求格式:
    {
        "major": "计算机科学与技术",
        "allowed_categories": ["计算机类", "电子信息类"]
    }
    """
    try:
        from agent import excel_match_major, is_major_acceptable
        
        data = request.get_json()
        major = data.get('major')
        allowed_categories = data.get('allowed_categories', [])
        
        if not major:
            return jsonify({
                "success": False,
                "error": "Missing 'major' field"
            }), 400
        
        major_category = excel_match_major(major)
        is_acceptable = is_major_acceptable(major, allowed_categories) if allowed_categories else None
        
        return jsonify({
            "success": True,
            "data": {
                "original_major": major,
                "mapped_category": major_category,
                "is_acceptable": is_acceptable,
                "allowed_categories": allowed_categories
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "success": False,
        "error": "Method not allowed"
    }), 405

if __name__ == '__main__':
    import os
    
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Recruitment Audit Agent API on port {port}")
    print(f"Health check: http://localhost:{port}/health")
    print(f"Audit endpoint: http://localhost:{port}/audit")
    print(f"Major matching: http://localhost:{port}/major/match")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
