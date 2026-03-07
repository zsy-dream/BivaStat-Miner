import os
import json
import markdown
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

# Premium CSS for AI Section
AI_STYLE = """
<style>
    .ai-smart-analysis {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
        border-left: 5px solid #007bff;
        padding: 25px;
        margin: 30px 0;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        position: relative;
        overflow: hidden;
    }
    .ai-smart-analysis::before {
        content: 'AI';
        position: absolute;
        top: -10px;
        right: -10px;
        font-size: 80px;
        color: rgba(0, 123, 255, 0.05);
        font-weight: bold;
        pointer-events: none;
    }
    .ai-smart-analysis h2 {
        color: #007bff;
        margin-top: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .ai-smart-analysis h2::after {
        content: '🤖 智能解读';
        font-size: 0.6em;
        background: #007bff;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
    }
    .ai-smart-analysis table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
        background: white;
        border-radius: 8px;
        overflow: hidden;
    }
    .ai-smart-analysis th, .ai-smart-analysis td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #eee;
    }
    .ai-smart-analysis th {
        background-color: #f8f9fa;
        color: #333;
    }
</style>
"""


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

            analysis_results = self._dedupe_ai_sections(analysis_results)
            
            # 准备报告数据
            exec_summary = self._generate_executive_summary(data_info, analysis_results)
            report_data = {
                'title': config.get('title', '数据分析报告'),
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'author': config.get('author', '系统自动生成'),
                'version': '1.0',
                'data_info': data_info,
                'analysis_results': analysis_results,
                'preprocessing_info': preprocessing_info,
                'executive_summary': exec_summary,
                # 结论：默认复用 key_findings（可后续扩展为更结构化的结论）
                'conclusions': exec_summary.get('key_findings', []) if isinstance(exec_summary, dict) else [],
                'recommendations': self._generate_recommendations(analysis_results, template_type),
                # 关键：传递 AI 摘要 HTML 到模板渲染上下文
                'ai_executive_summary_html': analysis_results.get('ai_executive_summary_html', ''),
                'ai_analysis_html': analysis_results.get('ai_analysis_html', ''),
            }
            
            # 生成图表
            charts = self._generate_report_charts(analysis_results, config)
            report_data['charts'] = charts
            
            # 生成统计表格
            tables = self._generate_report_tables(analysis_results)
            report_data['tables'] = tables
            
            # 注入真实的关联规则摘要数据到报告
            rules = analysis_results.get('association_rules', [])
            summary = analysis_results.get('summary', {})
            if isinstance(rules, list) and rules:
                report_data['rules_summary'] = {
                    'total': len(rules),
                    'high_confidence': len([r for r in rules if (self._to_float(r.get('confidence'), 0.0) or 0.0) > 0.8]),
                    'avg_lift': round(sum((self._to_float(r.get('lift'), 0.0) or 0.0) for r in rules) / len(rules), 3),
                    'avg_confidence': round(sum((self._to_float(r.get('confidence'), 0.0) or 0.0) for r in rules) / len(rules), 3),
                    'top_rules': [
                        {
                            **rule,
                            'antecedents': self._stringify_rule_side(rule.get('antecedents')),
                            'consequents': self._stringify_rule_side(rule.get('consequents'))
                        }
                        for rule in sorted(rules, key=lambda r: self._to_float(r.get('lift'), 0.0) or 0.0, reverse=True)[:5]
                    ]
                }
            if summary:
                report_data['mining_summary'] = summary
            
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

    def _dedupe_ai_sections(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """避免 AI 执行摘要与 AI 深度解读内容完全相同导致重复渲染。"""
        normalized_results = dict(analysis_results or {})
        ai_exec = normalized_results.get('ai_executive_summary')
        ai_analysis = normalized_results.get('ai_analysis')

        if self._normalize_ai_text(ai_exec) and self._normalize_ai_text(ai_exec) == self._normalize_ai_text(ai_analysis):
            normalized_results['ai_analysis'] = ''
            normalized_results.pop('ai_analysis_html', None)

        return normalized_results

    def _normalize_ai_text(self, content: Any) -> str:
        """对 AI 文本做轻量归一化，用于重复内容判断。"""
        if not isinstance(content, str):
            return ''
        return ' '.join(content.split()).strip()
    
    def _generate_executive_summary(self, data_info: Dict[str, Any], analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成数据驱动的执行摘要"""
        try:
            shape = data_info.get('shape', [0, 0])
            summary = {
                'data_overview': {
                    'total_records': shape[0],
                    'total_features': shape[1],
                    'numeric_features': len(data_info.get('numeric_columns', [])),
                    'categorical_features': len(data_info.get('categorical_columns', []))
                },
                'key_findings': [],
                'data_quality_score': 0.0,
                'analysis_confidence': '中等'
            }

            # ---------- 数据质量评分 ----------
            quality_score = 0.0
            if 'quality_report' in data_info:
                quality = data_info['quality_report']
                total_cells = shape[0] * shape[1] if shape[0] and shape[1] else 1
                missing_ratio = quality['missing_values']['total_missing'] / total_cells
                duplicate_ratio = quality['duplicates']['duplicate_percentage'] / 100
                quality_score = max(0, 100 - (missing_ratio * 50) - (duplicate_ratio * 30))
            summary['data_quality_score'] = round(quality_score, 2)

            findings = summary['key_findings']
            rules = analysis_results.get('association_rules') or []
            if not isinstance(rules, list):
                rules = []
            mining = analysis_results.get('summary', {}) if isinstance(analysis_results.get('summary'), dict) else {}
            p_thr = float(mining.get('p_value_threshold', 0.05) or 0.05)

            # ---------- 规则统计发现 ----------
            if rules:
                total = len(rules)
                high_conf = [r for r in rules if (self._to_float(r.get('confidence'), 0.0) or 0.0) > 0.8]
                high_lift = [r for r in rules if (self._to_float(r.get('lift'), 0.0) or 0.0) > 2.0]
                sig_rules = [r for r in rules if (self._to_float(r.get('p_value')) is not None) and (self._to_float(r.get('p_value'), 1.0) or 1.0) <= p_thr]

                findings.append(f"共挖掘到 {total} 条关联规则，其中 {len(high_conf)} 条置信度超过 80%")
                if high_lift:
                    findings.append(f"{len(high_lift)} 条规则提升度 (Lift) 超过 2.0，表明变量间存在强关联")
                if sig_rules:
                    findings.append(f"{len(sig_rules)} 条规则通过统计显著性检验 (P < {p_thr})，结果具有统计可信度")

                # 提取最强规则具体内容
                top_rule = max(rules, key=lambda r: self._to_float(r.get('lift'), 0.0) or 0.0)
                ant = self._stringify_rule_side(top_rule.get('antecedents'))
                con = self._stringify_rule_side(top_rule.get('consequents'))
                top_lift = self._to_float(top_rule.get('lift'), 0.0) or 0.0
                top_conf = self._to_float(top_rule.get('confidence'), 0.0) or 0.0
                if ant and con:
                    findings.append(
                        f"最强关联：「{ant}」→「{con}」"
                        f"（Lift={top_lift:.2f}, 置信度={top_conf:.0%}）"
                    )

                # 高频后件汇总
                consequent_freq: Dict[str, int] = {}
                for r in rules:
                    c = self._stringify_rule_side(r.get('consequents'))
                    if c:
                        consequent_freq[c] = consequent_freq.get(c, 0) + 1
                if consequent_freq:
                    top_con = max(consequent_freq, key=consequent_freq.get)  # type: ignore[arg-type]
                    findings.append(f"最常触发的结果变量为「{top_con}」，共在 {consequent_freq[top_con]} 条规则中出现")

                # 平均 Lift 水平评估
                avg_lift = sum((self._to_float(r.get('lift'), 0.0) or 0.0) for r in rules) / total
                if avg_lift > 2.0:
                    findings.append(f"整体平均 Lift = {avg_lift:.2f}，规则关联强度较高")
                elif avg_lift > 1.2:
                    findings.append(f"整体平均 Lift = {avg_lift:.2f}，存在有意义的关联但非极强")

            # ---------- 统计检验发现 ----------
            tests = self._normalize_tests_payload(analysis_results.get('statistical_tests'))
            if tests:
                sig_tests = [t for t in tests if (self._to_float(t.get('p_value')) is not None) and (self._to_float(t.get('p_value'), 1.0) or 1.0) <= p_thr]
                findings.append(f"共执行 {len(tests)} 项统计检验，{len(sig_tests)} 项达到显著水平 (P < {p_thr})")
                if sig_tests:
                    best = min(sig_tests, key=lambda t: self._to_float(t.get('p_value'), 1.0) or 1.0)
                    tname = best.get('test_name', '未名检验')
                    best_p = self._to_float(best.get('p_value'), 0.0) or 0.0
                    findings.append(f"最显著检验：{tname}（P = {best_p:.4f}）")

            # ---------- 分析置信度等级 ----------
            confidence_level = '低'
            if rules and tests:
                sig_rule_ratio = len([
                    r for r in rules
                    if (self._to_float(r.get('p_value')) is not None) and (self._to_float(r.get('p_value'), 1.0) or 1.0) <= p_thr
                ]) / max(len(rules), 1)
                if sig_rule_ratio > 0.6 and quality_score > 80:
                    confidence_level = '高'
                elif sig_rule_ratio > 0.3 or quality_score > 60:
                    confidence_level = '中等'
            elif rules:
                confidence_level = '中等' if len(rules) > 5 else '低'
            summary['analysis_confidence'] = confidence_level

            return summary

        except Exception as e:
            logger.error(f"生成执行摘要失败: {str(e)}")
            return {'key_findings': [], 'data_overview': {}, 'data_quality_score': 0, 'analysis_confidence': '未知'}
    
    def _generate_recommendations(self, analysis_results: Dict[str, Any], template_type: str) -> List[str]:
        """基于实际规则和统计检验生成具体业务建议"""
        try:
            recs: List[str] = []
            rules = analysis_results.get('association_rules') or []
            if not isinstance(rules, list):
                rules = []
            mining = analysis_results.get('summary', {}) if isinstance(analysis_results.get('summary'), dict) else {}
            p_thr = float(mining.get('p_value_threshold', 0.05) or 0.05)
            tests = self._normalize_tests_payload(analysis_results.get('statistical_tests'))

            # --- 规则驱动建议 ---
            if rules:
                top3 = sorted(rules, key=lambda r: self._to_float(r.get('lift'), 0.0) or 0.0, reverse=True)[:3]
                for r in top3:
                    ant = self._stringify_rule_side(r.get('antecedents'))
                    con = self._stringify_rule_side(r.get('consequents'))
                    lift = self._to_float(r.get('lift'), 0.0) or 0.0
                    conf = self._to_float(r.get('confidence'), 0.0) or 0.0
                    if not ant or not con:
                        continue
                    if template_type == 'financial_risk':
                        recs.append(f"重点监控「{ant}」对「{con}」的风险传导（Lift={lift:.2f}, 置信度={conf:.0%}），考虑将其纳入风控规则引擎")
                    elif template_type == 'market_analysis':
                        recs.append(f"「{ant}」与「{con}」强关联（Lift={lift:.2f}），建议将其作为交叉营销/捆绑销售的候选组合")
                    else:
                        recs.append(f"关注「{ant}」→「{con}」的强关联（Lift={lift:.2f}, 置信度={conf:.0%}），建议纳入业务决策考量")

                # 高频后件分析
                con_freq: Dict[str, int] = {}
                for r in rules:
                    c = self._stringify_rule_side(r.get('consequents'))
                    if c:
                        con_freq[c] = con_freq.get(c, 0) + 1
                if con_freq:
                    top_con = max(con_freq, key=con_freq.get)  # type: ignore[arg-type]
                    if template_type == 'financial_risk':
                        recs.append(f"「{top_con}」是被触发最多的风险事件（{con_freq[top_con]} 条规则指向它），建议为其单独建立早期预警机制")
                    elif template_type == 'market_analysis':
                        recs.append(f"「{top_con}」是关联规则中最常见的结果标签，建议围绕其设计营销落地页与推荐算法")
                    else:
                        recs.append(f"「{top_con}」在 {con_freq[top_con]} 条规则中作为结果变量出现，建议优先进行因果分析")

            # --- 统计检验驱动建议 ---
            if tests:
                with_p = []
                for t in tests:
                    pv = self._to_float(t.get('p_value'))
                    if pv is None:
                        continue
                    with_p.append((t, pv))
                sig_tests = [t for t, pv in with_p if pv <= p_thr]
                non_sig = [t for t, pv in with_p if pv > p_thr]
                if sig_tests:
                    names = ', '.join(t.get('test_name', '?') for t in sig_tests[:3])
                    recs.append(f"{len(sig_tests)} 项检验达显著水平（如 {names}），相关变量关系已得到统计上确认")
                if non_sig:
                    recs.append(f"{len(non_sig)} 项检验未达显著，相关关联可能受样本量或数据分布影响，建议增加样本量后再次验证")

            # --- 数据质量建议 ---
            missing = analysis_results.get('data_info', {}).get('missing_total', 0)
            if missing and missing > 0:
                recs.append(f"数据中存在 {missing} 个缺失值，建议在下次分析前做更细致的缺失值处理")

            # --- 保底行业建议 ---
            if template_type == 'financial_risk':
                recs.append("建议将以上高关联规则纳入贷前/贷后风控策略，并定期回溯规则变化")
            elif template_type == 'market_analysis':
                recs.append("建议将高关联规则纳入推荐算法或营销自动化引擎，并通过 A/B 测试验证效果")
            else:
                recs.append("建议将关键规则与业务专家共同评审后再落地执行，并建立定期回溯机制")

            return recs if recs else ["暂无具体建议，请先运行关联挖掘算法"]

        except Exception as e:
            logger.error(f"生成建议失败: {str(e)}")
            return ["建议生成失败，请检查分析结果"]

    def _to_float(self, value: Any, default: Optional[float] = None) -> Optional[float]:
        """安全转换为 float（解析失败返回 default）"""
        try:
            if value is None:
                return default
            if isinstance(value, str) and not value.strip():
                return default
            return float(value)
        except Exception:
            return default

    def _normalize_tests_payload(self, raw_tests: Any) -> List[Dict[str, Any]]:
        """统一统计检验结果结构为 list[dict]"""
        if isinstance(raw_tests, list):
            return raw_tests
        if isinstance(raw_tests, dict):
            if isinstance(raw_tests.get('results'), list):
                return raw_tests.get('results', [])
            if isinstance(raw_tests.get('tests'), list):
                return raw_tests.get('tests', [])
            return [raw_tests]
        return []

    def _stringify_rule_side(self, side: Any) -> str:
        """将 antecedents / consequents 统一转为可显示字符串"""
        if isinstance(side, (list, tuple, set)):
            return ", ".join(str(item) for item in side if str(item).strip())
        if side is None:
            return ""
        return str(side)

    def _prepare_rules_dataframe(self, analysis_results: Dict[str, Any]) -> pd.DataFrame:
        rules = analysis_results.get('association_rules') or analysis_results.get('rules') or []
        rules_df = pd.DataFrame(rules)
        if rules_df.empty:
            return rules_df

        if 'antecedents' in rules_df.columns:
            rules_df['antecedents_text'] = rules_df['antecedents'].apply(self._stringify_rule_side)
        else:
            rules_df['antecedents_text'] = ''

        if 'consequents' in rules_df.columns:
            rules_df['consequents_text'] = rules_df['consequents'].apply(self._stringify_rule_side)
        else:
            rules_df['consequents_text'] = ''

        for col in ['support', 'confidence', 'lift', 'p_value']:
            if col in rules_df.columns:
                rules_df[col] = pd.to_numeric(rules_df[col], errors='coerce')

        return rules_df

    def _build_rule_network_figure(self, rules_df: pd.DataFrame) -> Optional[go.Figure]:
        """使用 Sankey 构建规则网络图，适配报告展示"""
        if rules_df.empty:
            return None
        if 'antecedents_text' not in rules_df.columns or 'consequents_text' not in rules_df.columns:
            return None

        link_weights: Dict[tuple[str, str], float] = {}
        working_df = rules_df.sort_values('confidence', ascending=False) if 'confidence' in rules_df.columns else rules_df
        working_df = working_df.head(120)

        for _, row in working_df.iterrows():
            ant_text = str(row.get('antecedents_text', '') or '')
            con_text = str(row.get('consequents_text', '') or '')
            ants = [item.strip() for item in ant_text.split(',') if item.strip()]
            cons = [item.strip() for item in con_text.split(',') if item.strip()]
            if not ants or not cons:
                continue

            weight = float(row.get('confidence', row.get('support', 0.05)) or 0.05)
            weight = max(weight, 0.01)

            for ant in ants[:3]:
                for con in cons[:3]:
                    key = (ant, con)
                    link_weights[key] = link_weights.get(key, 0.0) + weight

        if not link_weights:
            return None

        # 限制节点数量，防止图过于密集
        node_degree: Dict[str, float] = {}
        for (src, dst), val in link_weights.items():
            node_degree[src] = node_degree.get(src, 0.0) + val
            node_degree[dst] = node_degree.get(dst, 0.0) + val

        top_nodes = sorted(node_degree, key=node_degree.get, reverse=True)[:26]
        top_nodes_set = set(top_nodes)
        filtered_links = [
            (src, dst, val)
            for (src, dst), val in link_weights.items()
            if src in top_nodes_set and dst in top_nodes_set
        ]
        if not filtered_links:
            return None

        nodes = sorted({src for src, _, _ in filtered_links} | {dst for _, dst, _ in filtered_links})
        idx = {name: i for i, name in enumerate(nodes)}

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=15,
                line=dict(color="rgba(80,80,80,0.4)", width=0.5),
                label=nodes,
                color="rgba(35,131,226,0.35)"
            ),
            link=dict(
                source=[idx[src] for src, _, _ in filtered_links],
                target=[idx[dst] for _, dst, _ in filtered_links],
                value=[round(val, 4) for _, _, val in filtered_links],
                color="rgba(35,131,226,0.25)"
            )
        )])
        fig.update_layout(
            title='关联规则网络图',
            template='plotly_white',
            margin=dict(l=10, r=10, t=50, b=10),
            height=500
        )
        return fig
    
    def _generate_report_charts(self, analysis_results: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """按模板和任务结果动态生成图表"""
        try:
            charts: List[Dict[str, Any]] = []
            include_visuals = bool(config.get('include_visuals', True))
            if not include_visuals:
                return charts

            template_type = str(config.get('template_type', 'general_analysis'))
            chart_candidates: Dict[str, Dict[str, Any]] = {}

            rules_df = self._prepare_rules_dataframe(analysis_results)
            summary = analysis_results.get('summary', {}) if isinstance(analysis_results.get('summary'), dict) else {}
            p_threshold = float(summary.get('p_value_threshold', 0.05) or 0.05)

            # ---------- 规则类图表 ----------
            if not rules_df.empty:
                if 'confidence' in rules_df.columns and rules_df['confidence'].notna().any():
                    fig = px.histogram(
                        rules_df.dropna(subset=['confidence']),
                        x='confidence',
                        nbins=20,
                        template='plotly_white',
                        title='关联规则置信度分布'
                    )
                    chart_candidates['confidence_dist'] = {'title': '关联规则置信度分布', 'type': 'histogram', 'figure': fig}

                if 'support' in rules_df.columns and rules_df['support'].notna().any():
                    fig = px.histogram(
                        rules_df.dropna(subset=['support']),
                        x='support',
                        nbins=20,
                        template='plotly_white',
                        title='关联规则支持度分布'
                    )
                    chart_candidates['support_dist'] = {'title': '关联规则支持度分布', 'type': 'histogram', 'figure': fig}

                if {'support', 'confidence'}.issubset(set(rules_df.columns)):
                    scatter_df = rules_df.dropna(subset=['support', 'confidence']).copy()
                    if not scatter_df.empty:
                        fig = px.scatter(
                            scatter_df,
                            x='support',
                            y='confidence',
                            size='lift' if 'lift' in scatter_df.columns else None,
                            hover_data=['antecedents_text', 'consequents_text'] if {'antecedents_text', 'consequents_text'}.issubset(scatter_df.columns) else None,
                            template='plotly_white',
                            title='支持度 vs 置信度关系'
                        )
                        chart_candidates['support_conf_scatter'] = {'title': '支持度 vs 置信度关系', 'type': 'scatter', 'figure': fig}

                if {'lift', 'confidence'}.issubset(set(rules_df.columns)):
                    sc2 = rules_df.dropna(subset=['lift', 'confidence']).copy()
                    if not sc2.empty:
                        fig = px.scatter(
                            sc2, x='confidence', y='lift',
                            size='support' if 'support' in sc2.columns else None,
                            hover_data=['antecedents_text', 'consequents_text'] if {'antecedents_text', 'consequents_text'}.issubset(sc2.columns) else None,
                            template='plotly_white',
                            title='置信度 vs 提升度关系'
                        )
                        chart_candidates['conf_lift_scatter'] = {'title': '置信度 vs 提升度关系', 'type': 'scatter', 'figure': fig}

                if {'lift', 'antecedents_text', 'consequents_text'}.issubset(set(rules_df.columns)):
                    top_df = rules_df.dropna(subset=['lift']).sort_values('lift', ascending=False).head(15).copy()
                    if not top_df.empty:
                        top_df['rule_label'] = top_df['antecedents_text'] + ' → ' + top_df['consequents_text']
                        fig = px.bar(
                            top_df.sort_values('lift', ascending=True),
                            x='lift',
                            y='rule_label',
                            orientation='h',
                            template='plotly_white',
                            title='Top 规则提升度排行（Lift）'
                        )
                        fig.update_layout(yaxis_title='规则', xaxis_title='Lift')
                        chart_candidates['topn_lift'] = {'title': 'Top 规则提升度排行（Lift）', 'type': 'bar', 'figure': fig}

                if {'confidence', 'antecedents_text', 'consequents_text'}.issubset(set(rules_df.columns)):
                    topconf = rules_df.dropna(subset=['confidence']).sort_values('confidence', ascending=False).head(15).copy()
                    if not topconf.empty:
                        topconf['rule_label'] = topconf['antecedents_text'] + ' → ' + topconf['consequents_text']
                        fig = px.bar(
                            topconf.sort_values('confidence', ascending=True),
                            x='confidence', y='rule_label', orientation='h',
                            template='plotly_white',
                            title='Top 规则置信度排行'
                        )
                        fig.update_layout(yaxis_title='规则', xaxis_title='Confidence')
                        chart_candidates['topn_confidence'] = {'title': 'Top 规则置信度排行', 'type': 'bar', 'figure': fig}

                # 前件/后件出现频次 Top 10
                if 'antecedents_text' in rules_df.columns and 'consequents_text' in rules_df.columns:
                    items: Dict[str, int] = {}
                    for _, row in rules_df.iterrows():
                        for side in ['antecedents_text', 'consequents_text']:
                            parts = [p.strip() for p in str(row.get(side, '')).split(',') if p.strip()]
                            for p in parts:
                                items[p] = items.get(p, 0) + 1
                    if items:
                        freq_df = pd.DataFrame(sorted(items.items(), key=lambda x: x[1], reverse=True)[:10], columns=['变量', '出现次数'])
                        fig = px.bar(freq_df.sort_values('出现次数'), x='出现次数', y='变量', orientation='h', template='plotly_white', title='规则中变量出现频次 Top 10')
                        chart_candidates['item_frequency'] = {'title': '规则中变量出现频次 Top 10', 'type': 'bar', 'figure': fig}

                sig_series = None
                if 'significant' in rules_df.columns:
                    sig_series = rules_df['significant'].fillna(False).astype(bool)
                elif 'p_value' in rules_df.columns:
                    sig_series = rules_df['p_value'].fillna(1.0) <= p_threshold
                if sig_series is not None:
                    sig_cnt = int(sig_series.sum())
                    non_sig_cnt = int(len(sig_series) - sig_cnt)
                    if sig_cnt + non_sig_cnt > 0:
                        pie_df = pd.DataFrame({
                            '类别': ['显著规则', '非显著规则'],
                            '数量': [sig_cnt, non_sig_cnt]
                        })
                        fig = px.pie(
                            pie_df,
                            names='类别',
                            values='数量',
                            hole=0.55,
                            template='plotly_white',
                            title=f'规则显著性占比 (阈值 P<{p_threshold})'
                        )
                        chart_candidates['rule_significance_ratio'] = {'title': f'规则显著性占比 (阈值 P<{p_threshold})', 'type': 'pie', 'figure': fig}

                network_fig = self._build_rule_network_figure(rules_df)
                if network_fig is not None:
                    chart_candidates['rule_network'] = {'title': '关联规则网络图', 'type': 'network', 'figure': network_fig}

            # ---------- 统计检验类图表 ----------
            tests = self._normalize_tests_payload(analysis_results.get('statistical_tests'))
            tests_df = pd.DataFrame(tests)
            if not tests_df.empty and 'p_value' in tests_df.columns:
                tests_df['p_value'] = pd.to_numeric(tests_df['p_value'], errors='coerce')
                tests_df = tests_df.dropna(subset=['p_value'])
                if not tests_df.empty:
                    fig = px.histogram(
                        tests_df,
                        x='p_value',
                        nbins=20,
                        template='plotly_white',
                        title='统计检验P值分布'
                    )
                    chart_candidates['test_pvalue_dist'] = {'title': '统计检验P值分布', 'type': 'histogram', 'figure': fig}

                    sig_cnt = int((tests_df['p_value'] <= p_threshold).sum())
                    non_sig_cnt = int((tests_df['p_value'] > p_threshold).sum())
                    ratio_df = pd.DataFrame({
                        '类别': ['显著检验', '非显著检验'],
                        '数量': [sig_cnt, non_sig_cnt]
                    })
                    fig_ratio = px.pie(
                        ratio_df,
                        names='类别',
                        values='数量',
                        hole=0.5,
                        template='plotly_white',
                        title=f'统计检验显著性占比 (P<{p_threshold})'
                    )
                    chart_candidates['test_significance_ratio'] = {'title': f'统计检验显著性占比 (P<{p_threshold})', 'type': 'pie', 'figure': fig_ratio}

            # ---------- 模板差异化图表顺序 ----------
            orders = {
                'financial_risk': [
                    'topn_lift',
                    'rule_significance_ratio',
                    'support_conf_scatter',
                    'conf_lift_scatter',
                    'rule_network',
                    'topn_confidence',
                    'confidence_dist',
                    'support_dist',
                    'item_frequency',
                    'test_significance_ratio',
                    'test_pvalue_dist',
                ],
                'market_analysis': [
                    'support_conf_scatter',
                    'confidence_dist',
                    'topn_lift',
                    'item_frequency',
                    'rule_network',
                    'conf_lift_scatter',
                    'topn_confidence',
                    'support_dist',
                    'rule_significance_ratio',
                    'test_pvalue_dist',
                    'test_significance_ratio',
                ],
                'general_analysis': [
                    'confidence_dist',
                    'support_conf_scatter',
                    'topn_lift',
                    'topn_confidence',
                    'rule_significance_ratio',
                    'conf_lift_scatter',
                    'rule_network',
                    'item_frequency',
                    'support_dist',
                    'test_significance_ratio',
                    'test_pvalue_dist',
                ],
            }
            selected_order = orders.get(template_type, orders['general_analysis'])

            selected_candidates: List[Dict[str, Any]] = []
            used_keys = set()
            for key in selected_order:
                if key in chart_candidates:
                    selected_candidates.append(chart_candidates[key])
                    used_keys.add(key)
            for key, item in chart_candidates.items():
                if key not in used_keys:
                    selected_candidates.append(item)

            # 仅首图注入 PlotlyJS，后续图表复用
            for idx, item in enumerate(selected_candidates):
                fig = item['figure']
                charts.append({
                    'title': item['title'],
                    'html': fig.to_html(full_html=False, include_plotlyjs=True if idx == 0 else False),
                    'type': item['type']
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
                    if 'antecedents' in rules_df.columns:
                        rules_df['antecedents'] = rules_df['antecedents'].apply(self._stringify_rule_side)
                    if 'consequents' in rules_df.columns:
                        rules_df['consequents'] = rules_df['consequents'].apply(self._stringify_rule_side)
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
                tests_df = pd.DataFrame(self._normalize_tests_payload(analysis_results['statistical_tests']))
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
        body { font-family: 'Inter', system-ui, -apple-system, sans-serif; margin: 40px; line-height: 1.6; color: #333; }
        .header { text-align: center; border-bottom: 3px solid #c0392b; padding-bottom: 30px; margin-bottom: 30px; background: linear-gradient(135deg, #fdf2f2 0%, #fff 100%); padding: 30px; border-radius: 12px 12px 0 0; }
        .header h1 { color: #1a1a1a; margin-bottom: 4px; }
        .header .subtitle { color: #c0392b; font-weight: 600; font-size: 14px; letter-spacing: 2px; text-transform: uppercase; }
        .section { margin: 40px 0; }
        .executive-summary { background-color: #fcfcfc; padding: 25px; border: 1px solid #eee; border-radius: 8px; }
        .chart { margin: 30px 0; padding: 20px; border: 1px solid #f0f0f0; border-radius: 8px; text-align: center; }
        .table-container { margin: 25px 0; overflow-x: auto; }
        .recommendations { background: linear-gradient(135deg, #fdf2f2 0%, #fff5f5 100%); padding: 25px; border-radius: 8px; border-left: 4px solid #c0392b; }
        .footer { text-align: center; margin-top: 60px; font-size: 13px; color: #888; border-top: 1px solid #eee; padding-top: 20px; }
        table { border-collapse: collapse; width: 100%; margin: 15px 0; }
        th, td { border: 1px solid #eee; padding: 12px; text-align: left; }
        th { background-color: #f8f9fa; font-weight: 600; }
        h1, h2, h3 { color: #1a1a1a; }
        .risk-badge { display: inline-block; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        .risk-high { background: #ffe0e0; color: #c0392b; }
        .risk-low { background: #d4edda; color: #155724; }
    </style>
    """ + AI_STYLE + """
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <div class="subtitle">⚠️ 金融风控分析报告</div>
        <div style="color: #666; font-size: 14px; margin-top: 8px;">
            生成时间: {{ generated_at }} | 报告编者: {{ author }}
        </div>
    </div>

    <!-- AI 智能解读区块 -->
    {% if ai_executive_summary_html %}
    <div class="section ai-smart-analysis">
        <h2>智能风控摘要</h2>
        <div class="ai-content">{{ ai_executive_summary_html|safe }}</div>
    </div>
    {% endif %}

    {% if ai_analysis_html %}
    <div class="section ai-smart-analysis">
        <h2>AI 深度风险解读</h2>
        <div class="ai-content">{{ ai_analysis_html|safe }}</div>
    </div>
    {% endif %}

    <div class="section executive-summary">
        <h2>🛡️ 风控数据概况</h2>
        <div style="display: flex; gap: 30px; flex-wrap: wrap; margin-bottom: 20px;">
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 130px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">样本量</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #1864ab;">{{ data_info.shape[0] if data_info.shape else 0 }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 130px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">风控特征</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #1864ab;">{{ data_info.shape[1] if data_info.shape else 0 }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 130px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">数据质量</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #087f5b;">{{ executive_summary.data_quality_score }}/100</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 130px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">数值变量</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #1864ab;">{{ data_info.numeric_columns | length if data_info.numeric_columns else 0 }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 130px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">分类变量</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #5f3dc4;">{{ data_info.categorical_columns | length if data_info.categorical_columns else 0 }}</p>
            </div>
        </div>

        {% if data_info.missing_total is defined %}
        <div style="background: #f1f3f5; padding: 12px 16px; border-radius: 6px; margin-bottom: 15px; font-size: 13px;">
            缺失值总计: <strong>{{ data_info.missing_total }}</strong> | 重复行: <strong>{{ data_info.duplicate_rows | default(0) }}</strong>
        </div>
        {% endif %}

        <h3 style="margin-top: 25px;">风险关键发现</h3>
        <ul style="padding-left: 20px;">
        {% for finding in executive_summary.key_findings %}
            <li>{{ finding }}</li>
        {% endfor %}
        {% if not executive_summary.key_findings %}
            <li>暂无显著风险信号，建议持续监控</li>
        {% endif %}
        </ul>
    </div>

    <!-- 关联规则挖掘概览 -->
    {% if rules_summary %}
    <div class="section" style="background: #fdf2f2; padding: 25px; border-radius: 8px; border: 1px solid #f5c6cb;">
        <h2>⛓️ 风险因子关联规则</h2>
        <div style="display: flex; gap: 30px; flex-wrap: wrap; margin-bottom: 20px;">
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 140px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">规则总数</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #c0392b;">{{ rules_summary.total }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 140px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">高置信度规则 (&gt;0.8)</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #2b8a3e;">{{ rules_summary.high_confidence }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 140px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">平均提升度</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #e67700;">{{ rules_summary.avg_lift }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 140px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">平均置信度</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #5f3dc4;">{{ rules_summary.avg_confidence }}</p>
            </div>
        </div>

        {% if rules_summary.top_rules %}
        <h3>Top 5 高风险关联规则</h3>
        <table>
            <thead><tr><th>前件</th><th>后件</th><th>支持度</th><th>置信度</th><th>提升度</th></tr></thead>
            <tbody>
            {% for rule in rules_summary.top_rules %}
                <tr>
                    <td>{{ rule.antecedents }}</td>
                    <td>{{ rule.consequents }}</td>
                    <td>{{ '%.4f' | format(rule.support | default(0)) }}</td>
                    <td>{{ '%.4f' | format(rule.confidence | default(0)) }}</td>
                    <td style="font-weight: bold; color: {% if rule.lift|default(0) > 2 %}#c0392b{% elif rule.lift|default(0) > 1.5 %}#e67700{% else %}#333{% endif %};">{{ '%.3f' | format(rule.lift | default(0)) }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
        {% endif %}
    </div>
    {% endif %}

    {% if mining_summary %}
    <div class="section" style="background: #fff3bf; padding: 20px; border-radius: 8px; border-left: 4px solid #fab005;">
        <h3 style="margin-top: 0;">📊 挖掘统计摘要</h3>
        <ul style="padding-left: 20px; margin: 0;">
            {% if mining_summary.total_rules is defined %}<li>挖掘得到关联规则 <strong>{{ mining_summary.total_rules }}</strong> 条</li>{% endif %}
            {% if mining_summary.total_records is defined %}<li>有效样本记录 <strong>{{ mining_summary.total_records }}</strong> 条</li>{% endif %}
            {% if mining_summary.significant_rules is defined %}<li>显著性规则 (P &lt; {{ mining_summary.p_value_threshold | default(0.05) }}): <strong>{{ mining_summary.significant_rules }}</strong> 条</li>{% endif %}
            {% if mining_summary.test_method is defined %}<li>统计检验方法: {{ mining_summary.test_method }}</li>{% endif %}
        </ul>
    </div>
    {% endif %}

    {% if charts %}
    <div class="section">
        <h2>📈 风控可视化分析</h2>
        {% for chart in charts %}
        <div class="chart">
            <h4 style="margin-top: 0; color: #444;">{{ chart.title }}</h4>
            {{ chart.html|safe }}
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="section">
        <h2>📋 明细数据表</h2>
        {% for table in tables %}
        <div class="table-container">
            <h3>{{ table.title }}</h3>
            {{ table.html|safe }}
        </div>
        {% endfor %}
    </div>

    {% if conclusions %}
    <div class="section" style="background: #fff; padding: 20px; border-radius: 8px; border-left: 4px solid #c0392b; border: 1px solid #f5c6cb;">
        <h2 style="margin-top: 0;">✅ 关键结论</h2>
        <ul style="padding-left: 20px; margin: 0;">
        {% for c in conclusions %}
            <li>{{ c }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}

    <div class="section recommendations">
        <h2>🛡️ 风控策略建议</h2>
        <ul style="padding-left: 20px; margin: 0;">
        {% for recommendation in recommendations %}
            <li>{{ recommendation }}</li>
        {% endfor %}
        </ul>
    </div>

    <div class="footer">
        <p>本报告由 <strong>BivaStat-Miner 双变量关联挖掘与非参数统计分析平台</strong> 提供动力</p>
        <p>引擎支持：DeepSeek-V3.2 Engine via HUAWEI CLOUD MaaS | 报告版本: {{ version }}</p>
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
        body { font-family: 'Inter', system-ui, -apple-system, sans-serif; margin: 40px; line-height: 1.6; color: #333; }
        .header { text-align: center; border-bottom: 3px solid #28a745; padding-bottom: 30px; margin-bottom: 30px; background: linear-gradient(135deg, #f0faf0 0%, #fff 100%); padding: 30px; border-radius: 12px 12px 0 0; }
        .header h1 { color: #1a1a1a; margin-bottom: 4px; }
        .header .subtitle { color: #28a745; font-weight: 600; font-size: 14px; letter-spacing: 2px; text-transform: uppercase; }
        .section { margin: 40px 0; }
        .executive-summary { background-color: #fcfcfc; padding: 25px; border: 1px solid #eee; border-radius: 8px; }
        .chart { margin: 30px 0; padding: 20px; border: 1px solid #f0f0f0; border-radius: 8px; text-align: center; }
        .table-container { margin: 25px 0; overflow-x: auto; }
        .recommendations { background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%); padding: 25px; border-radius: 8px; border-left: 4px solid #28a745; }
        .footer { text-align: center; margin-top: 60px; font-size: 13px; color: #888; border-top: 1px solid #eee; padding-top: 20px; }
        table { border-collapse: collapse; width: 100%; margin: 15px 0; }
        th, td { border: 1px solid #eee; padding: 12px; text-align: left; }
        th { background-color: #f8f9fa; font-weight: 600; }
        h1, h2, h3 { color: #1a1a1a; }
    </style>
    """ + AI_STYLE + """
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <div class="subtitle">📊 市场趋势分析报告</div>
        <div style="color: #666; font-size: 14px; margin-top: 8px;">
            生成时间: {{ generated_at }} | 报告编者: {{ author }}
        </div>
    </div>

    {% if ai_executive_summary_html %}
    <div class="section ai-smart-analysis">
        <h2>智能市场洞察</h2>
        <div class="ai-content">{{ ai_executive_summary_html|safe }}</div>
    </div>
    {% endif %}

    {% if ai_analysis_html %}
    <div class="section ai-smart-analysis">
        <h2>AI 深度市场解读</h2>
        <div class="ai-content">{{ ai_analysis_html|safe }}</div>
    </div>
    {% endif %}

    <div class="section executive-summary">
        <h2>📊 市场数据概况</h2>
        <div style="display: flex; gap: 30px; flex-wrap: wrap; margin-bottom: 20px;">
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 130px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">数据规模</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #1864ab;">{{ data_info.shape[0] if data_info.shape else 0 }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 130px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">分析维度</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #1864ab;">{{ data_info.shape[1] if data_info.shape else 0 }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 130px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">数据质量</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #087f5b;">{{ executive_summary.data_quality_score }}/100</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 130px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">数值指标</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #1864ab;">{{ data_info.numeric_columns | length if data_info.numeric_columns else 0 }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 130px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">类别标签</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #5f3dc4;">{{ data_info.categorical_columns | length if data_info.categorical_columns else 0 }}</p>
            </div>
        </div>

        {% if data_info.missing_total is defined %}
        <div style="background: #f1f3f5; padding: 12px 16px; border-radius: 6px; margin-bottom: 15px; font-size: 13px;">
            缺失值总计: <strong>{{ data_info.missing_total }}</strong> | 重复行: <strong>{{ data_info.duplicate_rows | default(0) }}</strong>
        </div>
        {% endif %}

        <h3 style="margin-top: 25px;">核心市场发现</h3>
        <ul style="padding-left: 20px;">
        {% for finding in executive_summary.key_findings %}
            <li>{{ finding }}</li>
        {% endfor %}
        {% if not executive_summary.key_findings %}
            <li>暂未发现显著市场关联信号，建议扩大样本量或调整参数</li>
        {% endif %}
        </ul>
    </div>

    {% if rules_summary %}
    <div class="section" style="background: #f0faf0; padding: 25px; border-radius: 8px; border: 1px solid #c3e6cb;">
        <h2>⛓️ 市场关联规则概览</h2>
        <div style="display: flex; gap: 30px; flex-wrap: wrap; margin-bottom: 20px;">
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 140px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">规则总数</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #28a745;">{{ rules_summary.total }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 140px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">高置信度规则 (&gt;0.8)</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #2b8a3e;">{{ rules_summary.high_confidence }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 140px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">平均提升度</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #e67700;">{{ rules_summary.avg_lift }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 140px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">平均置信度</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #5f3dc4;">{{ rules_summary.avg_confidence }}</p>
            </div>
        </div>

        {% if rules_summary.top_rules %}
        <h3>Top 5 高价值关联规则</h3>
        <table>
            <thead><tr><th>前件</th><th>后件</th><th>支持度</th><th>置信度</th><th>提升度</th></tr></thead>
            <tbody>
            {% for rule in rules_summary.top_rules %}
                <tr>
                    <td>{{ rule.antecedents }}</td>
                    <td>{{ rule.consequents }}</td>
                    <td>{{ '%.4f' | format(rule.support | default(0)) }}</td>
                    <td>{{ '%.4f' | format(rule.confidence | default(0)) }}</td>
                    <td style="font-weight: bold; color: {% if rule.lift|default(0) > 2 %}#28a745{% elif rule.lift|default(0) > 1.5 %}#e67700{% else %}#333{% endif %};">{{ '%.3f' | format(rule.lift | default(0)) }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
        {% endif %}
    </div>
    {% endif %}

    {% if mining_summary %}
    <div class="section" style="background: #fff3bf; padding: 20px; border-radius: 8px; border-left: 4px solid #fab005;">
        <h3 style="margin-top: 0;">📊 挖掘统计摘要</h3>
        <ul style="padding-left: 20px; margin: 0;">
            {% if mining_summary.total_rules is defined %}<li>挖掘得到关联规则 <strong>{{ mining_summary.total_rules }}</strong> 条</li>{% endif %}
            {% if mining_summary.total_records is defined %}<li>有效数据记录 <strong>{{ mining_summary.total_records }}</strong> 条</li>{% endif %}
            {% if mining_summary.significant_rules is defined %}<li>显著性规则 (P &lt; {{ mining_summary.p_value_threshold | default(0.05) }}): <strong>{{ mining_summary.significant_rules }}</strong> 条</li>{% endif %}
            {% if mining_summary.test_method is defined %}<li>统计检验方法: {{ mining_summary.test_method }}</li>{% endif %}
        </ul>
    </div>
    {% endif %}

    {% if charts %}
    <div class="section">
        <h2>📈 市场关联可视化</h2>
        {% for chart in charts %}
        <div class="chart">
            <h4 style="margin-top: 0; color: #444;">{{ chart.title }}</h4>
            {{ chart.html|safe }}
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="section">
        <h2>📋 明细分析结果</h2>
        {% for table in tables %}
        <div class="table-container">
            <h3>{{ table.title }}</h3>
            {{ table.html|safe }}
        </div>
        {% endfor %}
    </div>

    {% if conclusions %}
    <div class="section" style="background: #fff; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745; border: 1px solid #c3e6cb;">
        <h2 style="margin-top: 0;">✅ 关键结论</h2>
        <ul style="padding-left: 20px; margin: 0;">
        {% for c in conclusions %}
            <li>{{ c }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}

    <div class="section recommendations">
        <h2>💡 市场策略建议</h2>
        <ul style="padding-left: 20px; margin: 0;">
        {% for recommendation in recommendations %}
            <li>{{ recommendation }}</li>
        {% endfor %}
        </ul>
    </div>

    <div class="footer">
        <p>本报告由 <strong>BivaStat-Miner 双变量关联挖掘与非参数统计分析平台</strong> 提供动力</p>
        <p>引擎支持：DeepSeek-V3.2 Engine via HUAWEI CLOUD MaaS | 报告版本: {{ version }}</p>
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
        body { font-family: 'Inter', system-ui, -apple-system, sans-serif; margin: 40px; line-height: 1.6; color: #333; }
        .header { text-align: center; border-bottom: 1px solid #eee; padding-bottom: 30px; margin-bottom: 30px; }
        .section { margin: 40px 0; }
        .executive-summary { background-color: #fcfcfc; padding: 25px; border: 1px solid #eee; border-radius: 8px; }
        .chart { margin: 30px 0; padding: 20px; border: 1px solid #f0f0f0; border-radius: 8px; text-align: center; }
        .table-container { margin: 25px 0; overflow-x: auto; }
        .recommendations { background-color: #fff9db; padding: 25px; border-radius: 8px; border-left: 4px solid #fab005; }
        .footer { text-align: center; margin-top: 60px; font-size: 13px; color: #888; border-top: 1px solid #eee; padding-top: 20px; }
        table { border-collapse: collapse; width: 100%; margin: 15px 0; }
        th, td { border: 1px solid #eee; padding: 12px; text-align: left; }
        th { background-color: #f8f9fa; font-weight: 600; }
        h1, h2, h3 { color: #1a1a1a; }
    </style>
    """ + AI_STYLE + """
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <div style="color: #666; font-size: 14px;">
            生成时间: {{ generated_at }} | 分析方: {{ author }}
        </div>
    </div>
    
    <!-- AI 智能解读区块 -->
    {% if ai_executive_summary_html %}
    <div class="section ai-smart-analysis">
        <h2>智能分析摘要</h2>
        <div class="ai-content">
            {{ ai_executive_summary_html|safe }}
        </div>
    </div>
    {% endif %}

    {% if ai_analysis_html %}
    <div class="section ai-smart-analysis">
        <h2>AI 深度解读存档</h2>
        <div class="ai-content">
            {{ ai_analysis_html|safe }}
        </div>
    </div>
    {% endif %}

    <div class="section executive-summary">
        <h2>📊 数据资产概况</h2>
        <div style="display: flex; gap: 40px; flex-wrap: wrap; margin-bottom: 20px;">
            <div>
                <p><strong>记录规模</strong></p>
                <p style="font-size: 24px; font-weight: bold; margin: 0;">{{ data_info.shape[0] if data_info.shape else 0 }} 条</p>
            </div>
            <div>
                <p><strong>特征维度</strong></p>
                <p style="font-size: 24px; font-weight: bold; margin: 0;">{{ data_info.shape[1] if data_info.shape else 0 }} 个</p>
            </div>
            <div>
                <p><strong>数据质量评分</strong></p>
                <p style="font-size: 24px; font-weight: bold; margin: 0; color: #087f5b;">{{ executive_summary.data_quality_score }}/100</p>
            </div>
            <div>
                <p><strong>数值变量</strong></p>
                <p style="font-size: 24px; font-weight: bold; margin: 0; color: #1864ab;">{{ data_info.numeric_columns | length if data_info.numeric_columns else 0 }} 个</p>
            </div>
            <div>
                <p><strong>分类变量</strong></p>
                <p style="font-size: 24px; font-weight: bold; margin: 0; color: #5f3dc4;">{{ data_info.categorical_columns | length if data_info.categorical_columns else 0 }} 个</p>
            </div>
        </div>

        {% if data_info.missing_total is defined %}
        <div style="background: #f1f3f5; padding: 12px 16px; border-radius: 6px; margin-bottom: 15px; font-size: 13px;">
            缺失值总计: <strong>{{ data_info.missing_total }}</strong> 个单元格 | 
            重复行: <strong>{{ data_info.duplicate_rows | default(0) }}</strong> 行
        </div>
        {% endif %}
        
        <h3 style="margin-top: 25px;">核心发现</h3>
        <ul style="padding-left: 20px;">
        {% for finding in executive_summary.key_findings %}
            <li>{{ finding }}</li>
        {% endfor %}
        {% if not executive_summary.key_findings %}
            <li>暂无显著统计发现，建议调整挖掘参数后重新分析</li>
        {% endif %}
        </ul>
    </div>

    <!-- 关联规则挖掘概览 -->
    {% if rules_summary %}
    <div class="section" style="background: #f8f9fa; padding: 25px; border-radius: 8px; border: 1px solid #e9ecef;">
        <h2>⛓️ 关联规则挖掘概览</h2>
        <div style="display: flex; gap: 30px; flex-wrap: wrap; margin-bottom: 20px;">
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 140px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">规则总数</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #1864ab;">{{ rules_summary.total }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 140px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">高置信度规则 (&gt;0.8)</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #2b8a3e;">{{ rules_summary.high_confidence }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 140px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">平均提升度</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #e67700;">{{ rules_summary.avg_lift }}</p>
            </div>
            <div style="background: white; padding: 16px 24px; border-radius: 8px; border: 1px solid #dee2e6; min-width: 140px;">
                <p style="font-size: 12px; color: #868e96; margin: 0;">平均置信度</p>
                <p style="font-size: 28px; font-weight: bold; margin: 4px 0 0; color: #5f3dc4;">{{ rules_summary.avg_confidence }}</p>
            </div>
        </div>

        {% if rules_summary.top_rules %}
        <h3>Top 5 最强关联规则 (按提升度排序)</h3>
        <table>
            <thead>
                <tr>
                    <th>前件 (Antecedents)</th>
                    <th>后件 (Consequents)</th>
                    <th>支持度</th>
                    <th>置信度</th>
                    <th>提升度</th>
                </tr>
            </thead>
            <tbody>
            {% for rule in rules_summary.top_rules %}
                <tr>
                    <td>{{ rule.antecedents }}</td>
                    <td>{{ rule.consequents }}</td>
                    <td>{{ '%.4f' | format(rule.support | default(0)) }}</td>
                    <td>{{ '%.4f' | format(rule.confidence | default(0)) }}</td>
                    <td style="font-weight: bold; color: {% if rule.lift|default(0) > 2 %}#2b8a3e{% elif rule.lift|default(0) > 1.5 %}#e67700{% else %}#333{% endif %};">{{ '%.3f' | format(rule.lift | default(0)) }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
        {% endif %}
    </div>
    {% endif %}

    <!-- 挖掘统计摘要 -->
    {% if mining_summary %}
    <div class="section" style="background: #fff3bf; padding: 20px; border-radius: 8px; border-left: 4px solid #fab005;">
        <h3 style="margin-top: 0;">📊 挖掘统计摘要</h3>
        <ul style="padding-left: 20px; margin: 0;">
            {% if mining_summary.total_rules is defined %}<li>挖掘得到关联规则 <strong>{{ mining_summary.total_rules }}</strong> 条</li>{% endif %}
            {% if mining_summary.total_records is defined %}<li>有效数据记录 <strong>{{ mining_summary.total_records }}</strong> 条</li>{% endif %}
            {% if mining_summary.significant_rules is defined %}<li>显著性规则 (P &lt; {{ mining_summary.p_value_threshold | default(0.05) }}): <strong>{{ mining_summary.significant_rules }}</strong> 条</li>{% endif %}
            {% if mining_summary.test_method is defined %}<li>统计检验方法: {{ mining_summary.test_method }}</li>{% endif %}
            {% if mining_summary.readiness_score is defined %}<li>数据挖掘适配度: {{ mining_summary.readiness_score }} 分 ({{ mining_summary.readiness_level | default('N/A') }})</li>{% endif %}
        </ul>
    </div>
    {% endif %}
    
    {% if charts %}
    <div class="section">
        <h2>📈 可视化透视</h2>
        {% for chart in charts %}
        <div class="chart">
            <h4 style="margin-top: 0; color: #444;">{{ chart.title }}</h4>
            {{ chart.html|safe }}
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="section">
        <h2>📋 明细分析结果</h2>
        {% for table in tables %}
        <div class="table-container">
            <h3>{{ table.title }}</h3>
            {{ table.html|safe }}
        </div>
        {% endfor %}
    </div>
    
    {% if conclusions %}
    <div class="section" style="background: #fff; padding: 20px; border-radius: 8px; border-left: 4px solid #2383e2; border: 1px solid #e9eef5;">
        <h2 style="margin-top: 0;">✅ 关键结论</h2>
        <ul style="padding-left: 20px; margin: 0;">
        {% for c in conclusions %}
            <li>{{ c }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}

    <div class="section recommendations">
        <h2>💡 业务改进建议</h2>
        <ul style="padding-left: 20px; margin: 0;">
        {% for rec in recommendations %}
            <li>{{ rec }}</li>
        {% endfor %}
        </ul>
    </div>
    
    <div class="footer">
        <p>本报告由 <strong>BivaStat-Miner 双变量关联挖掘与非参数统计分析平台</strong> 提供动力</p>
        <p>引擎支持：DeepSeek-V3.2 Engine via HUAWEI CLOUD MaaS | 报告版本: {{ version }}</p>
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
def generate_template(data: Dict[str, Any]) -> str:
    """生成报告模板的函数接口（生产环境版）"""
    include_ai_summary = bool(data.get('use_ai_summary') or data.get('include_ai_summary'))
    data['include_ai_summary'] = include_ai_summary
    # 确保只有在报告生成开关明确开启时，才渲染 AI 相关 HTML
    if include_ai_summary:
        ai_raw = data.get('ai_executive_summary')
        if ai_raw:
            data['ai_executive_summary_html'] = markdown.markdown(
                ai_raw,
                extensions=['tables', 'fenced_code', 'nl2br']
            )
        ai_analysis_raw = data.get('ai_analysis')
        if ai_analysis_raw:
            data['ai_analysis_html'] = markdown.markdown(
                ai_analysis_raw,
                extensions=['tables', 'fenced_code', 'nl2br']
            )
    else:
        data.pop('ai_executive_summary', None)
        data.pop('ai_analysis', None)
        data.pop('ai_executive_summary_html', None)
        data.pop('ai_analysis_html', None)
    
    # 获取数据基本信息
    data_info = data.get('data_info', {})
    template_type = data.get('templateType') or data.get('template_type') or 'general_analysis'
    template_mapping = {
        'basic': 'general_analysis',
        'general_analysis': 'general_analysis',
        'financial_risk': 'financial_risk',
        'medical_research': 'general_analysis',
        'market_analysis': 'market_analysis'
    }
    resolved_template = template_mapping.get(template_type, 'general_analysis')
    
    # 调用增强服务的综合报告生成逻辑
    return enhanced_report_service.generate_comprehensive_report(
        data_info=data_info,
        analysis_results=data,
        template_type=resolved_template,
        config={
            'title': data.get('title', '数据分析报告'),
            'author': data.get('author', 'BivaStat AI 助手'),
            'template_type': resolved_template,
            'include_visuals': bool(data.get('include_visuals', True))
        }
    )

def save_report(html_content, filename=None, format_type='html'):
    """保存报告的函数接口"""
    return enhanced_report_service.save_report(html_content, filename, format_type)