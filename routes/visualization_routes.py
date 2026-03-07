from flask import Blueprint, request, jsonify, send_file
import pandas as pd
import numpy as np
import logging
import base64
import io

from services.visualization_service import visualization_service
from utils.global_state import global_state
from utils.error_handler import (
    handle_app_exception, create_success_response, create_error_response,
    ValidationException, DataException
)

# 设置日志
logger = logging.getLogger(__name__)

visualization_bp = Blueprint('visualization_routes', __name__)


@visualization_bp.route('/create_chart', methods=['POST'])
@handle_app_exception
def create_chart():
    """创建图表"""
    try:
        req_data = request.json
        chart_type = req_data.get('chart_type')
        config = req_data.get('config', {})
        use_current_data = req_data.get('use_current_data', False)
        
        # 获取数据
        if use_current_data:
            current_data, current_path = global_state.get_current_data()
            if current_data is None:
                raise ValidationException("未找到当前数据，请先上传或导入数据")
            df = current_data
        else:
            file_path = req_data.get('file_path')
            if not file_path:
                raise ValidationException("未指定数据文件路径")
            from models.data_model import get_data
            df = get_data(file_path)
        
        # 根据图表类型创建图表
        if chart_type == 'correlation_heatmap':
            result = visualization_service.create_correlation_heatmap(df, config)
        elif chart_type == 'scatter':
            x_col = req_data.get('x_col')
            y_col = req_data.get('y_col')
            if not x_col or not y_col:
                raise ValidationException("散点图需要指定x_col和y_col")
            result = visualization_service.create_scatter_plot(df, x_col, y_col, config)
        elif chart_type == 'distribution':
            column = req_data.get('column')
            if not column:
                raise ValidationException("分布图需要指定column")
            result = visualization_service.create_distribution_plot(df, column, config)
        elif chart_type == 'box':
            value_col = req_data.get('value_col')
            group_col = req_data.get('group_col')
            if not value_col:
                raise ValidationException("箱线图需要指定value_col")
            result = visualization_service.create_box_plot(df, value_col, group_col, config)
        elif chart_type == 'bar':
            x_col = req_data.get('x_col')
            y_col = req_data.get('y_col')
            if not x_col:
                raise ValidationException("柱状图需要指定x_col")
            result = visualization_service.create_bar_chart(df, x_col, y_col, config)
        elif chart_type == 'line':
            x_col = req_data.get('x_col')
            y_col = req_data.get('y_col')
            if not x_col or not y_col:
                raise ValidationException("折线图需要指定x_col和y_col")
            result = visualization_service.create_line_plot(df, x_col, y_col, config)
        elif chart_type == 'network':
            rules_data = req_data.get('rules_data')
            if not rules_data:
                raise ValidationException("网络图需要提供rules_data")
            rules_df = pd.DataFrame(rules_data)
            result = visualization_service.create_association_rules_network(rules_df, config)
        elif chart_type == 'dashboard':
            result = visualization_service.create_dashboard(df, config)
        else:
            raise ValidationException(f"不支持的图表类型: {chart_type}")
        
        # 启用自适应布局，让图表跟随容器尺寸
        result['figure'].update_layout(autosize=True)
        figure_html = result['figure'].to_html(
            full_html=False,
            include_plotlyjs=True,
            config={'responsive': True}
        )
        
        return create_success_response({
            'chart_html': figure_html,
            'chart_type': result.get('chart_type', chart_type),
            'metadata': {k: v for k, v in result.items() if k != 'figure'}
        })
        
    except Exception as e:
        raise DataException(f"创建图表失败: {str(e)}")


@visualization_bp.route('/get_chart_config', methods=['POST'])
@handle_app_exception
def get_chart_config():
    """获取图表配置选项"""
    try:
        req_data = request.json
        chart_type = req_data.get('chart_type')
        use_current_data = req_data.get('use_current_data', False)
        
        # 获取数据
        if use_current_data:
            current_data, current_path = global_state.get_current_data()
            if current_data is None:
                raise ValidationException("未找到当前数据，请先上传或导入数据")
            df = current_data
        else:
            file_path = req_data.get('file_path')
            if not file_path:
                raise ValidationException("未指定数据文件路径")
            from models.data_model import get_data
            df = get_data(file_path)
        
        config_options = {
            'available_columns': list(df.columns),
            'numeric_columns': df.select_dtypes(include=[np.number]).columns.tolist(),
            'categorical_columns': df.select_dtypes(include=['object', 'category']).columns.tolist(),
            'datetime_columns': df.select_dtypes(include=['datetime64']).columns.tolist()
        }
        
        # 根据图表类型提供特定配置
        if chart_type == 'scatter':
            config_options['required_params'] = ['x_col', 'y_col']
            config_options['optional_params'] = {
                'add_trendline': {'type': 'boolean', 'default': False},
                'show_regression_info': {'type': 'boolean', 'default': False},
                'width': {'type': 'integer', 'default': 800},
                'height': {'type': 'integer', 'default': 600}
            }
        elif chart_type == 'correlation_heatmap':
            config_options['required_params'] = []
            config_options['optional_params'] = {
                'method': {'type': 'select', 'options': ['pearson', 'spearman', 'kendall'], 'default': 'pearson'},
                'colorscale': {'type': 'select', 'options': ['RdBu_r', 'viridis', 'plasma'], 'default': 'RdBu_r'},
                'width': {'type': 'integer', 'default': 800},
                'height': {'type': 'integer', 'default': 600}
            }
        elif chart_type == 'distribution':
            config_options['required_params'] = ['column']
            config_options['optional_params'] = {
                'bins': {'type': 'integer', 'default': 30},
                'color': {'type': 'string', 'default': 'lightblue'},
                'width': {'type': 'integer', 'default': 800},
                'height': {'type': 'integer', 'default': 600}
            }
        elif chart_type == 'box':
            config_options['required_params'] = ['value_col']
            config_options['optional_params'] = {
                'group_col': {'type': 'string', 'default': None},
                'show_points': {'type': 'boolean', 'default': True},
                'width': {'type': 'integer', 'default': 800},
                'height': {'type': 'integer', 'default': 600}
            }
        elif chart_type == 'bar':
            config_options['required_params'] = ['x_col']
            config_options['optional_params'] = {
                'y_col': {'type': 'string', 'default': None},
                'top_n': {'type': 'integer', 'default': 20},
                'show_values': {'type': 'boolean', 'default': True},
                'xaxis_angle': {'type': 'integer', 'default': -45},
                'width': {'type': 'integer', 'default': 800},
                'height': {'type': 'integer', 'default': 600}
            }
        elif chart_type == 'line':
            config_options['required_params'] = ['x_col', 'y_col']
            config_options['optional_params'] = {
                'show_markers': {'type': 'boolean', 'default': True},
                'add_trendline': {'type': 'boolean', 'default': False},
                'trendline_window': {'type': 'integer', 'default': 5},
                'width': {'type': 'integer', 'default': 800},
                'height': {'type': 'integer', 'default': 600}
            }
        elif chart_type == 'dashboard':
            config_options['required_params'] = []
            config_options['optional_params'] = {
                'width': {'type': 'integer', 'default': 1000},
                'height': {'type': 'integer', 'default': 800}
            }
        
        return create_success_response(config_options)
        
    except Exception as e:
        raise DataException(f"获取图表配置失败: {str(e)}")


@visualization_bp.route('/export_chart', methods=['POST'])
@handle_app_exception
def export_chart():
    """导出图表"""
    try:
        req_data = request.json
        chart_type = req_data.get('chart_type')
        config = req_data.get('config', {})
        export_format = req_data.get('format', 'html')
        filename = req_data.get('filename')
        use_current_data = req_data.get('use_current_data', False)
        
        # 获取数据
        if use_current_data:
            current_data, current_path = global_state.get_current_data()
            if current_data is None:
                raise ValidationException("未找到当前数据，请先上传或导入数据")
            df = current_data
        else:
            file_path = req_data.get('file_path')
            if not file_path:
                raise ValidationException("未指定数据文件路径")
            from models.data_model import get_data
            df = get_data(file_path)
        
        # 创建图表
        if chart_type == 'correlation_heatmap':
            result = visualization_service.create_correlation_heatmap(df, config)
        elif chart_type == 'scatter':
            x_col = req_data.get('x_col')
            y_col = req_data.get('y_col')
            result = visualization_service.create_scatter_plot(df, x_col, y_col, config)
        elif chart_type == 'distribution':
            column = req_data.get('column')
            result = visualization_service.create_distribution_plot(df, column, config)
        elif chart_type == 'box':
            value_col = req_data.get('value_col')
            group_col = req_data.get('group_col')
            result = visualization_service.create_box_plot(df, value_col, group_col, config)
        elif chart_type == 'bar':
            x_col = req_data.get('x_col')
            y_col = req_data.get('y_col')
            result = visualization_service.create_bar_chart(df, x_col, y_col, config)
        elif chart_type == 'line':
            x_col = req_data.get('x_col')
            y_col = req_data.get('y_col')
            result = visualization_service.create_line_plot(df, x_col, y_col, config)
        elif chart_type == 'dashboard':
            result = visualization_service.create_dashboard(df, config)
        else:
            raise ValidationException(f"不支持的图表类型: {chart_type}")
        
        # 导出图表
        if not filename:
            filename = f"chart_{chart_type}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.{export_format}"
        
        export_path = visualization_service.export_chart(result['figure'], filename, export_format)
        return send_file(export_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        raise DataException(f"导出图表失败: {str(e)}")


@visualization_bp.route('/chart_types', methods=['GET'])
@handle_app_exception
def get_chart_types():
    """获取支持的图表类型"""
    try:
        chart_types = {
            'correlation_heatmap': {
                'name': '相关性热力图',
                'description': '展示变量间的相关性矩阵',
                'required_data_type': 'numeric',
                'min_columns': 2
            },
            'scatter': {
                'name': '散点图',
                'description': '展示两个数值变量间的关系',
                'required_data_type': 'numeric',
                'min_columns': 2
            },
            'distribution': {
                'name': '分布图',
                'description': '展示单个变量的分布情况',
                'required_data_type': 'numeric',
                'min_columns': 1
            },
            'box': {
                'name': '箱线图',
                'description': '展示变量的分布特征和异常值',
                'required_data_type': 'numeric',
                'min_columns': 1
            },
            'bar': {
                'name': '柱状图',
                'description': '展示分类变量的频数或数值比较',
                'required_data_type': 'any',
                'min_columns': 1
            },
            'line': {
                'name': '折线图',
                'description': '展示变量随时间或其他有序变量的变化趋势',
                'required_data_type': 'any',
                'min_columns': 2
            },
            'network': {
                'name': '关联规则网络图',
                'description': '展示关联规则的网络关系',
                'required_data_type': 'rules',
                'min_columns': 0
            },
            'dashboard': {
                'name': '综合仪表板',
                'description': '展示数据的综合分析视图',
                'required_data_type': 'any',
                'min_columns': 1
            }
        }
        
        return create_success_response(chart_types)
        
    except Exception as e:
        raise DataException(f"获取图表类型失败: {str(e)}")


@visualization_bp.route('/data_summary', methods=['POST'])
@handle_app_exception
def get_data_summary():
    """获取数据摘要信息，用于图表配置"""
    try:
        req_data = request.json
        use_current_data = req_data.get('use_current_data', False)
        
        # 获取数据
        if use_current_data:
            current_data, current_path = global_state.get_current_data()
            if current_data is None:
                raise ValidationException("未找到当前数据，请先上传或导入数据")
            df = current_data
        else:
            file_path = req_data.get('file_path')
            if not file_path:
                raise ValidationException("未指定数据文件路径")
            from models.data_model import get_data
            df = get_data(file_path)
        
        # 生成数据摘要
        summary = {
            'shape': df.shape,
            'columns': {
                'all': list(df.columns),
                'numeric': df.select_dtypes(include=[np.number]).columns.tolist(),
                'categorical': df.select_dtypes(include=['object', 'category']).columns.tolist(),
                'datetime': df.select_dtypes(include=['datetime64']).columns.tolist()
            },
            'data_types': df.dtypes.astype(str).to_dict(),
            'missing_values': df.isnull().sum().to_dict(),
            'sample_data': df.head(5).fillna('').to_dict(orient='records')
        }
        
        # 为数值列添加统计信息
        numeric_summary = {}
        for col in summary['columns']['numeric']:
            numeric_summary[col] = {
                'min': float(df[col].min()),
                'max': float(df[col].max()),
                'mean': float(df[col].mean()),
                'median': float(df[col].median()),
                'std': float(df[col].std())
            }
        summary['numeric_summary'] = numeric_summary
        
        # 为分类列添加唯一值信息
        categorical_summary = {}
        for col in summary['columns']['categorical']:
            categorical_summary[col] = {
                'unique_count': int(df[col].nunique()),
                'top_values': df[col].value_counts().head(10).to_dict()
            }
        summary['categorical_summary'] = categorical_summary
        
        return create_success_response(summary)
        
    except Exception as e:
        raise DataException(f"获取数据摘要失败: {str(e)}")
