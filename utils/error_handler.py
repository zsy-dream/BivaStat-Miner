import logging
import traceback
import os
from logging.handlers import RotatingFileHandler
from functools import wraps
from flask import jsonify
from typing import Dict, Any, Optional

# 配置日志 - 控制台 + 文件
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 避免重复添加处理器
if not logger.handlers:
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（10MB滚动，保留5个备份）
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

class AppException(Exception):
    """应用基础异常类"""
    def __init__(self, message: str, error_code: str = "APP_ERROR", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

class DataException(AppException):
    """数据相关异常"""
    def __init__(self, message: str, error_code: str = "DATA_ERROR", status_code: int = 400):
        super().__init__(message, error_code, status_code)

class ValidationException(AppException):
    """验证异常"""
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR", status_code: int = 400):
        super().__init__(message, error_code, status_code)

class FileException(AppException):
    """文件相关异常"""
    def __init__(self, message: str, error_code: str = "FILE_ERROR", status_code: int = 400):
        super().__init__(message, error_code, status_code)

class SecurityException(AppException):
    """安全相关异常"""
    def __init__(self, message: str, error_code: str = "SECURITY_ERROR", status_code: int = 403):
        super().__init__(message, error_code, status_code)

class ResourceNotFoundException(AppException):
    """资源未找到异常"""
    def __init__(self, message: str, error_code: str = "RESOURCE_NOT_FOUND", status_code: int = 404):
        super().__init__(message, error_code, status_code)

class TaskException(AppException):
    """任务执行异常"""
    def __init__(self, message: str):
        super().__init__(message, "TASK_ERROR", 500)

def handle_app_exception(func):
    """统一异常处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppException as e:
            logger.warning(f"应用异常: {e.error_code} - {e.message}")
            return jsonify({
                'success': False,
                'error_code': e.error_code,
                'error': e.message
            }), e.status_code
        except FileNotFoundError as e:
            logger.error(f"文件未找到: {str(e)}")
            return jsonify({
                'success': False,
                'error_code': 'FILE_NOT_FOUND',
                'error': '请求的文件不存在'
            }), 404
        except PermissionError as e:
            logger.error(f"权限错误: {str(e)}")
            return jsonify({
                'success': False,
                'error_code': 'PERMISSION_DENIED',
                'error': '权限不足'
            }), 403
        except ValueError as e:
            logger.error(f"数据格式错误: {str(e)}")
            return jsonify({
                'success': False,
                'error_code': 'INVALID_DATA',
                'error': '数据格式不正确'
            }), 400
        except MemoryError as e:
            logger.error(f"内存不足: {str(e)}")
            return jsonify({
                'success': False,
                'error_code': 'MEMORY_ERROR',
                'error': '内存不足，请尝试处理较小的数据集'
            }), 507
        except Exception as e:
            logger.error(f"未处理的异常: {str(e)}")
            logger.debug(f"异常堆栈: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'error': '服务器内部错误，请稍后重试'
            }), 500
    return wrapper

def create_success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """创建统一成功响应"""
    response = {
        'success': True,
        'message': message
    }
    if data is not None:
        response['data'] = data
    return response

def create_error_response(error_code: str, message: str, status_code: int = 500) -> tuple:
    """创建统一错误响应"""
    return jsonify({
        'success': False,
        'error_code': error_code,
        'error': message
    }), status_code

def log_operation(operation: str, user_id: Optional[str] = None, details: Optional[Dict] = None):
    """记录操作日志"""
    log_data = {
        'operation': operation,
        'user_id': user_id,
        'details': details or {}
    }
    logger.info(f"操作记录: {log_data}")
