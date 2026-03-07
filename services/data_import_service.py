import os
import pandas as pd
import numpy as np
import sqlite3
import logging
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import urlparse
import json
import requests
from io import StringIO, BytesIO
import xml.etree.ElementTree as ET
from utils.error_handler import DataException, ValidationException

logger = logging.getLogger(__name__)

class DataImportService:
    """增强的数据导入服务，支持多种数据源和格式"""
    
    def __init__(self):
        self.supported_formats = {
            'csv', 'xlsx', 'xls', 'json', 'xml', 'parquet', 'hdf5', 'sql', 'api'
        }
        self.max_file_size_mb = 100
        
    def import_from_file(self, file_path: str, **kwargs) -> pd.DataFrame:
        """从文件导入数据"""
        try:
            file_ext = self._get_file_extension(file_path)
            
            if file_ext not in self.supported_formats:
                raise ValidationException(f"不支持的文件格式: {file_ext}")
            
            if file_ext == 'csv':
                return self._import_csv(file_path, **kwargs)
            elif file_ext in ['xlsx', 'xls']:
                return self._import_excel(file_path, **kwargs)
            elif file_ext == 'json':
                return self._import_json(file_path, **kwargs)
            elif file_ext == 'xml':
                return self._import_xml(file_path, **kwargs)
            elif file_ext == 'parquet':
                return self._import_parquet(file_path, **kwargs)
            elif file_ext == 'hdf5':
                return self._import_hdf5(file_path, **kwargs)
            else:
                raise ValidationException(f"暂不支持的格式: {file_ext}")
                
        except Exception as e:
            if isinstance(e, (DataException, ValidationException)):
                raise
            logger.error(f"文件导入失败: {file_path}, 错误: {str(e)}")
            raise DataException(f"文件导入失败: {str(e)}")
    
    def import_from_database(self, connection_config: Dict[str, Any], query: str) -> pd.DataFrame:
        """从数据库导入数据"""
        try:
            db_type = connection_config.get('type', '').lower()
            
            if db_type == 'sqlite':
                return self._import_sqlite(connection_config, query)
            elif db_type == 'mysql':
                return self._import_mysql(connection_config, query)
            elif db_type == 'postgresql':
                return self._import_postgresql(connection_config, query)
            elif db_type == 'mssql':
                return self._import_mssql(connection_config, query)
            else:
                raise ValidationException(f"不支持的数据库类型: {db_type}")
                
        except Exception as e:
            if isinstance(e, (DataException, ValidationException)):
                raise
            logger.error(f"数据库导入失败: {str(e)}")
            raise DataException(f"数据库导入失败: {str(e)}")
    
    def import_from_api(self, api_config: Dict[str, Any]) -> pd.DataFrame:
        """从API导入数据"""
        try:
            url = api_config.get('url')
            method = api_config.get('method', 'GET').upper()
            headers = api_config.get('headers', {})
            params = api_config.get('params', {})
            data_type = api_config.get('data_type', 'json')
            
            if not url:
                raise ValidationException("API URL不能为空")
            
            # 发送请求
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=params, timeout=30)
            else:
                raise ValidationException(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            
            # 解析响应数据
            if data_type == 'json':
                return self._parse_json_response(response.json(), api_config)
            elif data_type == 'csv':
                return pd.read_csv(StringIO(response.text))
            elif data_type == 'xml':
                return self._parse_xml_response(response.text, api_config)
            else:
                raise ValidationException(f"不支持的数据类型: {data_type}")
                
        except Exception as e:
            if isinstance(e, (DataException, ValidationException)):
                raise
            logger.error(f"API导入失败: {str(e)}")
            raise DataException(f"API导入失败: {str(e)}")
    
    def preview_data(self, source_config: Dict[str, Any], rows: int = 10) -> Dict[str, Any]:
        """预览数据"""
        try:
            source_type = source_config.get('type')
            
            if source_type == 'file':
                df = self.import_from_file(source_config.get('path'), nrows=rows)
            elif source_type == 'database':
                # 修改查询以限制行数
                query = f"SELECT * FROM ({source_config.get('query')}) LIMIT {rows}"
                df = self.import_from_database(source_config.get('connection'), query)
            elif source_type == 'api':
                df = self.import_from_api(source_config)
                df = df.head(rows)
            else:
                raise ValidationException(f"不支持的数据源类型: {source_type}")
            
            return {
                'success': True,
                'preview': df.fillna('').to_dict(orient='records'),
                'columns': list(df.columns),
                'dtypes': df.dtypes.astype(str).to_dict(),
                'shape': df.shape,
                'sample_size': len(df)
            }
            
        except Exception as e:
            logger.error(f"数据预览失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_data_source(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """验证数据源"""
        try:
            source_type = source_config.get('type')
            
            if source_type == 'file':
                return self._validate_file_source(source_config)
            elif source_type == 'database':
                return self._validate_database_source(source_config)
            elif source_type == 'api':
                return self._validate_api_source(source_config)
            else:
                return {'valid': False, 'error': f'不支持的数据源类型: {source_type}'}
                
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def _import_csv(self, file_path: str, **kwargs) -> pd.DataFrame:
        """导入CSV文件"""
        encodings = ['utf-8', 'gbk', 'gb18030', 'cp1252', 'latin1']
        sep = kwargs.get('sep', None)
        engine = 'python' if sep is None else 'c'
        
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    sep=sep,
                    header=kwargs.get('header', 0),
                    nrows=kwargs.get('nrows', None),
                    engine=engine,
                    on_bad_lines='skip'
                )
                logger.info(f"成功使用 {encoding} 编码读取CSV: {file_path}")
                return df
            except UnicodeDecodeError:
                continue
        
        raise DataException("所有编码尝试失败，请检查文件编码")
    
    def _import_excel(self, file_path: str, **kwargs) -> pd.DataFrame:
        """导入Excel文件"""
        try:
            df = pd.read_excel(
                file_path,
                sheet_name=kwargs.get('sheet_name', 0),
                header=kwargs.get('header', 0),
                nrows=kwargs.get('nrows', None),
                engine='openpyxl' if file_path.endswith('.xlsx') else 'xlrd'
            )
            return df
        except ImportError:
            raise DataException("缺少Excel处理库，请安装: pip install openpyxl xlrd")
    
    def _import_json(self, file_path: str, **kwargs) -> pd.DataFrame:
        """导入JSON文件"""
        try:
            orient = kwargs.get('orient', 'records')
            lines = kwargs.get('lines', False)
            
            if lines or file_path.endswith('.jsonl'):
                df = pd.read_json(file_path, lines=True, orient=orient)
            else:
                df = pd.read_json(file_path, orient=orient)
            
            return df
        except Exception as e:
            raise DataException(f"JSON解析失败: {str(e)}")
    
    def _import_xml(self, file_path: str, **kwargs) -> pd.DataFrame:
        """导入XML文件"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 简单的XML解析，可以根据需要扩展
            data = []
            for child in root:
                record = {}
                for elem in child:
                    record[elem.tag] = elem.text
                data.append(record)
            
            return pd.DataFrame(data)
        except Exception as e:
            raise DataException(f"XML解析失败: {str(e)}")
    
    def _import_parquet(self, file_path: str, **kwargs) -> pd.DataFrame:
        """导入Parquet文件"""
        try:
            df = pd.read_parquet(file_path)
            return df
        except ImportError:
            raise DataException("缺少Parquet处理库，请安装: pip install pyarrow")
    
    def _import_hdf5(self, file_path: str, **kwargs) -> pd.DataFrame:
        """导入HDF5文件"""
        try:
            key = kwargs.get('key', None)
            df = pd.read_hdf(file_path, key=key)
            return df
        except ImportError:
            raise DataException("缺少HDF5处理库，请安装: pip install tables")
    
    def _import_sqlite(self, config: Dict[str, Any], query: str) -> pd.DataFrame:
        """导入SQLite数据"""
        try:
            db_path = config.get('database')
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            raise DataException(f"SQLite连接失败: {str(e)}")
    
    def _import_mysql(self, config: Dict[str, Any], query: str) -> pd.DataFrame:
        """导入MySQL数据"""
        try:
            import pymysql
            conn = pymysql.connect(
                host=config.get('host'),
                port=config.get('port', 3306),
                user=config.get('user'),
                password=config.get('password'),
                database=config.get('database'),
                charset='utf8mb4'
            )
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except ImportError:
            raise DataException("缺少MySQL库，请安装: pip install pymysql")
        except Exception as e:
            raise DataException(f"MySQL连接失败: {str(e)}")
    
    def _import_postgresql(self, config: Dict[str, Any], query: str) -> pd.DataFrame:
        """导入PostgreSQL数据"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=config.get('host'),
                port=config.get('port', 5432),
                user=config.get('user'),
                password=config.get('password'),
                database=config.get('database')
            )
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except ImportError:
            raise DataException("缺少PostgreSQL库，请安装: pip install psycopg2-binary")
        except Exception as e:
            raise DataException(f"PostgreSQL连接失败: {str(e)}")
    
    def _import_mssql(self, config: Dict[str, Any], query: str) -> pd.DataFrame:
        """导入SQL Server数据"""
        try:
            import pyodbc
            conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={config.get('host')};DATABASE={config.get('database')};UID={config.get('user')};PWD={config.get('password')}"
            conn = pyodbc.connect(conn_str)
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except ImportError:
            raise DataException("缺少SQL Server库，请安装: pip install pyodbc")
        except Exception as e:
            raise DataException(f"SQL Server连接失败: {str(e)}")
    
    def _parse_json_response(self, json_data: Any, config: Dict[str, Any]) -> pd.DataFrame:
        """解析JSON响应"""
        try:
            data_path = config.get('data_path', None)
            
            if data_path:
                # 支持嵌套JSON路径，如 'data.records'
                keys = data_path.split('.')
                current = json_data
                for key in keys:
                    current = current[key]
                json_data = current
            
            if isinstance(json_data, list):
                return pd.DataFrame(json_data)
            elif isinstance(json_data, dict):
                return pd.DataFrame([json_data])
            else:
                raise DataException("无法将JSON数据转换为DataFrame")
                
        except Exception as e:
            raise DataException(f"JSON解析失败: {str(e)}")
    
    def _parse_xml_response(self, xml_text: str, config: Dict[str, Any]) -> pd.DataFrame:
        """解析XML响应"""
        try:
            root = ET.fromstring(xml_text)
            data = []
            
            record_path = config.get('record_path', './/record')
            for record in root.findall(record_path):
                record_data = {}
                for elem in record:
                    record_data[elem.tag] = elem.text
                data.append(record_data)
            
            return pd.DataFrame(data)
        except Exception as e:
            raise DataException(f"XML解析失败: {str(e)}")
    
    def _get_file_extension(self, file_path: str) -> str:
        """获取文件扩展名"""
        return os.path.splitext(file_path)[1].lower().lstrip('.')
    
    def _validate_file_source(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证文件数据源"""
        try:
            file_path = config.get('path')
            if not file_path or not os.path.exists(file_path):
                return {'valid': False, 'error': '文件不存在'}
            
            file_ext = self._get_file_extension(file_path)
            if file_ext not in self.supported_formats:
                return {'valid': False, 'error': f'不支持的文件格式: {file_ext}'}
            
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            if file_size > self.max_file_size_mb:
                return {'valid': False, 'error': f'文件过大，最大支持 {self.max_file_size_mb}MB'}
            
            return {'valid': True, 'file_size_mb': file_size, 'format': file_ext}
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def _validate_database_source(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证数据库数据源"""
        try:
            connection = config.get('connection')
            if not connection:
                return {'valid': False, 'error': '数据库连接配置不能为空'}
            
            db_type = connection.get('type', '').lower()
            if db_type not in ['sqlite', 'mysql', 'postgresql', 'mssql']:
                return {'valid': False, 'error': f'不支持的数据库类型: {db_type}'}
            
            # 简单的连接测试
            if db_type == 'sqlite':
                db_path = connection.get('database')
                if not db_path or not os.path.exists(db_path):
                    return {'valid': False, 'error': 'SQLite数据库文件不存在'}
            
            return {'valid': True, 'database_type': db_type}
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def _validate_api_source(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证API数据源"""
        try:
            url = config.get('url')
            if not url:
                return {'valid': False, 'error': 'API URL不能为空'}
            
            # 简单的URL格式验证
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return {'valid': False, 'error': '无效的URL格式'}
            
            return {'valid': True, 'url': url}
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}

# 创建全局实例
data_import_service = DataImportService()
