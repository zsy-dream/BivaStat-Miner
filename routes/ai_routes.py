"""
AI 推理接口路由

提供 /api/ai 前缀下的 REST 端点，
对接前端的 AI 深度解读、报告摘要、自由对话等功能。
"""
import json
import logging
from flask import Blueprint, jsonify, request, Response, stream_with_context
from services.ai_service import ai_service
from utils.task_manager import task_manager

logger = logging.getLogger(__name__)

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/status', methods=['GET'])
def ai_status():
    """检查 AI 服务是否可用"""
    return jsonify({
        'success': True,
        'available': ai_service.is_available(),
        'model': ai_service.model
    })


@ai_bp.route('/test_connection', methods=['GET'])
def test_connection():
    """测试 AI 服务连通性，返回详细诊断信息"""
    try:
        result = ai_service.test_connection()
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"AI 连通性测试异常：{str(e)}")
        return jsonify({'success': False, 'status': 'error', 'message': str(e)}), 500


@ai_bp.route('/analyze_rules', methods=['POST'])
def analyze_rules():
    """
    对关联规则进行 AI 深度解读

    请求体：
        task_id: 任务 ID（从历史任务中取规则），或
        rules: 直接传入规则列表
        summary: 可选的挖掘摘要信息
    """
    if not ai_service.is_available():
        return jsonify({
            'success': False,
            'error': 'AI 服务未配置，请检查 HUAWEI_MAAS_API_KEY 环境变量'
        }), 503

    data = request.get_json(force=True)
    rules = data.get('rules', [])
    summary = data.get('summary', {})

    # 如果提供了 task_id，从任务管理器中获取规则
    task_id = data.get('task_id')
    if task_id and not rules:
        task = task_manager.get_task(task_id)
        if task and task.get('result'):
            rules = task['result'].get('association_rules') or task['result'].get('rules', [])
            summary = task['result'].get('summary', {})

    if not rules:
        return jsonify({
            'success': False,
            'error': '未找到可分析的规则数据'
        }), 400

    try:
        from utils.global_state import global_state
        statistical_tests = global_state.get_results('statistical_tests')
        analysis = ai_service.analyze_rules(rules, summary, statistical_tests=statistical_tests)
        if task_id:
            task = task_manager.get_task(task_id)
            if task and task.get('result'):
                updated_result = dict(task.get('result') or {})
                updated_result['ai_analysis'] = analysis
                updated_result['ai_analysis_updated_at'] = __import__('datetime').datetime.now().isoformat()
                task_manager.update_task(task_id, result=updated_result)
                try:
                    latest_analysis = global_state.get_results('latest_analysis') or {}
                    latest_analysis = dict(latest_analysis)
                    latest_analysis['ai_analysis'] = analysis
                    latest_analysis['ai_analysis_updated_at'] = updated_result['ai_analysis_updated_at']
                    global_state.set_results('latest_analysis', latest_analysis)
                except Exception:
                    pass
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except RuntimeError as e:
        logger.error(f"AI 分析规则失败：{str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'hint': '如果反复失败，请访问 /api/ai/test_connection 检查 AI 服务连通性'
        }), 500
    except Exception as e:
        logger.error(f"AI 分析规则未预期异常：{type(e).__name__}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'AI 分析异常: {type(e).__name__}: {str(e)}'
        }), 500


@ai_bp.route('/generate_summary', methods=['POST'])
def generate_summary():
    """
    为报告生成 AI 执行摘要

    请求体：
        data_info: 数据集基本信息
        analysis_results: 分析结果
    """
    if not ai_service.is_available():
        return jsonify({
            'success': False,
            'error': 'AI 服务未配置'
        }), 503

    data = request.get_json(force=True)
    data_info = data.get('data_info', {})
    analysis_results = data.get('analysis_results', {})

    try:
        summary_text = ai_service.generate_report_summary(data_info, analysis_results)
        return jsonify({
            'success': True,
            'summary': summary_text
        })
    except RuntimeError as e:
        logger.error(f"AI 生成摘要失败：{str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'hint': '如果反复失败，请访问 /api/ai/test_connection 检查 AI 服务连通性'
        }), 500
    except Exception as e:
        logger.error(f"AI 生成摘要未预期异常：{type(e).__name__}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'AI 摘要异常: {type(e).__name__}: {str(e)}'
        }), 500


@ai_bp.route('/chat', methods=['POST'])
def chat():
    """
    通用 AI 对话接口

    请求体：
        message: 用户消息
        context: 可选上下文
        stream: 是否流式（默认 false）
    """
    if not ai_service.is_available():
        return jsonify({
            'success': False,
            'error': 'AI 服务未配置'
        }), 503

    data = request.get_json(force=True)
    user_message = data.get('message', '')
    context = data.get('context', '')
    use_stream = data.get('stream', False)

    if not user_message.strip():
        return jsonify({
            'success': False,
            'error': '消息不能为空'
        }), 400

    try:
        if use_stream:
            def generate():
                """SSE 流式输出生成器"""
                try:
                    for chunk in ai_service.chat_stream(user_message, context):
                        yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                except RuntimeError as e:
                    yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            reply = ai_service.chat(user_message, context)
            return jsonify({
                'success': True,
                'reply': reply
            })
    except RuntimeError as e:
        logger.error(f"AI 对话失败：{str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
