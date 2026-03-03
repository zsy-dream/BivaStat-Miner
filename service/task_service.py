import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, List
from core.logging import logger

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.lock = threading.Lock()

    def create_task(self, name: str) -> str:
        task_id = str(uuid.uuid4())
        with self.lock:
            self.tasks[task_id] = {
                'id': task_id,
                'name': name,
                'status': 'pending',
                'progress': 0,
                'message': '任务待启动',
                'start_time': time.strftime("%Y-%m-%d %H:%M:%S"),
                'end_time': None,
                'result': None,
                'logs': []
            }
        return task_id

    def update_task(self, task_id: str, status: str = None, progress: int = None, 
                   message: str = None, result: Any = None, log: str = None):
        with self.lock:
            if task_id in self.tasks:
                if status: self.tasks[task_id]['status'] = status
                if progress is not None: self.tasks[task_id]['progress'] = progress
                if message: self.tasks[task_id]['message'] = message
                if result: self.tasks[task_id]['result'] = result
                if log: self.tasks[task_id]['logs'].append(f"{time.strftime('%H:%M:%S')} - {log}")
                
                if status in ('completed', 'failed', 'cancelled'):
                    self.tasks[task_id]['end_time'] = time.strftime("%Y-%m-%d %H:%M:%S")

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(task_id)

    def run_async(self, func, task_id: str, *args, **kwargs):
        """
        在线程池中执行异步任务。
        """
        def wrapper():
            try:
                self.update_task(task_id, status='running', message='任务执行中...')
                result = func(task_id, *args, **kwargs)
                self.update_task(task_id, status='completed', progress=100, 
                                message='任务已完成', result=result)
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                self.update_task(task_id, status='failed', message=f'任务失败: {str(e)}')
        
        self.executor.submit(wrapper)

task_manager = TaskManager()
