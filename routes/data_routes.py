from flask import Blueprint, request, jsonify, current_app, send_file
import os
import uuid
import time
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

# 设置日志
logger = logging.getLogger(__name__)

data_bp = Blueprint('data_routes', __name__)

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
        'preview': current_data.head(10).fillna('').to_dict(orient='records')
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
            'preview': df.head().fillna('').to_dict(orient='records')
        })

    except Exception as e:
        # 清理上传的文件
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.warning(f"清理失败文件: {file_path}")
        raise


@data_bp.route('/preview_data', methods=['POST'])
def preview_data():
    """获取数据预览信息（列名、缺失值、类型等）"""
    try:
        data = request.json
        file_path = data.get('file_path')
        if not file_path:
            return jsonify({'error': '未提供文件路径'}), 400
            
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
            
        return jsonify({
            'success': True,
            'columns_info': columns_info,
            'shape': df.shape,
            'preview': df.head(10).fillna('NaN').to_dict(orient='records')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@data_bp.route('/preprocess_data', methods=['POST'])
def preprocess_data():
    """执行数据清洗与预处理（缺失值、异常值、标准化、变量变换等）"""
    try:
        req_data = request.json
        file_path = req_data.get('file_path')
        options = req_data.get('options', {})
        
        if not file_path:
            return jsonify({'error': '未提供文件路径'}), 400
            
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
        # 为了不覆盖原始数据，建议保存为新文件，但为了 demo 方便，我们更新缓存 key 为 cleaned_path
        cleaned_path = file_path + ".cleaned" # 虚拟路径
        from models.data_model import data_model_instance
        # 关键修复：DataModel.data_cache 的 value 结构是 (df, timestamp)，不能直接塞 DataFrame
        now_ts = time.time()
        try:
            lock = getattr(data_model_instance, "_lock", None)
            if lock:
                lock.acquire()
            data_model_instance.data_cache[cleaned_path] = (cleaned_df, now_ts)
            if hasattr(data_model_instance, "_cache_access_times") and isinstance(getattr(data_model_instance, "_cache_access_times"), dict):
                data_model_instance._cache_access_times[cleaned_path] = now_ts
            # 保持缓存约束（LRU/内存上限）
            if hasattr(data_model_instance, "_cleanup_cache"):
                data_model_instance._cleanup_cache()
        finally:
            if 'lock' in locals() and lock:
                lock.release()
        data_model_instance.current_data = cleaned_df
        data_model_instance.current_path = cleaned_path
        global_state.current_data = cleaned_df
        global_state.current_path = cleaned_path
        
        return jsonify({
            'success': True,
            'message': '数据清洗完成',
            'cleaned_path': cleaned_path, # 前端下次用这个路径请求分析
            'shape_before': df.shape,
            'shape_after': cleaned_df.shape,
            'preview': cleaned_df.head(10).fillna('NaN').to_dict(orient='records')
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@data_bp.route('/quality_report', methods=['POST'])
def quality_report():
    """数据质量评估：缺失值分布、基础统计、告警信息"""
    try:
        req = request.get_json() or {}
        file_path = req.get('file_path')
        if not file_path:
            return jsonify({'success': False, 'error': '未提供文件路径'}), 400

        df = get_data(file_path)
        if df is None or df.empty:
            return jsonify({'success': False, 'error': '数据为空'}), 400

        # 使用服务层能力生成质量报告
        profile = data_service.calculate_data_profile(df)
        validation = data_service.validate_data_integrity(df)

        missing_values = profile.get('missing_values', {})
        # 取缺失最多的前 12 列做图（避免太挤）
        sorted_missing = sorted(missing_values.items(), key=lambda x: x[1], reverse=True)
        top_missing = sorted_missing[:12]

        total_cells = int(df.shape[0] * df.shape[1]) if df.shape[0] and df.shape[1] else 0
        total_missing = int(sum(missing_values.values())) if missing_values else 0
        # 不要过度四舍五入：小缺失率（例如 0.02%）在前端 *100 后很容易显示成 0.0%
        missing_rate = (total_missing / total_cells) if total_cells else 0.0

        return jsonify({
            'success': True,
            'summary': {
                'rows': int(df.shape[0]),
                'cols': int(df.shape[1]),
                'total_missing': total_missing,
                # 保留更高精度给前端展示/计算
                'missing_rate': round(float(missing_rate), 8),
                'warnings': validation.get('warnings', []),
                'errors': validation.get('errors', []),
            },
            'missing_chart': {
                'labels': [k for k, _ in top_missing],
                'values': [int(v) for _, v in top_missing]
            },
            'profile': {
                'dtypes': profile.get('dtypes', {}),
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@data_bp.route('/export_current', methods=['GET'])
def export_current():
    """
    将当前数据集（上传或清洗后的 latest 版本）导出为文件，供用户下载。
    这也是后续算法/报告所依赖的数据“落盘版本”。
    """
    try:
        # 1. 获取当前数据：优先 global_state，其次 data_model_instance
        df = getattr(global_state, 'current_data', None)
        if df is None or getattr(df, 'empty', True):
            df = getattr(data_model_instance, 'current_data', None)

        if df is None or getattr(df, 'empty', True):
            return jsonify({'success': False, 'error': '暂无可导出的数据，请先上传或完成清洗。'}), 400

        export_format = (request.args.get('format') or 'csv').strip().lower()

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        export_dir = os.path.join(base_dir, 'static', 'exports')
        os.makedirs(export_dir, exist_ok=True)

        uid = uuid.uuid4().hex
        if export_format in ('excel', 'xlsx'):
            filename = f"cleaned_data_{uid}.xlsx"
            path = os.path.join(export_dir, filename)
            df.to_excel(path, index=False)
            return send_file(path, as_attachment=True, download_name='cleaned_data.xlsx')

        # 默认导出 CSV
        if export_format in ('csv', ''):
            filename = f"cleaned_data_{uid}.csv"
            path = os.path.join(export_dir, filename)
            df.to_csv(path, index=False, encoding='utf-8-sig')
            return send_file(path, as_attachment=True, download_name='cleaned_data.csv')

        return jsonify({'success': False, 'error': f'不支持的导出格式: {export_format}'}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@data_bp.route('/profile', methods=['GET'])
def auto_profile():
    """
    针对当前数据集做一次“体检”，并给出推荐的挖掘/检验参数。
    供算法配置页和结果分析页自动读取，降低用户选参数的负担。
    """
    try:
        # 1. 获取当前数据（优先 global_state，其次 data_model_instance）
        df = getattr(global_state, 'current_data', None)
        if df is None or getattr(df, 'empty', True):
            df = getattr(data_model_instance, 'current_data', None)

        if df is None or getattr(df, 'empty', True):
            return jsonify({
                'success': False,
                'error': '暂无已加载的数据，请先上传或完成预处理。',
            }), 400

        rows, cols = map(int, df.shape)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = [c for c in df.columns if c not in numeric_cols]

        # 2. 根据样本规模和类型简单启发式推荐参数
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

        # 默认 P 阈值
        rec_p = 0.05

        profile = {
            'rows': rows,
            'cols': cols,
            'numeric_cols': numeric_cols,
            'categorical_cols': categorical_cols,
        }

        recommendations = {
            'min_support': round(rec_support, 3),
            'min_confidence': round(rec_confidence, 3),
            'min_lift': 1.0,
            'p_value_threshold': rec_p,
            'suggested_tests': recommend_tests,
            'summary_text': _build_recommend_summary(rows, cols, numeric_cols, categorical_cols, rec_support, rec_confidence, rec_p, recommend_tests),
        }

        return jsonify({
            'success': True,
            'profile': profile,
            'recommendations': recommendations,
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
        else:
            df = get_data(file_path)
        
        # 执行增强预处理
        preprocessing_result = enhanced_preprocessing_service.comprehensive_preprocessing(df, config)
        
        # 更新全局状态
        global_state.set_current_data(preprocessing_result['final_df'], file_path + "_enhanced")
        data_model_instance.current_data = preprocessing_result['final_df']
        data_model_instance.current_path = file_path + "_enhanced"
        
        return create_success_response({
            'message': '增强预处理完成',
            'preprocessing_result': preprocessing_result
        })
        
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
            'preview': df.head(10).fillna('').to_dict(orient='records'),
            'dataset_info': {
                'type': dataset_type,
                'rows': len(df),
                'cols': len(df.columns)
            }
        })
        
    except Exception as e:
        raise DataException(f"加载示例数据集失败: {str(e)}")
