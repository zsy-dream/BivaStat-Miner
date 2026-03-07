from flask import Blueprint, request, jsonify, send_file
import uuid
import os
import re
import logging
import importlib
from datetime import datetime
import services.report_service as report_service_module
from services.ai_service import ai_service
from utils.global_state import global_state
from models.data_model import data_model_instance

logger = logging.getLogger(__name__)

report_bp = Blueprint('report_routes', __name__)
reports_storage = {}
DEFAULT_REPORT_TITLE = '信贷场景关联因素挖掘与非参数验证报告'


def _is_uuid_filename(stem: str) -> bool:
    return bool(re.fullmatch(r'[0-9a-fA-F\-]{24,}', stem or ''))


def _template_label(template_type: str) -> str:
    mapping = {
        'financial_risk': '金融风控',
        'market_analysis': '市场分析',
        'general_analysis': '综合分析',
        'basic': '综合分析',
        'medical_research': '医学研究'
    }
    return mapping.get(template_type, '综合分析')


def _derive_dataset_name(current_path: str | None) -> str:
    if not current_path:
        return '当前数据集'
    name = os.path.basename(current_path)
    stem, _ = os.path.splitext(name)
    stem = stem.replace('_enhanced', '').replace('.cleaned', '')

    if stem.startswith('sample_'):
        sample_map = {
            'sample_retail': '零售交易数据集',
            'sample_medical': '医疗诊断数据集',
            'sample_financial': '金融风控数据集',
            'sample_education': '教育评估数据集',
            'sample_marketing': '市场营销数据集',
            'sample_iris_extended': '鸢尾花扩展数据集'
        }
        return sample_map.get(stem, '示例数据集')

    if _is_uuid_filename(stem):
        return '当前数据集'
    if stem.startswith('imported_'):
        return '导入数据集'
    return stem or '当前数据集'


def _build_auto_title(req_title: str, template_type: str, dataset_name: str, analysis_results: dict) -> str:
    req_title = (req_title or '').strip()
    if req_title and req_title != DEFAULT_REPORT_TITLE:
        return req_title

    summary = analysis_results.get('summary', {}) if isinstance(analysis_results, dict) else {}
    rules = analysis_results.get('association_rules') or analysis_results.get('rules') or []
    total_rules = summary.get('total_rules') if isinstance(summary, dict) else None
    if total_rules is None:
        total_rules = len(rules) if isinstance(rules, list) else 0

    date_tag = datetime.now().strftime('%Y%m%d')
    tpl = _template_label(template_type)
    if total_rules:
        return f"{dataset_name}·{tpl}关联分析报告（{total_rules}条规则）_{date_tag}"
    return f"{dataset_name}·{tpl}分析报告_{date_tag}"


@report_bp.route('/generate_report', methods=['POST'])
def generate_report():
    try:
        # 强制刷新报告服务模块，避免长生命周期进程持有旧函数对象
        importlib.reload(report_service_module)
        # 1. 获取请求参数
        req_data = request.get_json() or {}
        task_id = req_data.get('task_id')
        
        # 2. 检查是否有分析结果 (优先从指定任务中取，其次从全局状态取)
        analysis_results = None
        task = None
        if task_id:
            from utils.task_manager import task_manager
            task = task_manager.get_task(task_id)
            if task and task.get('result'):
                analysis_results = task['result']
                logger.info(f"正在为历史任务 {task_id} 生成分析报告")
        
        if not analysis_results:
            analysis_results = global_state.get_results('latest_analysis')
            logger.info("正在为最近一次会话结果生成分析报告")

        if not analysis_results:

            return jsonify({
                'success': False,
                'error': '暂无分析数据！请先点击【运行算法】。'
            }), 400

        # 3. 准备报告数据
        report_data = analysis_results.copy()
        report_data.update(req_data)  # 合并标题等表单数据
        template_type = req_data.get('templateType') or req_data.get('template_type') or 'general_analysis'

        include_ai_summary = bool(req_data.get('use_ai_summary'))
        report_data['include_ai_summary'] = include_ai_summary

        # 3.1 注入真实的数据集信息 (优先从原任务数据路径加载)
        data_info = {}
        try:
            df = None
            if task and task.get('params', {}).get('data_path'):
                from models.data_model import get_data
                data_path = task['params']['data_path']
                if os.path.exists(data_path):
                    df = get_data(data_path)
            
            if df is None:
                df = data_model_instance.current_data

            if df is not None:

                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
                data_info = {
                    'shape': [len(df), len(df.columns)],
                    'columns': df.columns.tolist(),
                    'numeric_columns': numeric_cols,
                    'categorical_columns': categorical_cols,
                    'dtypes': {col: str(dt) for col, dt in df.dtypes.items()},
                    'missing_total': int(df.isnull().sum().sum()),
                    'duplicate_rows': int(df.duplicated().sum()),
                }
                # 补充数据质量报告
                total_cells = len(df) * len(df.columns)
                missing_ratio = data_info['missing_total'] / total_cells if total_cells > 0 else 0
                dup_ratio = data_info['duplicate_rows'] / len(df) if len(df) > 0 else 0
                quality_score = max(0, 100 - missing_ratio * 50 - dup_ratio * 30)
                data_info['quality_report'] = {
                    'missing_values': {'total_missing': data_info['missing_total']},
                    'duplicates': {'duplicate_percentage': round(dup_ratio * 100, 2)}
                }
                data_info['quality_score'] = round(quality_score, 1)
        except Exception as e:
            logger.warning(f"获取数据集信息失败: {e}")

        report_data['data_info'] = data_info
        dataset_name = req_data.get('dataset_name') or _derive_dataset_name(getattr(data_model_instance, 'current_path', None))
        report_data['title'] = _build_auto_title(req_data.get('title', ''), template_type, dataset_name, analysis_results)
        report_data['template_type'] = template_type
        # 仅在用户明确开启报告 AI 摘要时，才允许把已保存的 AI 深度解读注入最终报告
        if include_ai_summary and analysis_results.get('ai_analysis'):
            report_data['ai_analysis'] = analysis_results.get('ai_analysis')
            report_data['ai_analysis_updated_at'] = analysis_results.get('ai_analysis_updated_at')
        else:
            report_data.pop('ai_analysis', None)
            report_data.pop('ai_analysis_updated_at', None)
            report_data.pop('ai_executive_summary', None)
            report_data.pop('ai_executive_summary_html', None)
            report_data.pop('ai_analysis_html', None)

        # 2.2 确保 summary 字段有真实的统计
        summary = report_data.get('summary', {})
        if isinstance(summary, dict):
            if data_info.get('shape'):
                summary.setdefault('total_records', data_info['shape'][0])
                summary.setdefault('total_features', data_info['shape'][1])
            report_data['summary'] = summary

        # 2.5 如果请求了 AI 执行摘要，调用 DeepSeek 生成
        if include_ai_summary and ai_service.is_available():
            try:
                if report_data.get('ai_executive_summary'):
                    logger.info("复用已存在的 AI 执行摘要")
                else:
                    full_analysis_context = report_data.copy()
                    st_results = global_state.get_results('statistical_tests')
                    if st_results:
                        full_analysis_context['statistical_tests'] = st_results

                    ai_summary = ai_service.generate_report_summary(
                        data_info=data_info,
                        analysis_results=full_analysis_context
                    )
                    report_data['ai_executive_summary'] = ai_summary
                    logger.info("AI 执行摘要生成成功")
            except Exception as e:
                logger.warning(f"AI 摘要生成失败，跳过：{type(e).__name__}: {str(e)}")
                report_data['ai_summary_error'] = str(e)

        # 3. 生成 HTML
        report_html = report_service_module.generate_template(report_data)

        # 4. 保存文件 (文件名保持 UUID 防止冲突)
        report_id = str(uuid.uuid4())
        filename = f"report_{report_id}.html"
        saved_path = report_service_module.save_report(report_html, filename)

        # 5. 记录元数据
        reports_storage[report_id] = {
            'title': report_data.get('title', '分析报告'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'filename': filename,
            'path': saved_path
        }

        return jsonify({
            'success': True,
            'report_id': report_id,
            'message': '报告生成成功',
            'title': report_data.get('title', '分析报告')
        })

    except Exception as e:
        print(f"Report Error: {e}")
        return jsonify({'error': str(e)}), 500


@report_bp.route('/download_report/<report_id>', methods=['GET'])
def download_report(report_id):
    if report_id not in reports_storage:
        return jsonify({'error': 'Report not found'}), 404

    info = reports_storage[report_id]
    if os.path.exists(info['path']):
        # 👇【关键修改】这里强制设置下载的文件名！
        # 如果标题里有特殊字符，简单处理一下
        safe_title = "".join([c for c in info['title'] if c.isalnum() or c in (' ', '-', '_', '.')]).strip()
        if not safe_title: safe_title = "report"

        return send_file(
            info['path'],
            as_attachment=True,
            download_name=f"{safe_title}.html"  # 这样下载下来就是中文名了
        )
    else:
        return jsonify({'error': 'File missing'}), 404