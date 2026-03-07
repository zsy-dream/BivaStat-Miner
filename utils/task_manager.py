import threading
import time
import uuid
import psutil
import os
import json
from datetime import datetime


class TaskManager:
    def __init__(self, storage_dir='tasks'):
        self.tasks = {}
        self.lock = threading.Lock()
        self._threads = {}  # 仅运行期线程引用，不持久化
        self._cancel_events = {}  # task_id -> threading.Event
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
        self._load_all_tasks()

    def _get_task_path(self, task_id):
        return os.path.join(self.storage_dir, f"{task_id}.json")

    def _save_task(self, task_id):
        """将单个任务持久化到磁盘"""
        if task_id not in self.tasks:
            return
        try:
            task_copy = self.tasks[task_id].copy()
            # 移除不可序列化的 params 对象（如果有的话，通常是 df）
            if 'params' in task_copy and 'df' in task_copy['params']:
                # 仅保留元数据，不保存整个 DataFrame
                p_copy = task_copy['params'].copy()
                p_copy['df_preview'] = "DataFrame in memory"
                del p_copy['df']
                task_copy['params'] = p_copy
            
            with open(self._get_task_path(task_id), 'w', encoding='utf-8') as f:
                json.dump(task_copy, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save task {task_id}: {str(e)}")

    def _load_all_tasks(self):
        """启动时从磁盘加载所有历史任务"""
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    task_id = filename[:-5]
                    with open(os.path.join(self.storage_dir, filename), 'r', encoding='utf-8') as f:
                        task = json.load(f)
                        changed = False

                        if not isinstance(task.get('metrics'), dict):
                            task['metrics'] = {
                                'processed_count': 0,
                                'total_count': 0,
                                'memory_usage': 0,
                                'estimated_time_remaining': 0
                            }
                            changed = True

                        if not task.get('updated_at'):
                            task['updated_at'] = task.get('start_time') or datetime.now().isoformat()
                            changed = True

                        # 服务重启恢复：避免“running/pending/paused”僵尸任务永久卡住
                        if task.get('status') in ('running', 'pending', 'paused'):
                            ts = datetime.now().strftime('%H:%M:%S')
                            task['status'] = 'failed'
                            task['end_time'] = datetime.now().isoformat()
                            task['error'] = '任务在服务重启后中断，请重新执行。'
                            logs = task.get('logs') or []
                            logs.append(f"[{ts}] ⚠️ 服务重启，未完成任务已自动标记为失败")
                            task['logs'] = logs[-1200:]
                            task['updated_at'] = datetime.now().isoformat()
                            changed = True

                        self.tasks[task_id] = task
                        if changed:
                            self._save_task(task_id)
        except Exception as e:
            print(f"Failed to load tasks: {str(e)}")

    def is_cancelled(self, task_id):
        """高频调用：检查任务是否已被取消。"""
        evt = self._cancel_events.get(task_id)
        if evt is not None and evt.is_set():
            return True
        task = self.tasks.get(task_id)
        return task is not None and task.get('status') == 'cancelled'

    def create_task(self, task_type, params):
        task_id = str(uuid.uuid4())
        now_iso = datetime.now().isoformat()
        self._cancel_events[task_id] = threading.Event()
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
                'updated_at': now_iso,
                'error': None,
                'result': None,
                'metrics': {
                    'processed_count': 0,
                    'total_count': 0,
                    'memory_usage': 0,
                    'estimated_time_remaining': 0
                }
            }
            self._save_task(task_id)
        return task_id

    def get_task(self, task_id):
        with self.lock:
            return self.tasks.get(task_id)

    def update_task(self, task_id, **kwargs):
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                # 若用户已取消任务，防止异步线程后续把状态覆盖回 running/completed
                current_status = task.get('status')
                requested_status = kwargs.get('status')
                if current_status == 'cancelled' and requested_status in ('running', 'pending', 'completed'):
                    kwargs = {k: v for k, v in kwargs.items() if k != 'status'}
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
                task['updated_at'] = datetime.now().isoformat()
                self._save_task(task_id)

    def start_task(self, task_id, target_func):
        with self.lock:
            if task_id not in self.tasks:
                return False
            self.tasks[task_id]['status'] = 'running'
            self.tasks[task_id]['start_time'] = datetime.now().isoformat()
            self.tasks[task_id]['updated_at'] = datetime.now().isoformat()
            self._save_task(task_id)
        
        # Start thread
        thread = threading.Thread(target=target_func, args=(task_id, self))
        thread.daemon = True
        self._threads[task_id] = thread
        thread.start()
        return True

    def reconcile_task_state(self, task_id, stale_seconds=180):
        """任务状态自愈：长时间无心跳且无线程存活的运行中任务自动转失败。"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None

            if task.get('status') not in ('running', 'pending'):
                return task

            t = self._threads.get(task_id)
            if t is not None and t.is_alive():
                return task

            updated_at = task.get('updated_at') or task.get('start_time')
            age_seconds = stale_seconds + 1
            if isinstance(updated_at, str):
                try:
                    age_seconds = (datetime.now() - datetime.fromisoformat(updated_at)).total_seconds()
                except Exception:
                    age_seconds = stale_seconds + 1

            if age_seconds >= stale_seconds:
                ts = datetime.now().strftime('%H:%M:%S')
                task['status'] = 'failed'
                task['end_time'] = datetime.now().isoformat()
                task['error'] = '任务长时间无进展，已自动终止，请重新执行。'
                logs = task.get('logs') or []
                logs.append(f"[{ts}] ⚠️ 任务长时间无心跳，已自动标记为失败")
                task['logs'] = logs[-1200:]
                task['updated_at'] = datetime.now().isoformat()
                self._save_task(task_id)
            return task

    def stop_task(self, task_id):
        # 1. 设置取消标志
        evt = self._cancel_events.get(task_id)
        if evt is not None:
            evt.set()

        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]['status'] = 'cancelled'
                self.tasks[task_id]['end_time'] = datetime.now().isoformat()
                self.tasks[task_id]['logs'].append(f"[{datetime.now().strftime('%H:%M:%S')}] 任务被用户取消")
                self.tasks[task_id]['updated_at'] = datetime.now().isoformat()
                self._save_task(task_id)

        # 2. 工作线程将在下一个 _check_cancel() / is_cancelled() 检查点自然退出
        #    不强制 kill 线程，避免线程持有锁时被杀死导致死锁

# Global instance
task_manager = TaskManager()
