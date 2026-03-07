import os
from werkzeug.utils import secure_filename
from typing import Tuple, Optional
from utils.config import config_manager

class SecurityValidator:
    """安全验证工具类"""
    
    # 允许的文件类型和对应的MIME类型
    ALLOWED_EXTENSIONS = {
        '.csv': ['text/csv', 'text/plain', 'application/csv', 'application/vnd.ms-excel', 'text/x-csv'],
        '.xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        '.xls': ['application/vnd.ms-excel', 'application/wps-office.xls'],
        '.json': ['application/json', 'text/plain']
    }
    
    # 最大文件大小 (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    # 危险文件扩展名黑名单
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', 
        '.jar', '.app', '.deb', '.pkg', '.dmg', '.rpm', '.deb', '.sh'
    }
    
    @classmethod
    def validate_filename(cls, filename: str) -> Tuple[bool, str]:
        """验证文件名安全性"""
        if not filename:
            return False, "文件名为空"
        
        # 检查文件名长度
        if len(filename) > 255:
            return False, "文件名过长"
        
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in cls.DANGEROUS_EXTENSIONS:
            return False, f"不允许的文件类型: {file_ext}"

        # 使用werkzeug的安全文件名处理
        secure_name = secure_filename(filename)
        # 如果全中文，secure_filename会返回空字串，这里做个向下兼容
        if not secure_name or secure_name == file_ext.strip('.'):
            import uuid
            secure_name = f"upload_{uuid.uuid4().hex[:8]}{file_ext}"
        else:
            if not secure_name.endswith(file_ext):
                secure_name += file_ext
        
        return True, secure_name
    
    @classmethod
    def validate_file_type(cls, filename: str, file_content: bytes) -> Tuple[bool, str]:
        """验证文件类型（通过内容检测）"""
        file_ext = os.path.splitext(filename)[1].lower()
        try:
            # 动态导入magic模块，避免启动时依赖缺失
            import magic
            
            # 使用python-magic库检测文件类型
            mime_type = magic.from_buffer(file_content, mime=True)
            
            allowed_mimes = cls.ALLOWED_EXTENSIONS.get(file_ext, [])
            
            if not allowed_mimes:
                return False, f"不支持的文件扩展名: {file_ext}"
            
            # 鉴于 python-magic 可能会对带 BOM 的 CSV 或者空 CSV 产生奇怪的识别，对已知安全类型的文本稍微放行
            if file_ext in ['.csv', '.json'] and ('text' in mime_type or 'csv' in mime_type or 'json' in mime_type):
                pass
            elif mime_type not in allowed_mimes:
                # 记录一下警告但对已知后缀放行(有时候系统未完整安装libmagic导致结果为 application/octet-stream 等)
                if mime_type == 'application/octet-stream':
                    pass
                else:
                    return False, f"文件类型不匹配。期望: {allowed_mimes}, 实际: {mime_type}"
            
            return True, mime_type
        except ImportError:
            # 如果magic库未安装，回退到扩展名检查
            if file_ext in cls.ALLOWED_EXTENSIONS:
                return True, "extension_fallback"
            return False, f"不支持的文件扩展名: {file_ext}"
        except Exception as e:
            # 其它异常
            if file_ext in cls.ALLOWED_EXTENSIONS:
                return True, "extension_fallback"
            return False, f"文件类型验证失败: {str(e)}"
    
    @classmethod
    def validate_file_size(cls, file_size: int) -> Tuple[bool, str]:
        """验证文件大小"""
        if file_size <= 0:
            return False, "文件为空"
        
        if file_size > cls.MAX_FILE_SIZE:
            return False, f"文件过大。最大允许: {cls.MAX_FILE_SIZE // (1024*1024)}MB"
        
        return True, "size_ok"
    
    @classmethod
    def scan_file_content(cls, file_content: bytes, filename: str = None) -> Tuple[bool, str]:
        """扫描文件内容安全性"""
        # 允许通过配置关闭内容扫描（默认开启）
        if not config_manager.get_param("security.enable_content_scan", True):
            return True, "scan_disabled_by_config"
        try:
            # 获取文件扩展名
            file_ext = ''
            if filename:
                file_ext = os.path.splitext(filename)[1].lower()
            
            # 对于数据文件，跳过内容扫描
            if file_ext in ['.csv', '.xlsx', '.xls', '.json']:
                return True, "data_file_safe"
            
            # 检查是否包含可执行代码的特征
            content_str = file_content.decode('utf-8', errors='ignore').lower()
            
            # 检查危险脚本标签
            dangerous_patterns = [
                '<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=',
                '<?php', '<jsp', 'eval(', 'exec(', 'system('
            ]
            
            for pattern in dangerous_patterns:
                if pattern in content_str:
                    return False, f"文件包含潜在危险内容: {pattern}"
            
            return True, "content_safe"
        except Exception:
            # 如果解码失败，假设文件是二进制格式（如Excel），允许通过
            return True, "binary_content"

# 创建全局实例
security_validator = SecurityValidator()