from flask import Blueprint, jsonify, request, send_file
from utils.global_state import global_state
from services.algorithm_service import nonparametric_test
from utils.task_manager import task_manager
import pandas as pd
import os
import uuid
import json

analysis_bp = Blueprint('analysis_bp', __name__)


@analysis_bp.route('/get_results', methods=['GET'])
def get_results():
    results = global_state.get_results('latest_analysis')

    # 兜底：结果页如果带 task_id，可以直接从任务里回填结果
    task_id = request.args.get('task_id')
    if task_id:
        task = task_manager.get_task(task_id)
        # ✅ 关键修复：如果用户明确指定了 task_id，就只看这个任务
        # 中途取消/失败/未完成时，不要兜底回填“上一次完成任务”的旧结果（否则看起来像跳转错了）
        if not task:
            return jsonify({
                'success': False,
                'error': '任务不存在或已过期。',
                'task': {'task_id': task_id, 'status': None, 'progress': None},
                'data': {
                    'summary': {'total_rules': 0, 'significant_rules': 0, 'avg_confidence': 0, 'avg_support': 0},
                    'rules': []
                }
            }), 404

        if task.get('status') != 'completed' or not task.get('result'):
            return jsonify({
                'success': False,
                'error': f"任务尚未完成（当前状态：{task.get('status')}），暂无可展示结果。",
                'task': {
                    'task_id': task_id,
                    'status': task.get('status'),
                    'progress': task.get('progress')
                },
                'data': {
                    'summary': {'total_rules': 0, 'significant_rules': 0, 'avg_confidence': 0, 'avg_support': 0},
                    'rules': []
                }
            })

        # task completed with result
        global_state.set_results('latest_analysis', task['result'])
        results = task['result']

    if not results:
        # 兜底1：即使结果页没带 task_id，也尝试用“最近任务”回填结果
        last_id = getattr(global_state, 'last_task_id', None)
        last_task = task_manager.get_task(last_id) if last_id else None
        if last_task and last_task.get('status') == 'completed' and last_task.get('result'):
            global_state.set_results('latest_analysis', last_task['result'])
            results = last_task['result']

    if not results:
        # 兜底2：在 TaskManager 里查找任意“已完成”的任务结果（防止 last_task_id 没被正确设置）
        completed_with_result = [
            t for t in task_manager.tasks.values()
            if t.get('status') == 'completed' and t.get('result')
        ]
        if completed_with_result:
            # 简单地取最后一个
            task = completed_with_result[-1]
            global_state.set_results('latest_analysis', task['result'])
            results = task['result']

    if not results:
        # 兜底3：仍然没有结果，返回带任务状态的空数据，让前端给出友好提示
        last_id = getattr(global_state, 'last_task_id', None)
        last_task = task_manager.get_task(last_id) if last_id else None
        return jsonify({
            'success': False,
            'error': '暂无分析数据，请先运行算法。',
            'task': {
                'task_id': last_id,
                'status': last_task.get('status') if last_task else None,
                'progress': last_task.get('progress') if last_task else None
            } if last_id else None,
            'data': {
                'summary': {'total_rules': 0, 'significant_rules': 0, 'avg_confidence': 0, 'avg_support': 0},
                'rules': []
            }
        })

    return jsonify({
        'success': True,
        'data': {
            'summary': results.get('summary', {}),
            'rules': results.get('association_rules', [])
        }
    })


@analysis_bp.route('/generate_chart', methods=['POST'])
def generate_chart():
    results = global_state.get_results('latest_analysis')
    if not results:
        return jsonify({'success': False, 'error': 'No data'})

    rules = results.get('association_rules', [])

    # 简单生成图表数据
    # 提取前20条规则用于画图，避免图表太拥挤
    top_rules = rules[:20]

    chart_data = {
        'labels': [f"R{i + 1}" for i in range(len(top_rules))],
        'confidence': [r['confidence'] for r in top_rules],
        'support': [r['support'] for r in top_rules],
        'lift': [r['lift'] for r in top_rules]
    }

    return jsonify({'success': True, 'chart_data': chart_data})


@analysis_bp.route('/run_test', methods=['POST'])
def run_test():
    try:
        req = request.get_json() or {}
        test_type = (req.get('test_type') or 'chi2').strip().lower()
        alpha = float(req.get('alpha', 0.05))
        var1 = req.get('var1')
        var2 = req.get('var2')

        # 优先使用当前会话数据（上传/清洗后会写入）
        df = getattr(global_state, 'current_data', None)
        if df is None:
            try:
                from models.data_model import data_model_instance
                df = data_model_instance.current_data
            except Exception:
                df = None

        if df is None or getattr(df, 'empty', True):
            return jsonify({'success': False, 'error': '暂无可用于检验的数据，请先上传并预处理数据。'}), 400

        # 兼容前端 testType 值
        mapping = {
            'auto': 'chi2',               # 自动模式：当前先简单映射为卡方检验
            'mannwhitney': 'mann-whitney',
            'mann-whitney': 'mann-whitney',
            'wilcoxon': 'wilcoxon',
            'kruskal': 'kruskal-wallis',
            'kruskal-wallis': 'kruskal-wallis',
            'chi2': 'chi2',
            'ks': 'ks',
            'spearman': 'spearman',
        }
        mapped = mapping.get(test_type, test_type)
        if not var1 or not var2:
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if len(numeric_cols) >= 2:
                var1, var2 = numeric_cols[:2]
            else:
                return jsonify({'success': False, 'error': '请指定 var1 和 var2，或确保当前数据至少包含两列数值变量。'}), 400

        results = nonparametric_test(df, {
            'test_method': mapped,
            'alpha': alpha,
            'var1': var1,
            'var2': var2
        })
        if isinstance(results, dict) and results.get('error'):
            return jsonify({'success': False, 'error': results['error']}), 400

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# 👇【修复 404】补上这个导出接口
@analysis_bp.route('/export_results', methods=['POST'])
def export_results():
    try:
        results = global_state.get_results('latest_analysis')
        if not results:
            return jsonify({'success': False, 'error': '没有数据可导出'})

        # 将规则导出为 CSV
        rules = results.get('association_rules', [])
        if not rules:
            return jsonify({'success': False, 'error': '规则列表为空'})

        req = request.get_json() or {}
        export_format = (req.get('format') or 'csv').strip().lower()

        # 规范化导出字段（让 Excel/CSV 更可读）
        def fmt_items(v):
            if isinstance(v, list):
                return "、".join(map(str, v))
            return str(v) if v is not None else ""

        export_rows = []
        for r in rules:
            export_rows.append({
                'Antecedent': fmt_items(r.get('antecedent') or r.get('antecedents')),
                'Consequent': fmt_items(r.get('consequent') or r.get('consequents')),
                'Support': r.get('support', 0),
                'Confidence': r.get('confidence', 0),
                'Lift': r.get('lift', 0),
                'Conviction': r.get('conviction', 0),
                'Length': r.get('length', 0),
            })

        df = pd.DataFrame(export_rows)

        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'reports')
        reports_dir = os.path.abspath(reports_dir)
        os.makedirs(reports_dir, exist_ok=True)

        file_id = str(uuid.uuid4())
        if export_format in ('excel', 'xlsx'):
            filename = f"analysis_rules_{file_id}.xlsx"
            file_path = os.path.join(reports_dir, filename)
            df.to_excel(file_path, index=False)
            return send_file(file_path, as_attachment=True, download_name="analysis_rules.xlsx")

        if export_format == 'csv':
            filename = f"analysis_rules_{file_id}.csv"
            file_path = os.path.join(reports_dir, filename)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            return send_file(file_path, as_attachment=True, download_name="analysis_rules.csv")

        if export_format == 'json':
            filename = f"analysis_rules_{file_id}.json"
            file_path = os.path.join(reports_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_rows, f, ensure_ascii=False, indent=2)
            return send_file(file_path, as_attachment=True, download_name="analysis_rules.json")

        return jsonify({'success': False, 'error': f'不支持的导出格式: {export_format}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500