from flask import Blueprint, request, jsonify, current_app, send_file
import os
import uuid
import time
from datetime import datetime
import pandas as pd
import numpy as np
import logging
from io import BytesIO

# 引用改进后的模块
from models.data_model import load_data, validate_data, get_data, data_model_instance
from services.data_service import data_service
from services.data_import_service import data_import_service
from services.enhanced_preprocessing_service import enhanced_preprocessing_service
from services.sample_data_service import sample_data_generator
from utils.global_state import global_state
from utils.security import security_validator
from utils.error_handler import (
    handle_app_exception, create_success_response, create_error_response,
    ValidationException, FileException, DataException, SecurityException, ResourceNotFoundException,
    log_operation
)
from utils.json_utils import to_json_compatible

# 设置日志
logger = logging.getLogger(__name__)

data_bp = Blueprint('data_routes', __name__)

@data_bp.route('/clear_current', methods=['POST'])
@handle_app_exception
def clear_current():
    """清除当前数据集会话"""
    global_state.clear()
    data_model_instance.current_data = None
    data_model_instance.current_path = None
    return create_success_response({"message": "会话已重置"})

@data_bp.route('/current', methods=['GET'])
@handle_app_exception
def get_current():
    """获取当前数据集信息（用于首页上传后在数据管理页自动同步显示）"""
    current_data, current_path = global_state.get_current_data()
    
    if not current_path:
        raise ResourceNotFoundException('暂无当前数据')

    if current_data is None or current_data.empty:
        raise DataException('当前数据为空')

    return create_success_response({
        'shape': current_data.shape,
        'columns': list(current_data.columns),
        'filename': os.path.basename(current_path),
        'path': current_path,
        'preview': current_data.head(300).fillna('').to_dict(orient='records')
    })


@data_bp.route('/upload_data', methods=['POST'])
@handle_app_exception
def upload_data():
    """安全文件上传处理"""
    # 1. 检查是否有文件
    if 'file' not in request.files:
        raise ValidationException('未上传文件')

    file = request.files['file']
    if file.filename == '':
        raise ValidationException('文件名为空')

    filename = file.filename

    # 2. 安全验证文件名
    is_valid, result = security_validator.validate_filename(file.filename)
    if not is_valid:
        raise SecurityException(result)
    secure_name = result

    # 3. 读取文件内容进行验证
    file_content = file.read()
    file.seek(0)  # 重置文件指针

    # 4. 验证文件大小
    is_valid, message = security_validator.validate_file_size(len(file_content))
    if not is_valid:
        raise FileException(message)

    # 5. 验证文件类型
    is_valid, mime_type = security_validator.validate_file_type(file.filename, file_content)
    if not is_valid:
        raise SecurityException(mime_type)

    # 6. 扫描文件内容安全性
    is_valid, message = security_validator.scan_file_content(file_content, filename)
    if not is_valid:
        raise SecurityException(message)

    # 7. 保存文件到 uploads 文件夹
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder, exist_ok=True)

    # 生成唯一文件名
    file_ext = os.path.splitext(secure_name)[1].lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(upload_folder, unique_filename)

    # 安全保存文件
    file.save(file_path)
    
    # 记录操作日志
    log_operation('file_upload', details={
        'original_filename': file.filename,
        'secure_filename': secure_name,
        'file_size': len(file_content),
        'mime_type': mime_type,
        'file_path': file_path
    })

    logger.info(f"文件已安全保存至: {file_path}")

    # 8. 加载和验证数据（添加超时保护）
    try:
        import signal
        import threading
        
        # 使用线程和超时机制防止卡死
        result_container = {}
        exception_container = {}
        
        def load_with_timeout():
            try:
                df = load_data(file_path)
                if not validate_data(df):
                    raise ValidationException('文件内容为空或格式无效')
                result_container['df'] = df
            except Exception as e:
                exception_container['error'] = e
        
        # 启动加载线程
        load_thread = threading.Thread(target=load_with_timeout)
        load_thread.daemon = True
        load_thread.start()
        
        # 等待最多30秒
        load_thread.join(timeout=30)
        
        if load_thread.is_alive():
            raise TimeoutError('文件加载超时，请检查文件是否过大或格式是否正确')
        
        if 'error' in exception_container:
            raise exception_container['error']
        
        df = result_container['df']

        # 9. 更新全局状态
        global_state.set_current_data(df, file_path)
        data_model_instance.current_data = df
        data_model_instance.current_path = file_path

        return create_success_response({
            'message': '文件上传并解析成功',
            'shape': df.shape,
            'columns': list(df.columns),
            'filename': secure_name,
            'original_filename': file.filename,
            'path': file_path,
            'preview': df.head(300).fillna('').to_dict(orient='records')
        })

    except Exception as e:
        # 清理上传的文件
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.warning(f"清理失败文件: {file_path}")
        raise


@data_bp.route('/preview_data', methods=['POST'])
@handle_app_exception
def preview_data():
    """获取数据预览信息（列名、缺失值、类型等）"""
    data = request.json
    file_path = data.get('file_path')
    if not file_path:
        raise ValidationException('未提供文件路径')
        
    df = get_data(file_path)
    
    # 构建列信息
    columns_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = int(df[col].isnull().sum())
        unique = int(df[col].nunique())
        columns_info.append({
            'name': col,
            'type': dtype,
            'missing': missing,
            'unique': unique
        })
        
    return create_success_response({
        'columns_info': columns_info,
        'shape': df.shape,
        'preview': df.head(10).fillna('NaN').to_dict(orient='records')
    })


@data_bp.route('/preprocess_data', methods=['POST'])
@handle_app_exception
def preprocess_data():
    """执行数据清洗与预处理（缺失值、异常值、标准化、变量变换等）"""
    req_data = request.json
    file_path = req_data.get('file_path')
    options = req_data.get('options', {})
    
    if not file_path:
        raise ValidationException('未提供文件路径')
        
    # 1. 获取原始数据（支持从缓存读取 cleaned_path）
    df = get_data(file_path)
    
    # 2. 执行清洗（缺失值 + 异常值）
    cleaned_df = data_service.clean_data(df, options)

    # 3. 可选标准化（Z-score / Min-Max）
    normalize_method = options.get('normalize_method', 'none')
    if normalize_method in ('standard', 'minmax'):
        cleaned_df = data_service.standardize_data(
            cleaned_df,
            method='standard' if normalize_method == 'standard' else 'minmax'
        )

    # 4. 可选变量变换（对数 / Box-Cox）
    transform_method = options.get('transform_method', 'none')
    if transform_method in ('log', 'boxcox'):
        cleaned_df = data_service.transform_data(cleaned_df, method=transform_method)
    
    # 5. 更新缓存（或保存为新文件，这里简化为更新缓存）
    cleaned_path = file_path + ".cleaned"
    # 关键修复：DataModel.data_cache 的 value 结构是 (df, timestamp)，不能直接塞 DataFrame
    now_ts = time.time()
    try:
        lock = getattr(data_model_instance, "_lock", None)
        if lock:
            lock.acquire()
        data_model_instance.data_cache[cleaned_path] = (cleaned_df, now_ts)
        if hasattr(data_model_instance, "_cache_access_times") and isinstance(getattr(data_model_instance, "_cache_access_times"), dict):
            data_model_instance._cache_access_times[cleaned_path] = now_ts
        if hasattr(data_model_instance, "_cleanup_cache"):
            data_model_instance._cleanup_cache()
    finally:
        if 'lock' in locals() and lock:
            lock.release()
    data_model_instance.current_data = cleaned_df
    data_model_instance.current_path = cleaned_path
    global_state.set_current_data(cleaned_df, cleaned_path)
    
    return create_success_response({
        'message': '数据清洗完成',
        'cleaned_path': cleaned_path,
        'shape_before': df.shape,
        'shape_after': cleaned_df.shape,
        'preview': cleaned_df.head(50).fillna('NaN').to_dict(orient='records')
    })


@data_bp.route('/quality_report', methods=['POST'])
@handle_app_exception
def quality_report():
    """数据质量评估：整合服务层能力，提供多维评分与深度诊断"""
    try:
        req = request.get_json() or {}
        file_path = req.get('file_path')
        
        if not file_path:
            # 兼容：如果未提供路径，尝试取最近一次的数据
            df, file_path = global_state.get_current_data()
            if df is None:
                raise ValidationException("未提供文件路径且当前无加载数据")
        else:
            try:
                df = get_data(file_path)
            except Exception:
                # 虚拟路径失败时回退到全局状态
                df, _ = global_state.get_current_data()
                if df is None:
                    raise
            
        if df is None or df.empty:
            raise DataException("数据集为空，无法进行质量评估")

        # 核心：使用增强预处理服务的深度评估
        assessment = enhanced_preprocessing_service.assess_data_quality(df)
        
        # 兼容旧的前端 summary 结构
        summary = {
            'rows': int(df.shape[0]),
            'cols': int(df.shape[1]),
            'total_missing': assessment['missing_values']['total_missing'],
            'missing_rate': (assessment['missing_values']['total_missing'] / df.size) if df.size > 0 else 0,
            'warnings': assessment['data_consistency']['issues_found'],
            'errors': assessment['missing_values']['high_missing_columns'],
            'overall_score': assessment['overall_score']
        }
        
        # 针对前端的可视化数据格式化
        missing_by_col = assessment['missing_values']['missing_percentage_by_column']
        sorted_missing = sorted(missing_by_col.items(), key=lambda x: x[1], reverse=True)[:12]
        
        return create_success_response({
            'summary': summary,
            'missing_chart': {
                'labels': [k for k, _ in sorted_missing],
                'values': [v for _, v in sorted_missing]
            },
            'assessment': assessment
        })
    except Exception as e:
        logger.error(f"质量评估接口异常: {str(e)}")
        raise


@data_bp.route('/export_current', methods=['GET'])
@handle_app_exception
def export_current():
    """将当前数据集导出为文件供用户下载"""
    try:
        df, _ = global_state.get_current_data()
        if df is None or df.empty:
            raise DataException("暂无可导出的数据，请先上传或加载数据集")

        export_format = (request.args.get('format') or 'csv').strip().lower()
        
        # 使用内存流避免产生物理临时文件（更安全、高性能）
        import io
        if export_format in ('excel', 'xlsx'):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            return send_file(
                output, 
                as_attachment=True, 
                download_name=f'processed_data_{datetime.now().strftime("%Y%m%d%H%M")}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        # 默认 CSV
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            as_attachment=True,
            download_name=f'processed_data_{datetime.now().strftime("%Y%m%d%H%M")}.csv',
            mimetype='text/csv'
        )
    except Exception as e:
        logger.error(f"导出数据失败: {str(e)}")
        raise

@data_bp.route('/quality_report/download', methods=['GET'])
@handle_app_exception
def download_quality_report():
    """下载数据质量诊断报告（HTML 格式）"""
    try:
        df, current_path = global_state.get_current_data()
        if df is None:
            raise ValidationException("无加载数据，无法生成报告")

        assessment = enhanced_preprocessing_service.assess_data_quality(df)
        dataset_name = os.path.basename(current_path) if current_path else '未知数据集'

        html = _render_quality_html(assessment, dataset_name)

        import io
        output = io.BytesIO(html.encode('utf-8'))

        return send_file(
            output,
            as_attachment=True,
            download_name=f'数据质量诊断报告_{datetime.now().strftime("%Y%m%d%H%M")}.html',
            mimetype='text/html'
        )
    except Exception as e:
        logger.error(f"下载质量报告失败: {str(e)}")
        raise


def _render_quality_html(assessment: dict, dataset_name: str) -> str:
    """将质量评估数据渲染为可读 HTML 报告"""
    basic = assessment.get('basic_info', {})
    shape = basic.get('shape', (0, 0))
    mem_mb = basic.get('memory_usage_mb', 0)
    dtypes = basic.get('dtypes', {})
    score = max(0, min(100, assessment.get('overall_score', 0)))

    missing = assessment.get('missing_values', {})
    total_missing = missing.get('total_missing', 0)
    pct_by_col = missing.get('missing_percentage_by_column', {})
    high_missing = missing.get('high_missing_columns', [])

    dup = assessment.get('duplicates', {})
    dup_count = dup.get('total_duplicates', 0)
    dup_pct = dup.get('duplicate_percentage', 0)

    outliers = assessment.get('outliers', {})
    consistency = assessment.get('data_consistency', {})
    issues = consistency.get('issues_found', [])

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # --- score color ---
    if score >= 80:
        score_color, score_label = '#16a34a', '优良'
    elif score >= 60:
        score_color, score_label = '#d97706', '中等'
    else:
        score_color, score_label = '#dc2626', '较差'

    # --- dtype rows ---
    dtype_rows = ''.join(
        f'<tr><td>{k}</td><td>{v} 列</td></tr>' for k, v in dtypes.items()
    ) or '<tr><td colspan="2">无</td></tr>'

    # --- missing rows (top 15) ---
    sorted_missing = sorted(pct_by_col.items(), key=lambda x: x[1], reverse=True)
    missing_rows = ''
    for col, pct in sorted_missing[:15]:
        bar_w = min(pct, 100)
        bar_color = '#dc2626' if pct > 50 else ('#d97706' if pct > 10 else '#2383e2')
        missing_rows += (
            f'<tr>'
            f'<td>{col}</td>'
            f'<td style="width:55%"><div class="bar-bg"><div class="bar" style="width:{bar_w}%;background:{bar_color}"></div></div></td>'
            f'<td style="text-align:right">{pct:.2f}%</td>'
            f'</tr>'
        )
    if not missing_rows:
        missing_rows = '<tr><td colspan="3" style="text-align:center;color:#9ca3af">所有列均无缺失值 ✓</td></tr>'

    # --- high missing warning ---
    high_missing_html = ''
    if high_missing:
        cols_str = '、'.join(high_missing)
        high_missing_html = f'<div class="alert alert-danger">⚠ 高缺失列（>50%）：{cols_str}</div>'

    # --- outlier rows ---
    outlier_rows = ''
    for col, info in outliers.items():
        cnt = info.get('count', 0)
        pct = info.get('percentage', 0)
        if cnt > 0:
            outlier_rows += (
                f'<tr>'
                f'<td>{col}</td>'
                f'<td style="text-align:right">{cnt}</td>'
                f'<td style="text-align:right">{pct:.2f}%</td>'
                f'<td>{info["bounds"]["lower"]:.4g} ~ {info["bounds"]["upper"]:.4g}</td>'
                f'</tr>'
            )
    if not outlier_rows:
        outlier_rows = '<tr><td colspan="4" style="text-align:center;color:#9ca3af">未检测到显著异常值 ✓</td></tr>'

    # --- consistency ---
    if issues:
        issue_items = ''.join(f'<li>{i}</li>' for i in issues)
        consistency_html = f'<ul class="issue-list">{issue_items}</ul>'
    else:
        consistency_html = '<p class="ok-text">未发现数据一致性问题 ✓</p>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>数据质量诊断报告</title>
<style>
  :root {{ --bg: #f8f9fa; --card: #fff; --border: #e5e7eb; --text: #1f2937; --muted: #6b7280; --accent: #2383e2; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
          background: var(--bg); color: var(--text); line-height:1.6; padding:40px 20px; }}
  .container {{ max-width:900px; margin:0 auto; }}
  .header {{ text-align:center; margin-bottom:36px; }}
  .header h1 {{ font-size:26px; font-weight:900; letter-spacing:-0.5px; margin-bottom:6px; }}
  .header .subtitle {{ font-size:13px; color:var(--muted); }}
  .score-ring {{ display:inline-flex; align-items:center; justify-content:center;
                 width:100px; height:100px; border-radius:50%; margin:20px auto 8px;
                 border:6px solid {score_color}; }}
  .score-ring .val {{ font-size:32px; font-weight:900; color:{score_color}; }}
  .score-label {{ font-size:13px; font-weight:700; color:{score_color}; }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:14px;
           padding:24px 28px; margin-bottom:20px; }}
  .card h2 {{ font-size:15px; font-weight:800; margin-bottom:14px; display:flex; align-items:center; gap:8px; }}
  .card h2 .icon {{ font-size:18px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ padding:8px 10px; border-bottom:1px solid #f1f1f0; text-align:left; }}
  th {{ font-weight:700; color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:0.5px; }}
  .bar-bg {{ height:8px; background:#f1f1f0; border-radius:4px; overflow:hidden; }}
  .bar {{ height:100%; border-radius:4px; transition:width .3s; }}
  .kv-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; }}
  .kv-item {{ background:#f9fafb; padding:14px 16px; border-radius:10px; }}
  .kv-item .label {{ font-size:11px; color:var(--muted); font-weight:600; text-transform:uppercase; letter-spacing:0.3px; }}
  .kv-item .value {{ font-size:20px; font-weight:800; margin-top:4px; }}
  .alert {{ padding:12px 16px; border-radius:10px; font-size:13px; font-weight:600; margin-bottom:14px; }}
  .alert-danger {{ background:#fef2f2; color:#991b1b; border:1px solid #fecaca; }}
  .issue-list {{ padding-left:20px; font-size:13px; }}
  .issue-list li {{ margin-bottom:6px; }}
  .ok-text {{ color:#16a34a; font-weight:600; font-size:13px; }}
  .footer {{ text-align:center; margin-top:36px; font-size:11px; color:var(--muted); }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>数据质量诊断报告</h1>
    <p class="subtitle">{dataset_name} · 生成时间 {now_str}</p>
    <div class="score-ring"><span class="val">{score:.0f}</span></div>
    <div class="score-label">综合评分 · {score_label}</div>
  </div>

  <!-- 基本信息 -->
  <div class="card">
    <h2><span class="icon">📋</span> 数据集概览</h2>
    <div class="kv-grid">
      <div class="kv-item"><div class="label">行数</div><div class="value">{shape[0]:,}</div></div>
      <div class="kv-item"><div class="label">列数</div><div class="value">{shape[1]:,}</div></div>
      <div class="kv-item"><div class="label">内存占用</div><div class="value">{mem_mb:.2f} MB</div></div>
      <div class="kv-item"><div class="label">总缺失单元格</div><div class="value">{total_missing:,}</div></div>
    </div>
    <table style="margin-top:16px">
      <tr><th>数据类型</th><th>列数</th></tr>
      {dtype_rows}
    </table>
  </div>

  <!-- 缺失值 -->
  <div class="card">
    <h2><span class="icon">🔍</span> 缺失值分析</h2>
    {high_missing_html}
    <table>
      <tr><th>列名</th><th>缺失占比</th><th style="text-align:right">百分比</th></tr>
      {missing_rows}
    </table>
  </div>

  <!-- 重复值 -->
  <div class="card">
    <h2><span class="icon">📑</span> 重复值检测</h2>
    <div class="kv-grid">
      <div class="kv-item"><div class="label">重复行数</div><div class="value">{dup_count:,}</div></div>
      <div class="kv-item"><div class="label">重复率</div><div class="value">{dup_pct:.2f}%</div></div>
    </div>
  </div>

  <!-- 异常值 -->
  <div class="card">
    <h2><span class="icon">📊</span> 异常值检测 (IQR)</h2>
    <table>
      <tr><th>列名</th><th style="text-align:right">异常值数</th><th style="text-align:right">占比</th><th>正常范围</th></tr>
      {outlier_rows}
    </table>
  </div>

  <!-- 一致性 -->
  <div class="card">
    <h2><span class="icon">🛡️</span> 数据一致性</h2>
    {consistency_html}
  </div>

  <div class="footer">
    <p>由 <strong>BivaStat-Miner 双变量关联挖掘与非参数统计分析平台</strong> 自动生成</p>
  </div>
</div>
</body>
</html>
"""


@data_bp.route('/profile', methods=['GET'])
def auto_profile():
    """
    针对当前数据集做一次“体检”，并给出推荐的挖掘/检验参数。
    支持通过 task_id 指定数据集。
    """
    try:
        task_id = request.args.get('task_id')
        df = None
        path = None

        if task_id:
            from services.algorithm_service import algorithm_service
            task = algorithm_service.get_task(task_id)
            if task:
                # 尝试从任务中恢复数据路径
                path = task.get('file_path') or task.get('cleaned_path')
                if path:
                    df = get_data(path)
                
                # 如果任务中有结果，也可以从结果中获取一些提示
                # 注意：这里我们主要需要 df 进行体检
        
        if df is None:
            # 1. 获取当前数据（使用全局状态管理器的线程安全方法）
            df, path = global_state.get_current_data()
            
            # 如果全局状态为空，尝试从 model 层兜底（通常同步）
            if df is None or df.empty:
                df = data_model_instance.current_data

        if df is None or df.empty:
            return jsonify({
                'success': False,
                'error': '暂无已加载的数据，请先上传或完成预处理。',
            }), 400

        rows, cols = map(int, df.shape)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = [c for c in df.columns if c not in numeric_cols]

        # 2. 生成质量评估（复用逻辑）
        assessment = enhanced_preprocessing_service.assess_data_quality(df)
        
        # 根据样本规模和类型简单启发式推荐参数
        if rows < 1000:
            rec_support = 0.08
        elif rows < 5000:
            rec_support = 0.05
        elif rows < 20000:
            rec_support = 0.03
        else:
            rec_support = 0.01

        rec_confidence = 0.7 if rows < 2000 else 0.8

        # 推荐非参数检验组合
        recommend_tests = []
        if len(categorical_cols) >= 2:
            recommend_tests.append('chi2')
        if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
            recommend_tests.append('mannwhitney')
        if len(numeric_cols) >= 2:
            recommend_tests.append('ks')

        profile = {
            'rows': rows,
            'cols': cols,
            'columns': list(df.columns),
            'numeric_cols': numeric_cols,
            'categorical_cols': categorical_cols,
        }

        recommendations = {
            'min_support': round(rec_support, 3),
            'min_confidence': round(rec_confidence, 3),
            'min_lift': 1.0,
            'p_value_threshold': 0.05,
            'suggested_tests': recommend_tests,
            'summary_text': _build_recommend_summary(rows, cols, numeric_cols, categorical_cols, rec_support, rec_confidence, 0.05, recommend_tests),
            'overall_score': assessment['overall_score']
        }
        from services.algorithm_service import algorithm_service
        mining_readiness = algorithm_service.assess_mining_suitability(df, recommendations)

        return create_success_response({
            'profile': profile,
            'recommendations': recommendations,
            'assessment': assessment,
            'mining_readiness': mining_readiness
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def _build_recommend_summary(rows, cols, num_cols, cat_cols, supp, conf, p, tests):
    """生成一段给前端直接展示的自然语言说明。"""
    parts = [
        f"当前数据包含 {rows} 行、{cols} 列，其中数值型 {len(num_cols)} 列、分类型 {len(cat_cols)} 列。",
        f"建议从最小支持度约 {supp:.2f}、最小置信度约 {conf:.2f} 开始挖掘关联规则。",
        f"显著性检验建议使用 P 值阈值 {p:.2f}。"
    ]
    if tests:
        mapping = {
            'chi2': '卡方检验 (Chi-Square)',
            'mannwhitney': 'Mann-Whitney U 检验',
            'ks': 'Kolmogorov-Smirnov 检验'
        }
        pretty = [mapping.get(t, t) for t in tests]
        parts.append("可优先尝试的非参数检验包括：" + "、".join(pretty) + "。")
    return " ".join(parts)


# =======================================================
# 👇 新增增强功能端点
# =======================================================

@data_bp.route('/import_from_source', methods=['POST'])
@handle_app_exception
def import_from_source():
    """从多种数据源导入数据"""
    try:
        source_config = request.json
        
        if not source_config:
            raise ValidationException("缺少数据源配置")
        
        source_type = source_config.get('type')
        
        if source_type == 'file':
            df = data_import_service.import_from_file(
                source_config.get('path'),
                **source_config.get('options', {})
            )
        elif source_type == 'database':
            df = data_import_service.import_from_database(
                source_config.get('connection'),
                source_config.get('query')
            )
        elif source_type == 'api':
            df = data_import_service.import_from_api(source_config)
        else:
            raise ValidationException(f"不支持的数据源类型: {source_type}")
        
        # 更新全局状态
        global_state.set_current_data(df, f"imported_{source_type}")
        data_model_instance.current_data = df
        data_model_instance.current_path = f"imported_{source_type}"
        
        return create_success_response({
            'message': f'成功从{source_type}导入数据',
            'shape': df.shape,
            'columns': list(df.columns),
            'preview': df.head(10).fillna('').to_dict(orient='records')
        })
        
    except Exception as e:
        raise DataException(f"数据导入失败: {str(e)}")


@data_bp.route('/validate_source', methods=['POST'])
@handle_app_exception
def validate_data_source():
    """验证数据源"""
    try:
        source_config = request.json
        
        if not source_config:
            raise ValidationException("缺少数据源配置")
        
        validation_result = data_import_service.validate_data_source(source_config)
        
        return create_success_response(validation_result)
        
    except Exception as e:
        raise DataException(f"数据源验证失败: {str(e)}")


@data_bp.route('/preview_source', methods=['POST'])
@handle_app_exception
def preview_data_source():
    """预览数据源"""
    try:
        source_config = request.json
        rows = request.json.get('rows', 10)
        
        if not source_config:
            raise ValidationException("缺少数据源配置")
        
        preview_result = data_import_service.preview_data(source_config, rows)
        
        return jsonify(preview_result)
        
    except Exception as e:
        raise DataException(f"数据预览失败: {str(e)}")


@data_bp.route('/enhanced_preprocessing', methods=['POST'])
@handle_app_exception
def enhanced_preprocessing():
    """增强的数据预处理"""
    try:
        req_data = request.json
        file_path = req_data.get('file_path')
        config = req_data.get('config', {})
        
        if not file_path:
            # 尝试使用当前数据
            current_data, current_path = global_state.get_current_data()
            if current_data is None:
                raise ValidationException("未找到数据，请先上传或导入数据")
            df = current_data
            file_path = current_path if isinstance(current_path, str) else "current_dataset"
        else:
            df = get_data(file_path)
        
        # 执行增强预处理
        preprocessing_result = enhanced_preprocessing_service.comprehensive_preprocessing(df, config)
        final_df = preprocessing_result.get('final_df')
        
        # 更新全局状态
        enhanced_path = f"{file_path}_enhanced"
        final_df = preprocessing_result['final_df']
        global_state.set_current_data(final_df, enhanced_path)
        data_model_instance.current_data = final_df
        data_model_instance.current_path = enhanced_path
        # 关键修复：同步写入 data_cache，否则后续 get_data 找不到虚拟路径
        now_ts = time.time()
        with data_model_instance._lock:
            data_model_instance.data_cache[enhanced_path] = (final_df, now_ts)
            data_model_instance._cache_access_times[enhanced_path] = now_ts
        
        response_result = {
            'original_shape': preprocessing_result.get('original_shape', df.shape),
            'final_shape': getattr(final_df, 'shape', preprocessing_result.get('final_shape', df.shape)),
            'steps_applied': preprocessing_result.get('steps_applied', []),
            'processing_log': preprocessing_result.get('processing_log', []),
            'success': preprocessing_result.get('success', True),
            'columns': list(final_df.columns) if isinstance(final_df, pd.DataFrame) else list(df.columns),
            'preview': (
                final_df.head(300).fillna('').to_dict(orient='records')
                if isinstance(final_df, pd.DataFrame)
                else []
            )
        }

        return create_success_response({
            'path': enhanced_path,
            'preprocessing_result': to_json_compatible(response_result)
        }, message='增强预处理完成')
        
    except Exception as e:
        raise DataException(f"增强预处理失败: {str(e)}")


@data_bp.route('/data_quality_assessment', methods=['POST'])
@handle_app_exception
def data_quality_assessment():
    """数据质量评估"""
    try:
        req_data = request.json
        file_path = req_data.get('file_path')
        
        if not file_path:
            # 尝试使用当前数据
            current_data, current_path = global_state.get_current_data()
            if current_data is None:
                raise ValidationException("未找到数据，请先上传或导入数据")
            df = current_data
        else:
            df = get_data(file_path)
        
        # 执行数据质量评估
        quality_report = enhanced_preprocessing_service.assess_data_quality(df)
        
        return create_success_response({
            'quality_report': quality_report
        })
        
    except Exception as e:
        raise DataException(f"数据质量评估失败: {str(e)}")


@data_bp.route('/get_supported_formats', methods=['GET'])
@handle_app_exception
def get_supported_formats():
    """获取支持的数据格式"""
    try:
        formats = {
            'file_formats': list(data_import_service.supported_formats),
            'database_types': ['sqlite', 'mysql', 'postgresql', 'mssql'],
            'api_formats': ['json', 'csv', 'xml'],
            'preprocessing_methods': {
                'missing_value': ['mean', 'median', 'mode', 'constant', 'knn', 'drop', 'forward_fill', 'backward_fill'],
                'outlier_detection': ['iqr', 'zscore', 'dbscan'],
                'outlier_action': ['clip', 'remove', 'transform'],
                'normalization': ['standard', 'minmax', 'robust', 'power'],
                'encoding': ['onehot', 'label', 'target'],
                'feature_selection': ['univariate', 'mutual_info'],
                'dimensionality_reduction': ['pca']
            }
        }
        
        return create_success_response(formats)
        
    except Exception as e:
        raise DataException(f"获取支持格式失败: {str(e)}")


@data_bp.route('/cache_info', methods=['GET'])
@handle_app_exception
def get_cache_info():
    """获取缓存信息"""
    try:
        cache_info = data_model_instance.get_cache_stats()
        global_cache_info = global_state.get_cache_info()
        memory_usage = global_state.get_memory_usage()
        
        return create_success_response({
            'data_model_cache': cache_info,
            'global_cache': global_cache_info,
            'memory_usage': memory_usage
        })
        
    except Exception as e:
        raise DataException(f"获取缓存信息失败: {str(e)}")


@data_bp.route('/clear_cache', methods=['POST'])
@handle_app_exception
def clear_cache():
    """清理缓存"""
    try:
        pattern = request.json.get('pattern') if request.json else None
        
        data_model_instance.clear_cache(pattern)
        global_state.clear(pattern)
        
        return create_success_response({
            'message': '缓存清理完成',
            'pattern': pattern
        })
        
    except Exception as e:
        raise DataException(f"清理缓存失败: {str(e)}")


# =======================================================
# 👇 新增示例数据集功能
# =======================================================

@data_bp.route('/sample_datasets', methods=['GET'])
@handle_app_exception
def get_sample_datasets():
    """获取可用的示例数据集列表"""
    try:
        datasets = sample_data_generator.get_available_datasets()
        return create_success_response({
            'datasets': datasets
        })
    except Exception as e:
        raise DataException(f"获取示例数据集失败: {str(e)}")


@data_bp.route('/load_sample_dataset', methods=['POST'])
@handle_app_exception
def load_sample_dataset():
    """加载示例数据集"""
    try:
        data = request.json
        dataset_type = data.get('dataset_type')
        n_samples = data.get('n_samples')
        
        if not dataset_type:
            raise ValidationException("请指定数据集类型")
        
        # 生成示例数据
        df = sample_data_generator.generate_dataset(dataset_type, n_samples)
        
        # 保存到临时文件
        temp_path = f"sample_{dataset_type}_{uuid.uuid4().hex[:8]}.csv"
        full_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), temp_path)
        df.to_csv(full_path, index=False, encoding='utf-8-sig')
        
        # 更新全局状态
        global_state.set_current_data(df, full_path)
        data_model_instance.current_data = df
        data_model_instance.current_path = full_path
        
        # 记录日志
        log_operation('load_sample_dataset', details={
            'dataset_type': dataset_type,
            'rows': len(df),
            'columns': len(df.columns),
            'path': full_path
        })
        
        return create_success_response({
            'message': f'示例数据集 "{dataset_type}" 加载成功',
            'shape': df.shape,
            'columns': list(df.columns),
            'path': full_path,
            'preview': df.head(300).fillna('').to_dict(orient='records'),
            'dataset_info': {
                'type': dataset_type,
                'rows': len(df),
                'cols': len(df.columns)
            }
        })
        
    except Exception as e:
        raise DataException(f"加载示例数据集失败: {str(e)}")
