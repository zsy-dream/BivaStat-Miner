import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class GlobalState:
    """线程安全的全局状态管理器"""
    
    def __init__(self):
        self._results = {}
        self._current_data = None
        self._current_path = None
        self._last_task_id = None
        self._lock = threading.RLock()  # 使用可重入锁
        self._cache_timestamps = {}  # 缓存时间戳
        self._cache_ttl = 3600  # 缓存TTL：1小时
        
        # 性能监控
        self._operation_count = 0
        self._last_cleanup = time.time()

    def set_results(self, key: str, value: Any) -> None:
        """线程安全地设置结果"""
        with self._lock:
            self._results[key] = value
            self._cache_timestamps[key] = time.time()
            self._operation_count += 1
            self._maybe_cleanup_cache()

    def get_results(self, key: str, default: Any = None) -> Any:
        """线程安全地获取结果"""
        with self._lock:
            # 检查缓存是否过期
            if key in self._cache_timestamps:
                if time.time() - self._cache_timestamps[key] > self._cache_ttl:
                    self._remove_expired_entry(key)
                    return default
            return self._results.get(key, default)

    def set_current_data(self, data: Any, path: Optional[str] = None) -> None:
        """线程安全地设置当前数据"""
        with self._lock:
            self._current_data = data
            self._current_path = path
            self._cache_timestamps['current_data'] = time.time()
            self._operation_count += 1

    def get_current_data(self) -> tuple[Any, Optional[str]]:
        """线程安全地获取当前数据"""
        with self._lock:
            # 检查缓存是否过期
            if 'current_data' in self._cache_timestamps:
                if time.time() - self._cache_timestamps['current_data'] > self._cache_ttl:
                    self._current_data = None
                    self._current_path = None
                    del self._cache_timestamps['current_data']
            return self._current_data, self._current_path

    def set_last_task_id(self, task_id: str) -> None:
        """线程安全地设置最后任务ID"""
        with self._lock:
            self._last_task_id = task_id

    def get_last_task_id(self) -> Optional[str]:
        """线程安全地获取最后任务ID"""
        with self._lock:
            return self._last_task_id

    @property
    def last_task_id(self) -> Optional[str]:
        """property 代理，兼容历史代码中的 global_state.last_task_id 直接访问"""
        return self.get_last_task_id()

    @last_task_id.setter
    def last_task_id(self, value: Optional[str]) -> None:
        self.set_last_task_id(value)

    def clear(self, pattern: Optional[str] = None) -> None:
        """清理状态，支持模式匹配"""
        with self._lock:
            if pattern is None:
                # 清理所有
                self._results.clear()
                self._cache_timestamps.clear()
                self._current_data = None
                self._current_path = None
                self._last_task_id = None
            else:
                # 按模式清理
                keys_to_remove = [k for k in self._results.keys() if pattern in k]
                for key in keys_to_remove:
                    self._results.pop(key, None)
                    self._cache_timestamps.pop(key, None)

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        with self._lock:
            return {
                'total_entries': len(self._results),
                'operation_count': self._operation_count,
                'last_cleanup': self._last_cleanup,
                'cache_ttl': self._cache_ttl,
                'entries': list(self._results.keys())
            }

    def _remove_expired_entry(self, key: str) -> None:
        """移除过期条目"""
        self._results.pop(key, None)
        self._cache_timestamps.pop(key, None)

    def _maybe_cleanup_cache(self) -> None:
        """定期清理过期缓存"""
        current_time = time.time()
        if current_time - self._last_cleanup > 300:  # 5分钟清理一次
            expired_keys = [
                k for k, ts in self._cache_timestamps.items()
                if current_time - ts > self._cache_ttl
            ]
            for key in expired_keys:
                self._remove_expired_entry(key)
            self._last_cleanup = current_time

    def set_cache_ttl(self, ttl_seconds: int) -> None:
        """设置缓存TTL"""
        with self._lock:
            self._cache_ttl = ttl_seconds

    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        with self._lock:
            # 准确计算 DataFrame 内存占用
            current_data_size = 0
            if self._current_data is not None:
                try:
                    current_data_size = self._current_data.memory_usage(deep=True).sum()
                except Exception:
                    current_data_size = 0
            
            # 计算所有缓存结果的内存
            results_size = 0
            for key, value in self._results.items():
                try:
                    if hasattr(value, 'memory_usage'):
                        results_size += value.memory_usage(deep=True).sum()
                    else:
                        results_size += 0
                except Exception:
                    results_size += 0
            
            return {
                'results_size_bytes': results_size,
                'current_data_size_bytes': current_data_size,
                'cache_entries': len(self._results),
                'total_estimated_mb': round((results_size + current_data_size) / (1024 * 1024), 2)
            }

# 创建一个全局实例
global_state = GlobalState()