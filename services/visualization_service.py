import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Optional, Tuple
import logging
from pandas.api.types import is_numeric_dtype
from utils.error_handler import DataException, ValidationException

logger = logging.getLogger(__name__)

class VisualizationService:
    """增强的可视化服务，提供专业的数据分析图表"""
    
    def __init__(self):
        self.color_palette = px.colors.qualitative.Set3
        self.default_theme = 'plotly_white'
        self.font_family = "Microsoft YaHei, SimHei, Arial, sans-serif"

    def _apply_standard_layout(
        self,
        fig,
        title: str,
        config: Dict[str, Any],
        *,
        xaxis_title: Optional[str] = None,
        yaxis_title: Optional[str] = None,
        showlegend: bool = True
    ) -> None:
        """统一图表布局样式。"""
        fig.update_layout(
            title=dict(
                text=title,
                x=0.02,
                xanchor='left',
                font=dict(size=18, family=self.font_family, color='#1f2937')
            ),
            width=config.get('width', 900),
            height=config.get('height', 620),
            template=self.default_theme,
            showlegend=showlegend,
            font=dict(family=self.font_family, size=12, color='#374151'),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=70, r=40, t=70, b=70),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="rgba(203,213,225,0.8)",
                borderwidth=1,
                font=dict(size=11, family=self.font_family)
            )
        )

        fig.update_xaxes(
            title_text=xaxis_title,
            showgrid=True,
            gridcolor='rgba(226,232,240,0.7)',
            zeroline=False,
            linecolor='rgba(148,163,184,0.8)',
            tickfont=dict(family=self.font_family, size=11)
        )
        fig.update_yaxes(
            title_text=yaxis_title,
            showgrid=True,
            gridcolor='rgba(226,232,240,0.7)',
            zeroline=False,
            linecolor='rgba(148,163,184,0.8)',
            tickfont=dict(family=self.font_family, size=11)
        )

    def _format_column_label(self, column: Any) -> str:
        """将数据列名格式化为更适合图表展示的标签。"""
        label = str(column).strip() if column is not None else ''
        if not label:
            return '未命名字段'
        if label.lower().startswith('unnamed:'):
            suffix = label.split(':', 1)[1].strip() if ':' in label else ''
            return f"索引列 {suffix}" if suffix else "索引列"
        return label
        
    def create_correlation_heatmap(self, df: pd.DataFrame, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建相关性热力图"""
        try:
            if config is None:
                config = {}
            
            # 只选择数值列
            numeric_df = df.select_dtypes(include=[np.number])
            
            if numeric_df.empty:
                raise ValidationException("没有数值型数据可用于相关性分析")
            
            # 计算相关性矩阵
            method = config.get('method', 'pearson')
            corr_matrix = numeric_df.corr(method=method)
            
            # 创建热力图
            fig = px.imshow(
                corr_matrix,
                text_auto=True,
                aspect="auto",
                color_continuous_scale=config.get('colorscale', 'RdBu_r'),
                title=f"变量相关性热力图 ({method.capitalize()}相关系数)",
                template=self.default_theme
            )

            # 更新布局
            self._apply_standard_layout(
                fig,
                f"变量相关性热力图 ({method.capitalize()}相关系数)",
                config,
                xaxis_title="变量",
                yaxis_title="变量",
                showlegend=False
            )
            
            return {
                'figure': fig,
                'correlation_matrix': corr_matrix.to_dict(),
                'method': method,
                'chart_type': 'heatmap'
            }
            
        except Exception as e:
            logger.error(f"创建热力图失败: {str(e)}")
            raise DataException(f"创建热力图失败: {str(e)}")
    
    def create_scatter_plot(self, df: pd.DataFrame, x_col: str, y_col: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建散点图"""
        try:
            if config is None:
                config = {}
            
            if x_col not in df.columns or y_col not in df.columns:
                raise ValidationException(f"指定的列不存在: {x_col}, {y_col}")
            
            # 检查数据类型
            if not (is_numeric_dtype(df[x_col]) and is_numeric_dtype(df[y_col])):
                raise ValidationException("散点图需要数值型数据")

            plot_df = df[[x_col, y_col]].dropna().copy()
            if plot_df.empty:
                raise ValidationException("散点图缺少可用的数值数据")
            
            # 创建散点图
            fig = px.scatter(
                plot_df,
                x=x_col,
                y=y_col,
                title=f"{x_col} 与 {y_col} 的关系散点图",
                template=self.default_theme,
                color_discrete_sequence=[self.color_palette[0]]
            )
            
            # 添加趋势线
            if config.get('add_trendline', False) or config.get('show_regression_info', False):
                slope, intercept, r_value, p_value, std_err = stats.linregress(plot_df[x_col], plot_df[y_col])
                regression_stats = {
                    'slope': slope,
                    'intercept': intercept,
                    'r_squared': r_value**2,
                    'p_value': p_value
                }

            if config.get('add_trendline', False) and regression_stats is not None:
                trend_x = np.linspace(plot_df[x_col].min(), plot_df[x_col].max(), 100)
                trend_line = slope * trend_x + intercept
                
                fig.add_trace(
                    go.Scatter(
                        x=trend_x,
                        y=trend_line,
                        mode='lines',
                        name=f'趋势线（R² = {r_value**2:.3f}）',
                        line=dict(color='#ef4444', dash='dash', width=2.2)
                    )
                )
            
            # 添加回归方程信息
            if config.get('show_regression_info', False) and regression_stats is not None:
                sign = '+' if intercept >= 0 else '-'
                equation = f"y = {slope:.3f}x {sign} {abs(intercept):.3f}"
                r_squared = f"R² = {r_value**2:.3f}"
                p_val = f"p = {p_value:.4g}"
                
                fig.add_annotation(
                    text=f"<b>线性拟合结果</b><br>{equation}<br>{r_squared}<br>{p_val}",
                    xref="paper", yref="paper",
                    x=0.985, y=0.03,
                    xanchor="right", yanchor="bottom",
                    showarrow=False,
                    align="left",
                    bgcolor="rgba(255,255,255,0.96)",
                    bordercolor="#cbd5e1",
                    borderwidth=1,
                    borderpad=8,
                    font=dict(size=11, family=self.font_family, color="#334155")
                )
            
            self._apply_standard_layout(
                fig,
                f"{x_col} 与 {y_col} 的关系散点图",
                config,
                xaxis_title=x_col,
                yaxis_title=y_col,
                showlegend=config.get('add_trendline', False)
            )
            
            return {
                'figure': fig,
                'correlation': plot_df[x_col].corr(plot_df[y_col]),
                'chart_type': 'scatter',
                'regression_stats': regression_stats
            }
            
        except Exception as e:
            logger.error(f"创建散点图失败: {str(e)}")
            raise DataException(f"创建散点图失败: {str(e)}")
    
    def create_distribution_plot(self, df: pd.DataFrame, column: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建分布图（直方图 + 箱线图）"""
        try:
            if config is None:
                config = {}
            
            if column not in df.columns:
                raise ValidationException(f"指定的列不存在: {column}")
            
            if not is_numeric_dtype(df[column]):
                raise ValidationException("分布图需要数值型数据")

            display_column = self._format_column_label(column)
            series = df[column].dropna()
            if series.empty:
                raise ValidationException("分布图缺少可用的数值数据")
            
            # 创建子图
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=(f"{display_column} · 频数分布", f"{display_column} · 箱线分布"),
                vertical_spacing=0.14
            )
            
            # 直方图
            fig.add_trace(
                go.Histogram(
                    x=series,
                    nbinsx=config.get('bins', 30),
                    name='频数分布',
                    marker_color=config.get('color', 'rgba(125, 211, 252, 0.78)'),
                    marker_line=dict(width=0.6, color='rgba(14, 116, 144, 0.18)')
                ),
                row=1, col=1
            )
            
            # 箱线图
            fig.add_trace(
                go.Box(
                    y=series,
                    name='箱线分布',
                    marker_color='rgba(134, 239, 172, 0.88)',
                    line=dict(color='rgba(22, 163, 74, 0.8)')
                ),
                row=2, col=1
            )
            
            # 添加统计信息
            stats_info = {
                'mean': series.mean(),
                'median': series.median(),
                'std': series.std(),
                'min': series.min(),
                'max': series.max(),
                'q25': series.quantile(0.25),
                'q75': series.quantile(0.75),
                'skewness': stats.skew(series),
                'kurtosis': stats.kurtosis(series)
            }
            
            # 在直方图上添加统计线
            fig.add_vline(
                x=stats_info['mean'],
                line_dash="dash",
                line_color="#ef4444",
                line_width=2,
                row=1,
                col=1
            )
            fig.add_vline(
                x=stats_info['median'],
                line_dash="dash",
                line_color="#2563eb",
                line_width=2,
                row=1,
                col=1
            )

            fig.add_annotation(
                xref="paper",
                yref="paper",
                x=0.985,
                y=0.965,
                xanchor="right",
                yanchor="top",
                showarrow=False,
                align="left",
                text=(
                    f"<b>统计摘要</b><br>"
                    f"均值 = {stats_info['mean']:.2f}<br>"
                    f"中位数 = {stats_info['median']:.2f}<br>"
                    f"标准差 = {stats_info['std']:.2f}"
                ),
                bgcolor="rgba(255,255,255,0.96)",
                bordercolor="#cbd5e1",
                borderwidth=1,
                borderpad=8,
                font=dict(size=11, family=self.font_family, color="#334155")
            )
            
            # 更新布局
            self._apply_standard_layout(fig, f"{display_column} 分布分析", config, xaxis_title=display_column, showlegend=False)
            fig.update_yaxes(title_text='频数', row=1, col=1)
            fig.update_yaxes(title_text='取值范围', row=2, col=1)
            
            return {
                'figure': fig,
                'statistics': stats_info,
                'chart_type': 'distribution'
            }
            
        except Exception as e:
            logger.error(f"创建分布图失败: {str(e)}")
            raise DataException(f"创建分布图失败: {str(e)}")
    
    def create_box_plot(self, df: pd.DataFrame, value_col: str, group_col: str = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建箱线图"""
        try:
            if config is None:
                config = {}
            
            if value_col not in df.columns:
                raise ValidationException(f"指定的数值列不存在: {value_col}")
            
            if group_col and group_col not in df.columns:
                raise ValidationException(f"指定的分组列不存在: {group_col}")
            
            if not is_numeric_dtype(df[value_col]):
                raise ValidationException("箱线图需要数值型数据")
            
            # 创建箱线图
            if group_col:
                fig = px.box(
                    df,
                    x=group_col,
                    y=value_col,
                    title=f"{value_col} 按 {group_col} 分组的箱线图",
                    template=self.default_theme,
                    color_discrete_sequence=self.color_palette
                )
            else:
                fig = px.box(
                    df,
                    y=value_col,
                    title=f"{value_col} 箱线图",
                    template=self.default_theme
                )
            
            # 添加数据点
            if config.get('show_points', True):
                fig.update_traces(boxpoints='outliers')
            
            # 更新布局
            fig.update_layout(
                width=config.get('width', 800),
                height=config.get('height', 600),
                title_font_size=16
            )
            
            return {
                'figure': fig,
                'chart_type': 'boxplot',
                'group_column': group_col
            }
            
        except Exception as e:
            logger.error(f"创建箱线图失败: {str(e)}")
            raise DataException(f"创建箱线图失败: {str(e)}")
    
    def create_bar_chart(self, df: pd.DataFrame, x_col: str, y_col: str = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建柱状图"""
        try:
            if config is None:
                config = {}
            
            if x_col not in df.columns:
                raise ValidationException(f"指定的列不存在: {x_col}")
            
            # 如果没有指定y列，则计算频数
            if y_col is None:
                value_counts = df[x_col].value_counts().head(config.get('top_n', 20))
                plot_df = pd.DataFrame({
                    x_col: value_counts.index,
                    'count': value_counts.values
                })
                y_col = 'count'
                title = f"{x_col} 频数分布"
            else:
                if y_col not in df.columns:
                    raise ValidationException(f"指定的数值列不存在: {y_col}")
                
                # 如果x列是分类变量，按y列的均值聚合
                if not is_numeric_dtype(df[y_col]):
                    raise ValidationException("分组柱状图的纵轴必须是数值型数据")

                if not is_numeric_dtype(df[x_col]):
                    # 添加空值检查防止 NoneType groups 错误
                    if df is None or df.empty:
                        raise ValidationException("数据为空，无法生成图表")
                    if x_col not in df.columns or y_col not in df.columns:
                        raise ValidationException(f"指定的列不存在: {x_col}, {y_col}")
                    group_df = df[[x_col, y_col]].dropna().copy()
                    plot_df = (
                        group_df.groupby(x_col, dropna=False)[y_col]
                        .mean()
                        .sort_values(ascending=False)
                        .head(config.get('top_n', 20))
                        .reset_index()
                    )
                    title = f"{y_col} 按 {x_col} 分组的均值对比"
                else:
                    if df is None or df.empty:
                        raise ValidationException("数据为空，无法生成图表")
                    if x_col not in df.columns or y_col not in df.columns:
                        raise ValidationException(f"指定的列不存在: {x_col}, {y_col}")
                    numeric_df = df[[x_col, y_col]].dropna().copy()
                    if numeric_df.empty:
                        raise ValidationException("柱状图缺少可用数据")
                    plot_df = numeric_df.sort_values(y_col, ascending=False).head(config.get('top_n', 20))
                    title = f"{x_col} 与 {y_col} 对比"
            
            # 创建柱状图
            fig = px.bar(
                plot_df,
                x=x_col,
                y=y_col,
                title=title,
                template=self.default_theme,
                color_discrete_sequence=[self.color_palette[1]]
            )
            
            # 添加数值标签
            if config.get('show_values', True):
                fig.update_traces(
                    texttemplate='%{y:.2f}',
                    textposition='outside',
                    marker=dict(line=dict(width=0.6, color='rgba(15,23,42,0.18)'))
                )
            
            self._apply_standard_layout(
                fig,
                title,
                config,
                xaxis_title=x_col,
                yaxis_title=y_col,
                showlegend=False
            )
            fig.update_xaxes(tickangle=config.get('xaxis_angle', -35))
            
            return {
                'figure': fig,
                'chart_type': 'bar',
                'data_summary': {
                    'total_categories': len(plot_df),
                    'max_value': plot_df[y_col].max(),
                    'min_value': plot_df[y_col].min()
                }
            }
            
        except Exception as e:
            logger.error(f"创建柱状图失败: {str(e)}")
            raise DataException(f"创建柱状图失败: {str(e)}")
    
    def create_line_plot(self, df: pd.DataFrame, x_col: str, y_col: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建折线图"""
        try:
            if config is None:
                config = {}
            
            if x_col not in df.columns or y_col not in df.columns:
                raise ValidationException(f"指定的列不存在: {x_col}, {y_col}")
            
            # 按x列排序
            plot_df = df.sort_values(x_col)
            
            # 创建折线图
            fig = px.line(
                plot_df,
                x=x_col,
                y=y_col,
                title=f"{y_col} 随 {x_col} 的变化趋势",
                template=self.default_theme,
                markers=config.get('show_markers', True),
                color_discrete_sequence=self.color_palette
            )
            
            # 添加趋势线
            if config.get('add_trendline', False):
                # 计算移动平均
                window = config.get('trendline_window', 5)
                if len(plot_df) >= window:
                    plot_df[f'{y_col}_trend'] = plot_df[y_col].rolling(window=window).mean()
                    fig.add_trace(
                        go.Scatter(
                            x=plot_df[x_col],
                            y=plot_df[f'{y_col}_trend'],
                            mode='lines',
                            name=f'{window}期移动平均',
                            line=dict(color='red', dash='dash')
                        )
                    )
            
            # 更新布局
            fig.update_layout(
                width=config.get('width', 800),
                height=config.get('height', 600),
                title_font_size=16
            )
            
            return {
                'figure': fig,
                'chart_type': 'line',
                'trend_analysis': {
                    'increasing': (plot_df[y_col].iloc[-1] > plot_df[y_col].iloc[0]),
                    'change_rate': ((plot_df[y_col].iloc[-1] - plot_df[y_col].iloc[0]) / plot_df[y_col].iloc[0]) * 100
                }
            }
            
        except Exception as e:
            logger.error(f"创建折线图失败: {str(e)}")
            raise DataException(f"创建折线图失败: {str(e)}")
    
    def create_association_rules_network(self, rules_df: pd.DataFrame, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建关联规则网络图"""
        try:
            if config is None:
                config = {}
            
            required_columns = ['antecedents', 'consequents', 'support', 'confidence']
            for col in required_columns:
                if col not in rules_df.columns:
                    raise ValidationException(f"关联规则数据缺少必要列: {col}")
            
            # 提取所有唯一项
            all_items = set()
            for idx, row in rules_df.iterrows():
                if isinstance(row['antecedents'], str):
                    antecedents = row['antecedents'].split(',')
                else:
                    antecedents = list(row['antecedents'])
                
                if isinstance(row['consequents'], str):
                    consequents = row['consequents'].split(',')
                else:
                    consequents = list(row['consequents'])
                
                all_items.update(antecedents)
                all_items.update(consequents)
            
            all_items = list(all_items)
            
            # 创建节点
            nodes = []
            for i, item in enumerate(all_items):
                nodes.append({
                    'id': i,
                    'label': item,
                    'size': 10
                })
            
            # 创建边
            edges = []
            for idx, row in rules_df.iterrows():
                if isinstance(row['antecedents'], str):
                    antecedents = row['antecedents'].split(',')
                else:
                    antecedents = list(row['antecedents'])
                
                if isinstance(row['consequents'], str):
                    consequents = row['consequents'].split(',')
                else:
                    consequents = list(row['consequents'])
                
                for antecedent in antecedents:
                    for consequent in consequents:
                        ant_idx = all_items.index(antecedent)
                        con_idx = all_items.index(consequent)
                        
                        edges.append({
                            'source': ant_idx,
                            'target': con_idx,
                            'value': row['support'] * 10,  # 边的粗细
                            'label': f"支持度: {row['support']:.3f}<br>置信度: {row['confidence']:.3f}",
                            'color': f'rgba(255, 0, 0, {row["confidence"]})'  # 根据置信度设置颜色
                        })
            
            # 使用Plotly创建网络图
            edge_x = []
            edge_y = []
            for edge in edges:
                x0, y0 = nodes[edge['source']]['id'] % 5, nodes[edge['source']]['id'] // 5
                x1, y1 = nodes[edge['target']]['id'] % 5, nodes[edge['target']]['id'] // 5
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
            
            node_x = []
            node_y = []
            node_text = []
            for node in nodes:
                x, y = node['id'] % 5, node['id'] // 5
                node_x.append(x)
                node_y.append(y)
                node_text.append(node['label'])
            
            # 创建图形
            fig = go.Figure()
            
            # 添加边
            fig.add_trace(go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=0.5, color='#888'),
                hoverinfo='none',
                mode='lines'
            ))
            
            # 添加节点
            fig.add_trace(go.Scatter(
                x=node_x, y=node_y,
                mode='markers+text',
                hoverinfo='text',
                text=node_text,
                textposition="middle center",
                marker=dict(
                    size=20,
                    color='lightblue',
                    line=dict(width=2, color='darkblue')
                )
            ))
            
            # 更新布局
            fig.update_layout(
                title=dict(
                    text="关联规则网络图",
                    font=dict(size=16)
                ),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20,l=5,r=5,t=40),
                annotations=[ dict(
                    text="节点表示项目，连线表示关联关系",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.005, y=-0.002,
                    xanchor='left', yanchor='bottom',
                    font=dict(color='black', size=12)
                )],
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                template=self.default_theme
            )
            
            return {
                'figure': fig,
                'chart_type': 'network',
                'nodes_count': len(nodes),
                'edges_count': len(edges)
            }
            
        except Exception as e:
            logger.error(f"创建关联规则网络图失败: {str(e)}")
            raise DataException(f"创建关联规则网络图失败: {str(e)}")
    
    def create_dashboard(self, df: pd.DataFrame, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建综合仪表板"""
        try:
            if config is None:
                config = {}
            
            # 创建子图
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    "数据概览", "数值变量分布",
                    "相关性热力图", "分类变量分布"
                ),
                specs=[
                    [{"type": "table"}, {"type": "histogram"}],
                    [{"type": "heatmap"}, {"type": "bar"}]
                ]
            )
            
            # 1. 数据概览表
            data_overview = pd.DataFrame({
                '指标': ['总行数', '总列数', '数值列数', '分类列数', '缺失值总数', '重复行数'],
                '值': [
                    len(df),
                    len(df.columns),
                    len(df.select_dtypes(include=[np.number]).columns),
                    len(df.select_dtypes(include=['object', 'category']).columns),
                    df.isnull().sum().sum(),
                    df.duplicated().sum()
                ]
            })
            
            fig.add_trace(
                go.Table(
                    header=dict(values=list(data_overview.columns)),
                    cells=dict(values=[data_overview['指标'], data_overview['值']])
                ),
                row=1, col=1
            )
            
            # 2. 数值变量分布（选择第一个数值列）
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                fig.add_trace(
                    go.Histogram(x=df[numeric_cols[0]], name=numeric_cols[0]),
                    row=1, col=2
                )
            
            # 3. 相关性热力图
            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr()
                fig.add_trace(
                    go.Heatmap(
                        z=corr_matrix.values,
                        x=corr_matrix.columns,
                        y=corr_matrix.columns,
                        colorscale='RdBu',
                        name='相关性'
                    ),
                    row=2, col=1
                )
            
            # 4. 分类变量分布（选择第一个分类列）
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns
            if len(categorical_cols) > 0:
                value_counts = df[categorical_cols[0]].value_counts().head(10)
                fig.add_trace(
                    go.Bar(
                        x=value_counts.index,
                        y=value_counts.values,
                        name=categorical_cols[0]
                    ),
                    row=2, col=2
                )
            
            # 更新布局
            fig.update_layout(
                title="数据分析仪表板",
                template=self.default_theme,
                height=800,
                showlegend=False
            )
            
            return {
                'figure': fig,
                'chart_type': 'dashboard',
                'summary_stats': {
                    'shape': df.shape,
                    'numeric_columns': len(numeric_cols),
                    'categorical_columns': len(categorical_cols),
                    'missing_values': df.isnull().sum().sum(),
                    'duplicates': df.duplicated().sum()
                }
            }
            
        except Exception as e:
            logger.error(f"创建仪表板失败: {str(e)}")
            raise DataException(f"创建仪表板失败: {str(e)}")
    
    def export_chart(self, figure, filename: str, format: str = 'html') -> str:
        """导出图表"""
        try:
            if format.lower() == 'html':
                figure.write_html(filename)
            elif format.lower() == 'png':
                figure.write_image(filename)
            elif format.lower() == 'pdf':
                figure.write_image(filename)
            elif format.lower() == 'svg':
                figure.write_image(filename)
            else:
                raise ValidationException(f"不支持的导出格式: {format}")
            
            return f"图表已导出至: {filename}"
            
        except Exception as e:
            logger.error(f"导出图表失败: {str(e)}")
            raise DataException(f"导出图表失败: {str(e)}")

# 创建全局实例
visualization_service = VisualizationService()
