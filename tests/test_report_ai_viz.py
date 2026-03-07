# -*- coding: utf-8 -*-
"""报告生成、AI 服务、可视化模块综合测试"""

import sys
import os
import traceback
import numpy as np
import pandas as pd

PASS = 0
FAIL = 0


def report(name, ok, detail=""):
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{tag}] {name}" + (f"  -- {detail}" if detail else ""))


# ============================================================
# 构造测试数据
# ============================================================
np.random.seed(42)
N = 200
df_test = pd.DataFrame({
    "gender":   np.random.choice(["男", "女"], N),
    "city":     np.random.choice(["北京", "上海", "广州", "深圳"], N),
    "age":      np.random.randint(18, 65, N).astype(float),
    "income":   np.random.normal(8000, 2000, N).round(2),
    "score":    np.random.uniform(50, 100, N).round(2),
    "level":    np.random.choice(["A", "B", "C"], N),
})

# 模拟关联规则结果
mock_rules = [
    {"antecedents": ["city=北京"], "consequents": ["level=A"], "support": 0.15, "confidence": 0.72, "lift": 2.1, "p_value": 0.03, "conviction": 1.8, "length": 2},
    {"antecedents": ["gender=女", "city=上海"], "consequents": ["level=B"], "support": 0.08, "confidence": 0.85, "lift": 1.9, "p_value": 0.01, "conviction": 2.5, "length": 3},
    {"antecedents": ["city=广州"], "consequents": ["gender=男"], "support": 0.12, "confidence": 0.60, "lift": 1.2, "p_value": 0.15, "conviction": 1.1, "length": 2},
    {"antecedents": ["level=C"], "consequents": ["city=深圳"], "support": 0.10, "confidence": 0.55, "lift": 1.05, "p_value": 0.45, "conviction": 0.9, "length": 2},
    {"antecedents": ["gender=男"], "consequents": ["level=A", "city=北京"], "support": 0.05, "confidence": 0.90, "lift": 3.5, "p_value": 0.005, "conviction": 4.0, "length": 3},
]

mock_analysis_results = {
    "association_rules": mock_rules,
    "summary": {
        "total_rules": len(mock_rules),
        "significant_rules": 3,
        "avg_confidence": 0.724,
        "avg_support": 0.10,
        "p_value_threshold": 0.05,
        "readiness_score": 85.0,
        "readiness_level": "good",
        "total_records": N,
    },
    "statistical_tests": {
        "tests": [
            {"test_name": "Mann-Whitney U检验", "feature": "age", "target": "gender", "p_value": 0.32, "effect_size": 0.05, "is_significant": False, "conclusion": "无显著差异", "effect_interpretation": "可忽略", "recommendation": "关联不显著"},
            {"test_name": "Kruskal-Wallis H检验", "feature": "income", "target": "city", "p_value": 0.004, "effect_size": 0.12, "is_significant": True, "conclusion": "多组间存在显著差异", "effect_interpretation": "中等效应", "recommendation": "重点关注"},
        ]
    }
}

mock_data_info = {
    "shape": [N, len(df_test.columns)],
    "columns": df_test.columns.tolist(),
    "numeric_columns": ["age", "income", "score"],
    "categorical_columns": ["gender", "city", "level"],
    "missing_total": 0,
    "duplicate_rows": 0,
    "quality_report": {
        "missing_values": {"total_missing": 0},
        "duplicates": {"duplicate_percentage": 0.0},
        "overall_score": 95.0
    }
}

# ============================================================
# 1. 可视化模块测试
# ============================================================
print("\n========== 1. VisualizationService 测试 ==========")
try:
    from services.visualization_service import VisualizationService
    viz = VisualizationService()
    report("VisualizationService 导入 & 实例化", True)
except Exception as e:
    report("VisualizationService 导入 & 实例化", False, str(e))
    traceback.print_exc()

# 1a. 相关性热力图
try:
    result = viz.create_correlation_heatmap(df_test)
    ok = result.get("chart_type") == "heatmap" and result.get("figure") is not None
    html = result["figure"].to_html(full_html=False, include_plotlyjs=False)
    report("相关性热力图", ok, f"HTML长度={len(html)}")
except Exception as e:
    report("相关性热力图", False, str(e))

# 1b. 散点图（含趋势线）
try:
    result = viz.create_scatter_plot(df_test, "age", "income", {"add_trendline": True, "show_regression_info": True})
    ok = result.get("chart_type") == "scatter" and result.get("regression_stats") is not None
    report("散点图+趋势线+回归信息", ok, f"R²={result['regression_stats']['r_squared']:.4f}")
except Exception as e:
    report("散点图+趋势线+回归信息", False, str(e))

# 1c. 分布图
try:
    result = viz.create_distribution_plot(df_test, "income")
    ok = result.get("chart_type") == "distribution" and "statistics" in result
    stats = result["statistics"]
    report("分布图", ok, f"mean={stats['mean']:.1f}, std={stats['std']:.1f}")
except Exception as e:
    report("分布图", False, str(e))

# 1d. 箱线图（分组）
try:
    result = viz.create_box_plot(df_test, "score", "gender")
    ok = result.get("chart_type") == "boxplot"
    report("分组箱线图", ok)
except Exception as e:
    report("分组箱线图", False, str(e))

# 1e. 柱状图（频数）
try:
    result = viz.create_bar_chart(df_test, "city")
    ok = result.get("chart_type") == "bar" and result.get("data_summary") is not None
    report("柱状图（频数）", ok, f"categories={result['data_summary']['total_categories']}")
except Exception as e:
    report("柱状图（频数）", False, str(e))

# 1f. 柱状图（聚合）
try:
    result = viz.create_bar_chart(df_test, "city", "income")
    ok = result.get("chart_type") == "bar"
    report("柱状图（分组均值）", ok)
except Exception as e:
    report("柱状图（分组均值）", False, str(e))

# 1g. 折线图
try:
    result = viz.create_line_plot(df_test.sort_values("age"), "age", "income", {"add_trendline": True, "trendline_window": 10})
    ok = result.get("chart_type") == "line"
    report("折线图+移动平均", ok)
except Exception as e:
    report("折线图+移动平均", False, str(e))

# 1h. 关联规则网络图
try:
    rules_df = pd.DataFrame(mock_rules)
    result = viz.create_association_rules_network(rules_df)
    ok = result.get("chart_type") == "network" and result.get("nodes_count", 0) > 0
    report("关联规则网络图", ok, f"nodes={result.get('nodes_count')}, edges={result.get('edges_count')}")
except Exception as e:
    report("关联规则网络图", False, str(e))

# 1i. 综合仪表板
try:
    result = viz.create_dashboard(df_test)
    ok = result.get("chart_type") == "dashboard"
    report("综合仪表板", ok, f"shape={result.get('summary_stats', {}).get('shape')}")
except Exception as e:
    report("综合仪表板", False, str(e))

# 1j. 非数值列散点图应报错
try:
    viz.create_scatter_plot(df_test, "gender", "city")
    report("散点图非数值列校验", False, "应该抛出异常")
except Exception as e:
    ok = "数值" in str(e)
    report("散点图非数值列校验", ok, f"正确拒绝: {str(e)[:30]}")

# ============================================================
# 2. AI 服务模块测试（离线逻辑，不调用 API）
# ============================================================
print("\n========== 2. AIService 测试（离线逻辑） ==========")
try:
    from services.ai_service import AIService
    ai = AIService()
    report("AIService 导入 & 实例化", True, f"available={ai.is_available()}")
except Exception as e:
    report("AIService 导入 & 实例化", False, str(e))
    traceback.print_exc()

# 2a. 规则标准化
try:
    normalized = ai._normalize_rules_for_prompt(mock_rules)
    ok = len(normalized) == len(mock_rules)
    top = normalized[0]
    ok = ok and "evidence_score" in top and top["evidence_score"] > 0
    report("规则标准化 (_normalize_rules_for_prompt)", ok, f"top evidence_score={top['evidence_score']:.2f}")
except Exception as e:
    report("规则标准化", False, str(e))

# 2b. 规则全景摘要
try:
    landscape = ai._summarize_rule_landscape(mock_rules)
    ok = "summary_lines" in landscape and "top_rule_lines" in landscape and "top_items" in landscape
    report("规则全景摘要 (_summarize_rule_landscape)", ok, f"top_items={len(landscape['top_items'])}")
except Exception as e:
    report("规则全景摘要", False, str(e))

# 2c. 统计检验摘要
try:
    stats_snap = ai._summarize_statistical_tests(mock_analysis_results["statistical_tests"])
    ok = len(stats_snap["tests"]) == 2 and len(stats_snap["top_test_lines"]) > 0
    report("统计检验摘要 (_summarize_statistical_tests)", ok, f"tests={len(stats_snap['tests'])}")
except Exception as e:
    report("统计检验摘要", False, str(e))

# 2d. 分析 Prompt 构建
try:
    messages = ai._build_analysis_prompt(mock_rules, mock_analysis_results["summary"], mock_analysis_results["statistical_tests"])
    ok = len(messages) == 2 and messages[0]["role"] == "system" and messages[1]["role"] == "user"
    prompt_len = len(messages[1]["content"])
    ok = ok and "高价值规则" in messages[1]["content"]
    report("分析Prompt构建 (_build_analysis_prompt)", ok, f"prompt长度={prompt_len}")
except Exception as e:
    report("分析Prompt构建", False, str(e))

# 2e. 报告摘要 Prompt 构建
try:
    messages = ai._build_report_summary_prompt(mock_data_info, mock_analysis_results)
    ok = len(messages) == 2 and "执行结论" in messages[0]["content"]
    report("报告摘要Prompt构建 (_build_report_summary_prompt)", ok)
except Exception as e:
    report("报告摘要Prompt构建", False, str(e))

# 2f. 缓存机制
try:
    fp = ai._fingerprint("test", {"a": 1})
    ai._set_cached(fp, "cached_content")
    cached = ai._get_cached(fp)
    ok = cached == "cached_content"
    report("缓存机制 (set/get)", ok)
except Exception as e:
    report("缓存机制", False, str(e))

# 2g. 空规则处理
try:
    landscape_empty = ai._summarize_rule_landscape([])
    ok = len(landscape_empty["top_rules"]) == 0 and landscape_empty["top_rule"] is None
    report("空规则处理", ok)
except Exception as e:
    report("空规则处理", False, str(e))

# 2h. 辅助函数
try:
    ok1 = ai._safe_float("3.14") == 3.14
    ok2 = ai._safe_float(None, 0.0) == 0.0
    ok3 = ai._format_number(0.123456, 3) == "0.123"
    ok4 = ai._format_number(None) == "N/A"
    ants, cons = ai._extract_rule_items({"antecedents": "A", "consequents": ["B", "C"]})
    ok5 = ants == ["A"] and cons == ["B", "C"]
    ok6 = ai._format_rule_side(["X", "Y"]) == "X ∧ Y"
    ok = ok1 and ok2 and ok3 and ok4 and ok5 and ok6
    report("辅助函数 (safe_float/format_number/extract/format)", ok)
except Exception as e:
    report("辅助函数", False, str(e))

# ============================================================
# 3. 报告生成模块测试
# ============================================================
print("\n========== 3. ReportService 测试 ==========")
try:
    from services.report_service import EnhancedReportService, generate_template, save_report
    rs = EnhancedReportService()
    report("EnhancedReportService 导入 & 实例化", True)
except Exception as e:
    report("EnhancedReportService 导入 & 实例化", False, str(e))
    traceback.print_exc()

# 3a. 执行摘要生成
try:
    exec_summary = rs._generate_executive_summary(mock_data_info, mock_analysis_results)
    ok = "data_overview" in exec_summary and exec_summary["data_overview"]["total_records"] == N
    report("执行摘要生成", ok, f"records={exec_summary['data_overview']['total_records']}")
except Exception as e:
    report("执行摘要生成", False, str(e))

# 3b. 建议生成
try:
    recs_fin = rs._generate_recommendations(mock_analysis_results, "financial_risk")
    recs_mkt = rs._generate_recommendations(mock_analysis_results, "market_analysis")
    recs_gen = rs._generate_recommendations(mock_analysis_results, "general_analysis")
    ok = len(recs_fin) > 0 and len(recs_mkt) > 0 and len(recs_gen) > 0
    report("建议生成（3种模板）", ok, f"financial={len(recs_fin)}, market={len(recs_mkt)}, general={len(recs_gen)}")
except Exception as e:
    report("建议生成", False, str(e))

# 3c. 规则 DataFrame 准备
try:
    rules_df = rs._prepare_rules_dataframe(mock_analysis_results)
    ok = not rules_df.empty and "antecedents_text" in rules_df.columns and "consequents_text" in rules_df.columns
    report("规则DataFrame准备", ok, f"shape={rules_df.shape}")
except Exception as e:
    report("规则DataFrame准备", False, str(e))

# 3d. 规则网络图（Sankey）
try:
    fig = rs._build_rule_network_figure(rules_df)
    ok = fig is not None
    report("规则网络图（Sankey）", ok)
except Exception as e:
    report("规则网络图（Sankey）", False, str(e))

# 3e. 报告图表生成
try:
    charts = rs._generate_report_charts(mock_analysis_results, {"include_visuals": True, "template_type": "general_analysis"})
    ok = len(charts) > 0
    types = [c["type"] for c in charts]
    report("报告图表生成", ok, f"图表数={len(charts)}, 类型={types}")
except Exception as e:
    report("报告图表生成", False, str(e))
    traceback.print_exc()

# 3f. 报告表格生成
try:
    tables = rs._generate_report_tables(mock_analysis_results)
    ok = len(tables) > 0
    table_types = [t["type"] for t in tables]
    report("报告表格生成", ok, f"表格数={len(tables)}, 类型={table_types}")
except Exception as e:
    report("报告表格生成", False, str(e))

# 3g. 完整报告生成（general_analysis）
try:
    html = rs.generate_comprehensive_report(
        data_info=mock_data_info,
        analysis_results=mock_analysis_results,
        template_type="general_analysis",
        config={"title": "测试报告", "author": "自动测试"}
    )
    ok = len(html) > 500 and "<html>" in html.lower() and "测试报告" in html
    report("完整报告 (general_analysis)", ok, f"HTML长度={len(html)}")
except Exception as e:
    report("完整报告 (general_analysis)", False, str(e))
    traceback.print_exc()

# 3h. 完整报告生成（financial_risk）
try:
    html_fin = rs.generate_comprehensive_report(
        data_info=mock_data_info,
        analysis_results=mock_analysis_results,
        template_type="financial_risk",
        config={"title": "金融风控报告"}
    )
    ok = "金融风控" in html_fin
    report("完整报告 (financial_risk)", ok, f"HTML长度={len(html_fin)}")
except Exception as e:
    report("完整报告 (financial_risk)", False, str(e))

# 3i. 完整报告生成（market_analysis）
try:
    html_mkt = rs.generate_comprehensive_report(
        data_info=mock_data_info,
        analysis_results=mock_analysis_results,
        template_type="market_analysis",
        config={"title": "市场分析报告"}
    )
    ok = "市场" in html_mkt
    report("完整报告 (market_analysis)", ok, f"HTML长度={len(html_mkt)}")
except Exception as e:
    report("完整报告 (market_analysis)", False, str(e))

# 3j. generate_template 函数接口
try:
    template_data = {
        **mock_analysis_results,
        "data_info": mock_data_info,
        "title": "函数接口测试",
        "templateType": "general_analysis"
    }
    html_fn = generate_template(template_data)
    ok = len(html_fn) > 500 and "函数接口测试" in html_fn
    report("generate_template 函数接口", ok, f"HTML长度={len(html_fn)}")
except Exception as e:
    report("generate_template 函数接口", False, str(e))

# 3k. 报告保存与清理
try:
    path = save_report(html, "test_report_cleanup.html")
    ok = os.path.exists(path)
    report("报告保存", ok, f"path={path}")
    # 清理
    if os.path.exists(path):
        os.remove(path)
except Exception as e:
    report("报告保存", False, str(e))

# 3l. 空规则报告
try:
    empty_results = {"association_rules": [], "summary": {"total_rules": 0}}
    html_empty = rs.generate_comprehensive_report(
        data_info=mock_data_info,
        analysis_results=empty_results,
        template_type="general_analysis",
        config={"title": "空结果报告"}
    )
    ok = "<html>" in html_empty.lower()
    report("空规则报告生成", ok, f"HTML长度={len(html_empty)}")
except Exception as e:
    report("空规则报告生成", False, str(e))

# 3m. AI摘要注入测试（模拟Markdown → HTML）
try:
    ai_data = {
        **mock_analysis_results,
        "data_info": mock_data_info,
        "title": "AI摘要测试",
        "templateType": "general_analysis",
        "use_ai_summary": True,
        "ai_executive_summary": "## 执行结论\n本次分析共发现 **5条** 关联规则。",
    }
    html_ai = generate_template(ai_data)
    ok = "执行结论" in html_ai and "5条" in html_ai
    report("AI摘要Markdown→HTML注入", ok)
except Exception as e:
    report("AI摘要Markdown→HTML注入", False, str(e))

# 3n. AI摘要与AI深度解读重复时只渲染一次
try:
    duplicate_ai_markdown = "## 执行结论\n同一段 AI 摘要内容。"
    duplicate_ai_data = {
        **mock_analysis_results,
        "data_info": mock_data_info,
        "title": "AI去重测试",
        "templateType": "general_analysis",
        "use_ai_summary": True,
        "ai_executive_summary": duplicate_ai_markdown,
        "ai_analysis": duplicate_ai_markdown,
    }
    html_duplicate_ai = generate_template(duplicate_ai_data)
    ok = html_duplicate_ai.count("同一段 AI 摘要内容。") == 1 and "AI 深度解读存档" not in html_duplicate_ai
    report("重复AI摘要去重", ok)
except Exception as e:
    report("重复AI摘要去重", False, str(e))

# ============================================================
# 汇总
# ============================================================
print("\n" + "=" * 55)
print(f"总计: {PASS + FAIL} 项 | 通过: {PASS} | 失败: {FAIL}")
if FAIL == 0:
    print("全部通过!")
else:
    print(f"有 {FAIL} 项未通过，请检查上方输出。")
print("=" * 55)

sys.exit(0 if FAIL == 0 else 1)
