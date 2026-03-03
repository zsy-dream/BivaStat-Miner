import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from jinja2 import Environment, FileSystemLoader
import logging
from utils.error_handler import DataException, ValidationException

logger = logging.getLogger(__name__)


class EnhancedReportService:
    """增强的报告生成服务，支持多种格式和模板"""
    
    def __init__(self, template_dir: str = None):
        # 自动定位到 static/templates 目录
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.template_dir = template_dir or os.path.join(base_dir, 'static', 'templates')
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        
        # 预定义的报告模板
        self.templates = {
            'financial_risk': self._get_financial_risk_template,
            'market_analysis': self._get_market_analysis_template,
            'general_analysis': self._get_general_analysis_template
        }
    
    def generate_comprehensive_report(self, 
                                    data_info: Dict[str, Any],
                                    analysis_results: Dict[str, Any],
                                    preprocessing_info: Dict[str, Any] = None,
                                    template_type: str = 'general_analysis',
                                    config: Dict[str, Any] = None) -> str:
        """生成综合分析报告"""
        try:
            if config is None:
                config = {}
            
            # 准备报告数据
            report_data = {
                'title': config.get('title', '数据分析报告'),
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'author': config.get('author', '系统自动生成'),
                'version': '1.0',
                'data_info': data_info,
                'analysis_results': analysis_results,
                'preprocessing_info': preprocessing_info,
                'executive_summary': self._generate_executive_summary(data_info, analysis_results),
                'recommendations': self._generate_recommendations(analysis_results, template_type)
            }
            
            # 生成图表
            charts = self._generate_report_charts(analysis_results, config)
            report_data['charts'] = charts
            
            # 生成统计表格
            tables = self._generate_report_tables(analysis_results)
            report_data['tables'] = tables
            
            # 选择模板
            if template_type in self.templates:
                template_content = self.templates[template_type](report_data)
            else:
                template_content = self._get_general_analysis_template(report_data)
            
            # 渲染模板
            try:
                template = self.env.from_string(template_content)
                html_content = template.render(**report_data)
            except Exception as e:
                logger.warning(f"模板渲染失败，使用默认模板: {str(e)}")
                html_content = self._get_fallback_template(report_data)
            
            return html_content
            
        except Exception as e:
            logger.error(f"生成综合报告失败: {str(e)}")
            raise DataException(f"生成综合报告失败: {str(e)}")
    
    def _generate_executive_summary(self, data_info: Dict[str, Any], analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成执行摘要"""
        try:
            summary = {
                'data_overview': {
                    'total_records': data_info.get('shape', [0, 0])[0],
                    'total_features': data_info.get('shape', [0, 0])[1],
                    'numeric_features': len(data_info.get('numeric_columns', [])),
                    'categorical_features': len(data_info.get('categorical_columns', []))
                },
                'key_findings': [],
                'data_quality_score': 0.0,
                'analysis_confidence': '中等'
            }
            
            # 数据质量评分
            if 'quality_report' in data_info:
                quality = data_info['quality_report']
                missing_ratio = quality['missing_values']['total_missing'] / (summary['data_overview']['total_records'] * summary['data_overview']['total_features'])
                duplicate_ratio = quality['duplicates']['duplicate_percentage'] / 100
                
                # 简单的质量评分算法
                quality_score = max(0, 100 - (missing_ratio * 50) - (duplicate_ratio * 30))
                summary['data_quality_score'] = round(quality_score, 2)
            
            # 关键发现
            if 'association_rules' in analysis_results:
                rules = analysis_results['association_rules']
                if rules:
                    high_confidence_rules = [r for r in rules if r.get('confidence', 0) > 0.8]
                    summary['key_findings'].append(f"发现 {len(high_confidence_rules)} 条高置信度关联规则")
            
            if 'statistical_tests' in analysis_results:
                tests = analysis_results['statistical_tests']
                significant_tests = [t for t in tests if t.get('p_value', 1) < 0.05]
                summary['key_findings'].append(f"发现 {len(significant_tests)} 个显著统计关系")
            
            return summary
            
        except Exception as e:
            logger.error(f"生成执行摘要失败: {str(e)}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, analysis_results: Dict[str, Any], template_type: str) -> List[str]:
        """生成建议"""
        try:
            recommendations = []
            
            if template_type == 'financial_risk':
                recommendations.extend([
                    "建议加强对高关联风险指标的监控",
                    "考虑建立动态风险评估模型",
                    "定期更新客户信用评分算法",
                    "加强异常交易模式的实时检测"
                ])
            elif template_type == 'market_analysis':
                recommendations.extend([
                    "基于关联规则优化产品组合策略",
                    "针对不同客户群体制定差异化营销方案",
                    "建立销售预测模型以优化库存管理",
                    "定期分析市场趋势变化"
                ])
            else:
                recommendations.extend([
                    "继续深入分析数据中的潜在模式",
                    "考虑引入更多特征变量提升分析精度",
                    "建立定期数据质量检查机制",
                    "根据分析结果优化业务决策流程"
                ])
            
            return recommendations
            
        except Exception as e:
            logger.error(f"生成建议失败: {str(e)}")
            return ["建议生成失败，请检查分析结果"]
    
    def _generate_report_charts(self, analysis_results: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成报告图表"""
        try:
            charts = []
            
            # 关联规则图表
            if 'association_rules' in analysis_results:
                rules_df = pd.DataFrame(analysis_results['association_rules'])
                if not rules_df.empty:
                    # 置信度分布图
                    fig1 = px.histogram(
                        rules_df, 
                        x='confidence',
                        title='关联规则置信度分布',
                        nbins=20,
                        template='plotly_white'
                    )
                    charts.append({
                        'title': '关联规则置信度分布',
                        'html': fig1.to_html(full_html=False, include_plotlyjs='cdn'),
                        'type': 'histogram'
                    })
                    
                    # 支持度vs置信度散点图
                    if 'support' in rules_df.columns:
                        fig2 = px.scatter(
                            rules_df,
                            x='support',
                            y='confidence',
                            size='lift' if 'lift' in rules_df.columns else None,
                            title='支持度 vs 置信度关系',
                            template='plotly_white'
                        )
                        charts.append({
                            'title': '支持度 vs 置信度关系',
                            'html': fig2.to_html(full_html=False, include_plotlyjs='cdn'),
                            'type': 'scatter'
                        })
            
            # 统计检验结果图表
            if 'statistical_tests' in analysis_results:
                tests_df = pd.DataFrame(analysis_results['statistical_tests'])
                if not tests_df.empty and 'p_value' in tests_df.columns:
                    # P值分布图
                    fig3 = px.histogram(
                        tests_df,
                        x='p_value',
                        title='统计检验P值分布',
                        nbins=20,
                        template='plotly_white'
                    )
                    charts.append({
                        'title': '统计检验P值分布',
                        'html': fig3.to_html(full_html=False, include_plotlyjs='cdn'),
                        'type': 'histogram'
                    })
            
            return charts
            
        except Exception as e:
            logger.error(f"生成报告图表失败: {str(e)}")
            return []
    
    def _generate_report_tables(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成报告表格"""
        try:
            tables = []
            
            # 关联规则表格
            if 'association_rules' in analysis_results:
                rules_df = pd.DataFrame(analysis_results['association_rules'])
                if not rules_df.empty:
                    # 选择重要列并格式化
                    important_columns = ['antecedents', 'consequents', 'support', 'confidence', 'lift']
                    available_columns = [col for col in important_columns if col in rules_df.columns]
                    
                    if available_columns:
                        table_df = rules_df[available_columns].copy()
                        
                        # 格式化数值列
                        for col in ['support', 'confidence', 'lift']:
                            if col in table_df.columns:
                                table_df[col] = table_df[col].round(4)
                        
                        # 按置信度排序
                        if 'confidence' in table_df.columns:
                            table_df = table_df.sort_values('confidence', ascending=False).head(20)
                        
                        tables.append({
                            'title': 'Top 20 关联规则',
                            'html': table_df.to_html(classes='table table-striped table-hover', index=False),
                            'type': 'association_rules'
                        })
            
            # 统计检验表格
            if 'statistical_tests' in analysis_results:
                tests_df = pd.DataFrame(analysis_results['statistical_tests'])
                if not tests_df.empty:
                    # 选择重要列
                    important_columns = ['test_name', 'statistic', 'p_value', 'conclusion']
                    available_columns = [col for col in important_columns if col in tests_df.columns]
                    
                    if available_columns:
                        table_df = tests_df[available_columns].copy()
                        
                        # 格式化数值列
                        if 'p_value' in table_df.columns:
                            table_df['p_value'] = table_df['p_value'].round(6)
                        if 'statistic' in table_df.columns:
                            table_df['statistic'] = table_df['statistic'].round(4)
                        
                        tables.append({
                            'title': '统计检验结果',
                            'html': table_df.to_html(classes='table table-striped table-hover', index=False),
                            'type': 'statistical_tests'
                        })
            
            return tables
            
        except Exception as e:
            logger.error(f"生成报告表格失败: {str(e)}")
            return []
    
    def _get_financial_risk_template(self, data: Dict[str, Any]) -> str:
        """金融风控报告模板"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .header { text-align: center; border-bottom: 2px solid #007bff; padding-bottom: 20px; }
        .section { margin: 30px 0; }
        .executive-summary { background-color: #f8f9fa; padding: 20px; border-radius: 5px; }
        .chart { margin: 20px 0; text-align: center; }
        .table { margin: 20px 0; }
        .recommendations { background-color: #d4edda; padding: 20px; border-radius: 5px; }
        .footer { text-align: center; margin-top: 50px; font-size: 12px; color: #666; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p>金融风控分析报告</p>
        <p>生成时间: {{ generated_at }}</p>
        <p>报告作者: {{ author }}</p>
    </div>
    
    <div class="section executive-summary">
        <h2>执行摘要</h2>
        <h3>数据概览</h3>
        <ul>
            <li>总记录数: {{ executive_summary.data_overview.total_records | default(0) }}</li>
            <li>总特征数: {{ executive_summary.data_overview.total_features | default(0) }}</li>
            <li>数据质量评分: {{ executive_summary.data_quality_score | default(0) }}/100</li>
        </ul>
        
        <h3>关键发现</h3>
        <ul>
        {% for finding in executive_summary.key_findings %}
            <li>{{ finding }}</li>
        {% endfor %}
        </ul>
    </div>
    
    <div class="section">
        <h2>分析结果</h2>
        {% for chart in charts %}
        <div class="chart">
            <h3>{{ chart.title }}</h3>
            {{ chart.html|safe }}
        </div>
        {% endfor %}
        
        {% for table in tables %}
        <div class="table">
            <h3>{{ table.title }}</h3>
            {{ table.html|safe }}
        </div>
        {% endfor %}
    </div>
    
    <div class="section recommendations">
        <h2>风控建议</h2>
        <ul>
        {% for recommendation in recommendations %}
            <li>{{ recommendation }}</li>
        {% endfor %}
        </ul>
    </div>
    
    <div class="footer">
        <p>本报告由基于启发式算法的双变量关联挖掘与非参数统计分析平台自动生成</p>
        <p>报告版本: {{ version }}</p>
    </div>
</body>
</html>
        """
    
    def _get_market_analysis_template(self, data: Dict[str, Any]) -> str:
        """市场分析报告模板"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .header { text-align: center; border-bottom: 2px solid #28a745; padding-bottom: 20px; }
        .section { margin: 30px 0; }
        .executive-summary { background-color: #f8f9fa; padding: 20px; border-radius: 5px; }
        .chart { margin: 20px 0; text-align: center; }
        .table { margin: 20px 0; }
        .recommendations { background-color: #d1ecf1; padding: 20px; border-radius: 5px; }
        .footer { text-align: center; margin-top: 50px; font-size: 12px; color: #666; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p>市场趋势分析报告</p>
        <p>生成时间: {{ generated_at }}</p>
        <p>报告作者: {{ author }}</p>
    </div>
    
    <div class="section executive-summary">
        <h2>执行摘要</h2>
        <h3>数据概览</h3>
        <ul>
            <li>总记录数: {{ executive_summary.data_overview.total_records | default(0) }}</li>
            <li>总特征数: {{ executive_summary.data_overview.total_features | default(0) }}</li>
            <li>数据质量评分: {{ executive_summary.data_quality_score | default(0) }}/100</li>
        </ul>
        
        <h3>关键发现</h3>
        <ul>
        {% for finding in executive_summary.key_findings %}
            <li>{{ finding }}</li>
        {% endfor %}
        </ul>
    </div>
    
    <div class="section">
        <h2>分析结果</h2>
        {% for chart in charts %}
        <div class="chart">
            <h3>{{ chart.title }}</h3>
            {{ chart.html|safe }}
        </div>
        {% endfor %}
        
        {% for table in tables %}
        <div class="table">
            <h3>{{ table.title }}</h3>
            {{ table.html|safe }}
        </div>
        {% endfor %}
    </div>
    
    <div class="section recommendations">
        <h2>市场策略建议</h2>
        <ul>
        {% for recommendation in recommendations %}
            <li>{{ recommendation }}</li>
        {% endfor %}
        </ul>
    </div>
    
    <div class="footer">
        <p>本报告由基于启发式算法的双变量关联挖掘与非参数统计分析平台自动生成</p>
        <p>报告版本: {{ version }}</p>
    </div>
</body>
</html>
        """
    
    def _get_general_analysis_template(self, data: Dict[str, Any]) -> str:
        """通用分析报告模板"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .header { text-align: center; border-bottom: 2px solid #6c757d; padding-bottom: 20px; }
        .section { margin: 30px 0; }
        .executive-summary { background-color: #f8f9fa; padding: 20px; border-radius: 5px; }
        .chart { margin: 20px 0; text-align: center; }
        .table { margin: 20px 0; }
        .recommendations { background-color: #fff3cd; padding: 20px; border-radius: 5px; }
        .footer { text-align: center; margin-top: 50px; font-size: 12px; color: #666; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p>数据分析报告</p>
        <p>生成时间: {{ generated_at }}</p>
        <p>报告作者: {{ author }}</p>
    </div>
    
    <div class="section executive-summary">
        <h2>执行摘要</h2>
        <h3>数据概览</h3>
        <ul>
            <li>总记录数: {{ executive_summary.data_overview.total_records | default(0) }}</li>
            <li>总特征数: {{ executive_summary.data_overview.total_features | default(0) }}</li>
            <li>数值特征数: {{ executive_summary.data_overview.numeric_features | default(0) }}</li>
            <li>分类特征数: {{ executive_summary.data_overview.categorical_features | default(0) }}</li>
            <li>数据质量评分: {{ executive_summary.data_quality_score | default(0) }}/100</li>
        </ul>
        
        <h3>关键发现</h3>
        <ul>
        {% for finding in executive_summary.key_findings %}
            <li>{{ finding }}</li>
        {% endfor %}
        </ul>
    </div>
    
    <div class="section">
        <h2>分析结果</h2>
        {% for chart in charts %}
        <div class="chart">
            <h3>{{ chart.title }}</h3>
            {{ chart.html|safe }}
        </div>
        {% endfor %}
        
        {% for table in tables %}
        <div class="table">
            <h3>{{ table.title }}</h3>
            {{ table.html|safe }}
        </div>
        {% endfor %}
    </div>
    
    <div class="section recommendations">
        <h2>分析建议</h2>
        <ul>
        {% for recommendation in recommendations %}
            <li>{{ recommendation }}</li>
        {% endfor %}
        </ul>
    </div>
    
    <div class="footer">
        <p>本报告由基于启发式算法的双变量关联挖掘与非参数统计分析平台自动生成</p>
        <p>报告版本: {{ version }}</p>
    </div>
</body>
</html>
        """
    
    def _get_fallback_template(self, data: Dict[str, Any]) -> str:
        """备用模板"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{data.get('title', '数据分析报告')}</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>{data.get('title', '数据分析报告')}</h1>
    <p>生成时间: {data.get('generated_at', 'Unknown')}</p>
    <p>报告生成过程中遇到问题，请检查模板配置。</p>
</body>
</html>
        """
    
    def save_report(self, html_content: str, filename: str = None, format_type: str = 'html') -> str:
        """保存报告"""
        try:
            if filename is None:
                filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
            
            # 确保保存到 reports 文件夹
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            reports_dir = os.path.join(base_dir, 'static', 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            filepath = os.path.join(reports_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"报告已保存至: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存报告失败: {str(e)}")
            raise DataException(f"保存报告失败: {str(e)}")
    
    def export_to_pdf(self, html_content: str, filename: str = None) -> str:
        """导出为PDF（需要额外的依赖库）"""
        try:
            # 这里可以集成 pdfkit 或其他PDF生成库
            # 目前先保存为HTML格式
            return self.save_report(html_content, filename, 'html')
        except Exception as e:
            logger.error(f"导出PDF失败: {str(e)}")
            raise DataException(f"导出PDF失败: {str(e)}")


# 保持向后兼容的原始类
class ReportService(EnhancedReportService):
    """向后兼容的报告服务类"""
    pass


# =======================================================
# 👇【关键修复】必须实例化并导出，否则路由层找不到！
# =======================================================
enhanced_report_service = EnhancedReportService()
report_service_instance = ReportService()

# 修复：创建正确的函数接口
def generate_template(data):
    """生成报告模板的函数接口"""
    return enhanced_report_service._get_fallback_template(data)

def save_report(html_content, filename=None, format_type='html'):
    """保存报告的函数接口"""
    return enhanced_report_service.save_report(html_content, filename, format_type)