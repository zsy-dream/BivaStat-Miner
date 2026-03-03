from flask import Blueprint, request, jsonify, current_app, Response
from services.algorithm_service import mine_association
from models.rule_model import filter_rules, sort_rules
from utils.config import load_params, save_params
from utils.global_state import global_state
from models.data_model import load_data
from utils.task_manager import task_manager
from services.async_service import async_algorithm_task
from services.statistical_test_service import statistical_test_service
import pandas as pd
import os

algorithm_bp = Blueprint('algorithm_routes', __name__)


@algorithm_bp.route('/run_algorithm', methods=['POST'])
def run_algorithm():
    try:
        data = request.json
        algorithm_type = data.get('algorithm_type', 'apriori')
        parameters = data.get('parameters', {})
        
        # 获取当前数据
        from models.data_model import data_model_instance
        current_data = data_model_instance.current_data
        
        if current_data is None:
            return jsonify({'success': False, 'error': '请先上传并预处理数据'})
        
        # 运行算法 - 修复文件引用
        if algorithm_type == 'apriori' or algorithm_type == 'fp_growth':
            from services.algorithm_service import mine_association
            rules = mine_association(current_data, parameters)
            
            # 构建完整结果
            results = {
                'summary': {
                    'total_rules': len(rules),
                    'significant_rules': len([r for r in rules if r.get('confidence', 0) > 0.7]),
                    'avg_confidence': sum(r.get('confidence', 0) for r in rules) / len(rules) if rules else 0,
                    'avg_support': sum(r.get('support', 0) for r in rules) / len(rules) if rules else 0
                },
                'association_rules': rules
            }
        else:
            return jsonify({'success': False, 'error': f'不支持的算法类型: {algorithm_type}'})
        
        # 🔥 关键修复：将结果保存到全局状态
        from utils.global_state import global_state
        global_state.set_results('latest_analysis', results)
        
        return jsonify({
            'success': True, 
            'message': '算法运行完成',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =======================================================
# 👇 新增异步任务接口
# =======================================================

@algorithm_bp.route('/start_task', methods=['POST'])
def start_task():
    try:
        req_json = request.get_json() or {}
        
        # 获取文件路径 (这里简化处理，假设前端先调用上传，然后这里只传路径，或者后端自己找最新)
        # 更好的做法是前端传 file_path
        # 优先使用“当前数据集”（可能是清洗后的 *.cleaned 虚拟路径）
        file_path = req_json.get('file_path') or getattr(global_state, 'current_path', None)
        if not file_path:
            # 尝试找最新的
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            if os.path.exists(upload_folder):
                files = [
                    os.path.join(upload_folder, f)
                    for f in os.listdir(upload_folder)
                    if not f.startswith('.')
                ]
                if files:
                    file_path = max(files, key=os.path.getmtime)
        
        if not file_path:
            return jsonify({'success': False, 'error': '未找到数据文件'}), 400

        # 参数准备
        default_params = load_params()
        request_params = req_json.get('params', {})
        params = {**default_params, **request_params}
        
        # 转换类型
        params['min_support'] = float(params.get('min_support', 0.1))
        params['min_confidence'] = float(params.get('min_confidence', 0.5))
        params['min_lift'] = float(params.get('min_lift', 1.0))
        params['max_len'] = int(params.get('max_len', 5))
        params['data_path'] = file_path # 传递路径给异步任务

        # 创建任务
        task_id = task_manager.create_task('algorithm_mining', params)
        # 记录最新任务，方便结果页兜底追踪
        global_state.last_task_id = task_id
        # ✅ 关键修复：启动新任务时清理旧结果，避免“中途取消后结果页显示上一次任务”
        try:
            global_state.set_results('latest_analysis', None)
        except Exception:
            pass
        
        # 启动任务
        if task_manager.start_task(task_id, async_algorithm_task):
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': '任务已启动'
            })
        else:
            return jsonify({'success': False, 'error': '任务启动失败'}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@algorithm_bp.route('/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    # 如果任务完成，把结果存入 global_state 方便后续获取
    if task['status'] == 'completed' and task.get('result'):
        global_state.set_results('latest_analysis', task['result'])

    return jsonify({
        'success': True,
        'task': task
    })

@algorithm_bp.route('/stop_task/<task_id>', methods=['POST'])
def stop_task(task_id):
    task_manager.stop_task(task_id)
    return jsonify({'success': True, 'message': '任务取消指令已下达'})


@algorithm_bp.route('/export_logs/<task_id>', methods=['GET'])
def export_logs(task_id):
    """导出任务实时日志为 txt"""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    logs = task.get('logs', [])
    content = "\n".join(logs) if logs else ""
    filename = f"task_{task_id}_logs.txt"
    return Response(
        content,
        mimetype='text/plain; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@algorithm_bp.route('/last_task', methods=['GET'])
def last_task():
    """返回最近一次启动的任务信息（给结果页兜底对接用）"""
    last_id = getattr(global_state, 'last_task_id', None)
    task = task_manager.get_task(last_id) if last_id else None
    return jsonify({
        'success': True,
        'task': {
            'task_id': last_id,
            'status': task.get('status') if task else None,
            'progress': task.get('progress') if task else None,
            'has_result': bool(task.get('result')) if task else False
        } if last_id else None
    })


@algorithm_bp.route('/statistical_test', methods=['POST'])
def statistical_test():
    """执行非参数统计检验"""
    try:
        data = request.json
        test_methods = data.get('test_methods', ['mann_whitney', 'chi2', 'spearman'])
        target_col = data.get('target_col')
        feature_cols = data.get('feature_cols')
        p_value_threshold = float(data.get('p_value_threshold', 0.05))
        
        # 获取当前数据
        from models.data_model import data_model_instance
        current_data = data_model_instance.current_data
        
        if current_data is None:
            return jsonify({'success': False, 'error': '请先上传并预处理数据'}), 400
        
        # 执行统计检验
        results = statistical_test_service.perform_statistical_tests(
            df=current_data,
            target_col=target_col,
            feature_cols=feature_cols,
            test_methods=test_methods,
            p_value_threshold=p_value_threshold
        )
        
        if 'error' in results:
            return jsonify({'success': False, 'error': results['error']}), 400
        
        # 保存结果到全局状态
        global_state.set_results('statistical_tests', results)
        
        return jsonify({
            'success': True,
            'message': '统计检验完成',
            'results': results
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@algorithm_bp.route('/run_statistical_test_async', methods=['POST'])
def run_statistical_test_async():
    """异步执行统计检验任务"""
    try:
        data = request.json or {}
        
        # 获取当前数据
        from models.data_model import data_model_instance
        current_data = data_model_instance.current_data
        
        if current_data is None:
            return jsonify({'success': False, 'error': '请先上传并预处理数据'}), 400
        
        # 创建异步任务
        params = {
            'task_type': 'statistical_test',
            'test_methods': data.get('test_methods', ['mann_whitney', 'chi2', 'spearman']),
            'target_col': data.get('target_col'),
            'feature_cols': data.get('feature_cols'),
            'p_value_threshold': float(data.get('p_value_threshold', 0.05)),
            'df': current_data
        }
        
        task_id = task_manager.create_task('statistical_test', params)
        global_state.last_task_id = task_id
        
        # 启动异步任务
        def async_statistical_test(task_id, manager):
            try:
                task = manager.get_task(task_id)
                params = task['params']
                
                manager.update_task(task_id, 
                    step_update={'index': 0, 'status': 'running'},
                    logs=['开始执行非参数统计检验...']
                )
                
                # 执行检验
                results = statistical_test_service.perform_statistical_tests(
                    df=params['df'],
                    target_col=params.get('target_col'),
                    feature_cols=params.get('feature_cols'),
                    test_methods=params.get('test_methods', ['mann_whitney', 'chi2', 'spearman']),
                    p_value_threshold=params.get('p_value_threshold', 0.05)
                )
                
                manager.update_task(task_id,
                    status='completed',
                    step_update={'index': 0, 'status': 'completed'},
                    progress=100,
                    result=results,
                    logs=['统计检验任务完成']
                )
                
                # 保存到全局状态
                global_state.set_results('statistical_tests', results)
                
            except Exception as e:
                manager.update_task(task_id,
                    status='failed',
                    error=str(e),
                    logs=[f'任务执行出错: {str(e)}']
                )
        
        if task_manager.start_task(task_id, async_statistical_test):
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': '统计检验任务已启动'
            })
        else:
            return jsonify({'success': False, 'error': '任务启动失败'}), 500
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# 保持原来的 set_params 和 get_params 不变
@algorithm_bp.route('/set_params', methods=['POST'])
def set_params():
    try:
        params = request.get_json()
        save_params(params)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@algorithm_bp.route('/get_params', methods=['GET'])
def get_params():
    return jsonify(load_params())