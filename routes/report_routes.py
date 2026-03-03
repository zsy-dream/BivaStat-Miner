from flask import Blueprint, request, jsonify, send_file
import uuid
import os
from datetime import datetime
from services.report_service import generate_template, save_report
from utils.global_state import global_state

report_bp = Blueprint('report_routes', __name__)
reports_storage = {}


@report_bp.route('/generate_report', methods=['POST'])
def generate_report():
    try:
        # 1. 检查是否有分析结果
        analysis_results = global_state.get_results('latest_analysis')
        if not analysis_results:
            return jsonify({
                'success': False,
                'error': '暂无分析数据！请先点击【运行算法】。'
            }), 400

        # 2. 准备数据
        req_data = request.get_json() or {}
        report_data = analysis_results.copy()
        report_data.update(req_data)  # 合并标题

        # 3. 生成 HTML
        report_html = generate_template(report_data)

        # 4. 保存文件 (文件名保持 UUID 防止冲突)
        report_id = str(uuid.uuid4())
        filename = f"report_{report_id}.html"
        saved_path = save_report(report_html, filename)

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
            'message': '报告生成成功'
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