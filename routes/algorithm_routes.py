from flask import Blueprint, request, jsonify, current_app, Response
from services.algorithm_service import algorithm_service
from utils.config import load_params, save_params
from utils.global_state import global_state
from models.data_model import load_data
from utils.task_manager import task_manager
from services.async_service import async_algorithm_task
from services.statistical_test_service import statistical_test_service
import os

algorithm_bp = Blueprint('algorithm_routes', __name__)


def _json_no_cache(payload, status_code=200):
    response = jsonify(payload)
    response.status_code = status_code
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


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
            results = algorithm_service.mine_association_with_diagnostics(current_data, parameters)
        else:
            return jsonify({'success': False, 'error': f'不支持的算法类型: {algorithm_type}'})
        
        # 🔥 关键修复：将结果保存到全局状态
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

        stats_config = request_params.get('stats_config')
        if isinstance(stats_config, dict):
            params['test_method'] = stats_config.get('test_method', params.get('test_method', 'auto'))
            params['p_value_threshold'] = float(stats_config.get('p_value_threshold', params.get('p_value_threshold', 0.05)))
            params['confidence_interval'] = float(stats_config.get('confidence_level', params.get('confidence_interval', 0.95)))
            params['alternative'] = stats_config.get('alternative', params.get('alternative', 'two-sided'))
        
        # 转换类型
        params['min_support'] = float(params.get('min_support', 0.1))
        params['min_confidence'] = float(params.get('min_confidence', 0.5))
        params['min_lift'] = float(params.get('min_lift', 1.0))
        params['max_len'] = int(params.get('max_len', 5))
        params['numeric_bins'] = int(params.get('numeric_bins', 5) or 5)
        params['max_columns_for_mining'] = int(params.get('max_columns_for_mining', 30) or 30)
        params['max_unique_per_categorical'] = int(params.get('max_unique_per_categorical', 50) or 50)
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
    task = task_manager.reconcile_task_state(task_id) or task_manager.get_task(task_id)
    if not task:
        return _json_no_cache({'success': False, 'error': '任务不存在'}, 404)
    
    # 如果任务完成，把结果存入 global_state 方便后续获取
    if task['status'] == 'completed' and task.get('result'):
        global_state.set_results('latest_analysis', task['result'])

    return _json_no_cache({
        'success': True,
        'task': task
    })

@algorithm_bp.route('/stop_task/<task_id>', methods=['POST'])
def stop_task(task_id):
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    if task.get('status') in ('completed', 'failed', 'cancelled', 'stopped'):
        return jsonify({'success': True, 'message': f"任务已处于终态: {task.get('status')}", 'status': task.get('status')})
    task_manager.stop_task(task_id)
    latest = task_manager.get_task(task_id) or {}
    return jsonify({'success': True, 'message': '任务取消指令已下达', 'status': latest.get('status', 'cancelled')})


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
    task = (task_manager.reconcile_task_state(last_id) or task_manager.get_task(last_id)) if last_id else None
    return _json_no_cache({
        'success': True,
        'task': {
            'task_id': last_id,
            'status': task.get('status') if task else None,
            'progress': task.get('progress') if task else None,
            'has_result': bool(task.get('result')) if task else False,
            'result': task.get('result') if task and task.get('result') else None
        } if last_id else None
    })


@algorithm_bp.route('/get_history', methods=['GET'])
def get_history():
    """获取所有历史任务列表"""
    all_tasks = []
    for tid in list(task_manager.tasks.keys()):
        task = task_manager.reconcile_task_state(tid) or task_manager.get_task(tid)
        if not task:
            continue
        all_tasks.append({
            'task_id': tid,
            'status': task.get('status'),
            'type': task.get('type'),
            'start_time': task.get('start_time'),
            'progress': task.get('progress'),
            'records': task.get('metrics', {}).get('total_count', 0),
            'rules_found': len(
                task.get('result', {}).get('association_rules')
                or task.get('result', {}).get('rules')
                or []
            ) if task.get('result') else 0
        })
    
    # 按时间倒序
    all_tasks.sort(key=lambda x: x['start_time'] or "", reverse=True)
    
    return _json_no_cache({
        'success': True,
        'tasks': all_tasks
    })


@algorithm_bp.route('/delete_task/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """从磁盘和内存中移除任务记录"""
    if task_id in task_manager.tasks:
        try:
            # 移除磁盘文件
            path = task_manager._get_task_path(task_id)
            if os.path.exists(path):
                os.remove(path)
            # 移除内存
            del task_manager.tasks[task_id]
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Task not found'}), 404


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
                    progress=10,
                    metrics={
                        'total_count': int(len(params.get('df')) if params.get('df') is not None else 0),
                        'processed_count': 0,
                        'estimated_time_remaining': 1
                    },
                    logs=['开始执行非参数统计检验...']
                )

                if (manager.get_task(task_id) or {}).get('status') == 'cancelled':
                    manager.update_task(task_id, logs=['统计检验任务已取消'])
                    return
                
                # 执行检验
                results = statistical_test_service.perform_statistical_tests(
                    df=params['df'],
                    target_col=params.get('target_col'),
                    feature_cols=params.get('feature_cols'),
                    test_methods=params.get('test_methods', ['mann_whitney', 'chi2', 'spearman']),
                    p_value_threshold=params.get('p_value_threshold', 0.05)
                )

                if (manager.get_task(task_id) or {}).get('status') == 'cancelled':
                    manager.update_task(task_id, logs=['统计检验任务已取消'])
                    return
                
                manager.update_task(task_id,
                    status='completed',
                    step_update={'index': 0, 'status': 'completed'},
                    progress=100,
                    metrics={'processed_count': int(len(params.get('df')) if params.get('df') is not None else 0), 'estimated_time_remaining': 0},
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