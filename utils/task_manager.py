import threading
import time
import uuid
import psutil
from datetime import datetime

class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.lock = threading.Lock()

    def create_task(self, task_type, params):
        task_id = str(uuid.uuid4())
        with self.lock:
            self.tasks[task_id] = {
                'id': task_id,
                'type': task_type,
                'params': params,
                'status': 'pending',  # pending, running, paused, completed, failed, cancelled
                'progress': 0,
                'steps': [
                    {'name': '数据加载', 'status': 'pending'},
                    {'name': '数据预处理', 'status': 'pending'},
                    {'name': '关联规则挖掘', 'status': 'pending'},
                    {'name': '统计检验', 'status': 'pending'},
                    {'name': '结果生成', 'status': 'pending'}
                ],
                'current_step_index': 0,
                'logs': [],
                'start_time': None,
                'end_time': None,
                'error': None,
                'result': None,
                'metrics': {
                    'processed_count': 0,
                    'total_count': 0,
                    'memory_usage': 0,
                    'estimated_time_remaining': 0
                }
            }
        return task_id

    def get_task(self, task_id):
        with self.lock:
            return self.tasks.get(task_id)

    def update_task(self, task_id, **kwargs):
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                for k, v in kwargs.items():
                    if k == 'logs':
                        # Append logs with timestamp
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        new_logs = [f"[{timestamp}] {log}" for log in v]
                        task['logs'].extend(new_logs)
                        # 防止日志无限增长导致接口返回越来越慢/页面越来越卡
                        if len(task['logs']) > 1200:
                            task['logs'] = task['logs'][-1200:]
                    elif k == 'step_update':
                        # Update specific step status
                        step_idx = v.get('index')
                        status = v.get('status')
                        if 0 <= step_idx < len(task['steps']):
                            task['steps'][step_idx]['status'] = status
                            if status == 'running':
                                task['current_step_index'] = step_idx
                    elif k == 'metrics':
                        # 关键修复：metrics 需要“合并更新”，不能整块覆盖
                        if not isinstance(task.get('metrics'), dict):
                            task['metrics'] = {}
                        if isinstance(v, dict):
                            task['metrics'].update(v)
                    else:
                        task[k] = v

    def start_task(self, task_id, target_func):
        with self.lock:
            if task_id not in self.tasks:
                return False
            self.tasks[task_id]['status'] = 'running'
            self.tasks[task_id]['start_time'] = datetime.now().isoformat()
        
        # Start thread
        thread = threading.Thread(target=target_func, args=(task_id, self))
        thread.daemon = True
        thread.start()
        return True

    def stop_task(self, task_id):
        # Note: True cancellation in threads is hard, we usually set a flag
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]['status'] = 'cancelled'
                self.tasks[task_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] 任务被用户取消")

# Global instance
task_manager = TaskManager()
