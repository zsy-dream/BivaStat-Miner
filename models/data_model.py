import os
import pandas as pd
import logging
import numpy as np
import threading
import time
from typing import Dict, Optional, Tuple
from utils.error_handler import DataException, ValidationException

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataModel:
    """改进的数据模型，支持缓存限制和性能优化"""
    
    def __init__(self, max_cache_size: int = 10, max_memory_mb: int = 512):
        self.data_cache: Dict[str, Tuple[pd.DataFrame, float]] = {}  # (data, timestamp)
        self.current_data: Optional[pd.DataFrame] = None
        self.current_path: Optional[str] = None
        self._lock = threading.RLock()
        
        # 缓存限制
        self.max_cache_size = max_cache_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache_access_times = {}  # LRU缓存访问时间
        
        # 编码检测配置
        self.encodings_to_try = ['utf-8', 'gbk', 'gb18030', 'cp1252', 'latin1']
        
        logger.info(f"DataModel初始化完成，最大缓存条目: {max_cache_size}, 最大内存: {max_memory_mb}MB")

    def _estimate_dataframe_size(self, df: pd.DataFrame) -> int:
        """估算DataFrame内存占用"""
        try:
            return df.memory_usage(deep=True).sum()
        except Exception:
            return len(df) * len(df.columns) * 8  # 保守估算

    def _cleanup_cache(self) -> None:
        """清理缓存以保持在限制范围内"""
        with self._lock:
            # 按LRU顺序清理
            while len(self.data_cache) > self.max_cache_size:
                self._evict_lru()
            
            # 检查内存使用
            total_memory = sum(self._estimate_dataframe_size(df) for df, _ in self.data_cache.values())
            while total_memory > self.max_memory_bytes and self.data_cache:
                self._evict_lru()
                total_memory = sum(self._estimate_dataframe_size(df) for df, _ in self.data_cache.values())

    def _evict_lru(self) -> None:
        """移除最少使用的缓存条目"""
        if not self._cache_access_times:
            return
        
        lru_key = min(self._cache_access_times.keys(), key=lambda k: self._cache_access_times[k])
        self.data_cache.pop(lru_key, None)
        self._cache_access_times.pop(lru_key, None)
        logger.debug(f"清理缓存条目: {lru_key}")

    def load_data(self, path: str) -> pd.DataFrame:
        """加载数据，支持缓存和错误处理"""
        if not os.path.exists(path):
            raise DataException(f"找不到文件: {path}")

        # 检查文件大小
        file_size = os.path.getsize(path)
        if file_size == 0:
            raise ValidationException("文件为空")
        
        if file_size > 100 * 1024 * 1024:  # 100MB
            logger.warning(f"文件较大: {file_size / (1024*1024):.1f}MB")

        file_ext = os.path.splitext(path)[1].lower()
        
        try:
            data = None
            error_messages = []
            
            if file_ext == '.csv':
                # 改进的编码检测
                for encoding in self.encodings_to_try:
                    try:
                        logger.debug(f"尝试使用 {encoding} 编码读取文件: {path}")
                        data = pd.read_csv(
                            path,
                            encoding=encoding,
                            sep=None,
                            engine='python',
                            on_bad_lines='skip',
                        )
                        logger.info(f"成功使用 {encoding} 编码读取文件: {path}")
                        break
                    except UnicodeDecodeError as e:
                        error_messages.append(f"{encoding}: {str(e)}")
                        continue
                    except pd.errors.EmptyDataError:
                        raise ValidationException("CSV文件为空或格式不正确")
                    except pd.errors.ParserError as e:
                        raise DataException(f"CSV解析错误: {str(e)}")

                if data is None:
                    raise DataException(f"所有编码都尝试失败。错误详情: {'; '.join(error_messages)}")

            elif file_ext in ['.xlsx', '.xls']:
                try:
                    # 优化Excel读取
                    data = pd.read_excel(
                        path, 
                        engine='openpyxl' if file_ext == '.xlsx' else 'xlrd',
                        dtype_backend='pyarrow'  # 更高效的数据类型
                    )
                except ImportError as ie:
                    raise DataException(
                        "读取Excel失败：缺少依赖库。请安装: pip install openpyxl xlrd"
                    ) from ie
                except Exception as e:
                    raise DataException(f'读取Excel文件出错: {e}') from e
                    
            elif file_ext == '.json':
                try:
                    data = pd.read_json(path, orient='records', lines=True if path.endswith('.jsonl') else False)
                except ValueError as e:
                    raise DataException(f"JSON格式错误: {str(e)}")
            else:
                raise ValidationException(f"不支持的文件类型: {file_ext}")

            # 数据验证和清理
            if data is not None:
                if data.empty:
                    raise ValidationException("文件内容为空")
                
                # 基础预处理
                original_shape = data.shape
                
                # 去除全空的列
                data = data.dropna(how='all', axis=1)
                
                # 去除完全重复的行
                data = data.drop_duplicates()
                
                # 仅对文本列填充空字符串，保留数值列的 NaN，避免后续数值计算/转换报错
                object_cols = data.select_dtypes(include=['object', 'string']).columns
                if len(object_cols) > 0:
                    data[object_cols] = data[object_cols].fillna('')
                
                logger.info(f"数据加载完成: {path}, 原始形状: {original_shape}, 清理后: {data.shape}")
                
                # 更新缓存
                with self._lock:
                    self.data_cache[path] = (data, time.time())
                    self._cache_access_times[path] = time.time()
                    self.current_data = data
                    self.current_path = path
                    self._cleanup_cache()
                
                return data
            else:
                raise DataException("数据加载失败")

        except Exception as e:
            if isinstance(e, (DataException, ValidationException)):
                raise
            logger.error(f"加载数据失败: {path}, 错误: {str(e)}")
            raise DataException(f"加载数据失败: {str(e)}")

    def get_data(self, path: str) -> pd.DataFrame:
        """从缓存获取数据，如果不存在则加载"""
        with self._lock:
            if path in self.data_cache:
                data, timestamp = self.data_cache[path]
                self._cache_access_times[path] = time.time()  # 更新访问时间
                self.current_data = data
                self.current_path = path
                logger.debug(f"从缓存获取数据: {path}")
                return data
        
        return self.load_data(path)

    def validate_data(self, data: pd.DataFrame) -> bool:
        """验证数据有效性"""
        if data is None or data.empty:
            return False
        
        # 检查是否有有效的列
        if len(data.columns) == 0:
            return False
        
        # 检查是否所有列都是空的
        if all(data[col].isna().all() for col in data.columns):
            return False
        
        return True

    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        with self._lock:
            total_memory = sum(self._estimate_dataframe_size(df) for df, _ in self.data_cache.values())
            return {
                'cache_size': len(self.data_cache),
                'max_cache_size': self.max_cache_size,
                'memory_usage_mb': total_memory / (1024 * 1024),
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
                'cached_files': list(self.data_cache.keys()),
                'current_file': self.current_path
            }

    def clear_cache(self, pattern: Optional[str] = None) -> None:
        """清理缓存"""
        with self._lock:
            if pattern is None:
                self.data_cache.clear()
                self._cache_access_times.clear()
                logger.info("清理所有缓存")
            else:
                keys_to_remove = [k for k in self.data_cache.keys() if pattern in k]
                for key in keys_to_remove:
                    self.data_cache.pop(key, None)
                    self._cache_access_times.pop(key, None)
                logger.info(f"清理匹配 '{pattern}' 的缓存条目: {len(keys_to_remove)}")

    def preload_data(self, path: str) -> bool:
        """预加载数据到缓存"""
        try:
            self.load_data(path)
            return True
        except Exception as e:
            logger.error(f"预加载失败: {path}, 错误: {str(e)}")
            return False


# =======================================================
# 👇 导出实例
# =======================================================
data_model_instance = DataModel()
load_data = data_model_instance.load_data
get_data = data_model_instance.get_data
validate_data = data_model_instance.validate_data
