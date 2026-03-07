# -*- coding: utf-8 -*-
"""算法模块综合测试脚本"""

import sys
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

# ============================================================
# 1. RuleModel 测试
# ============================================================
print("\n========== 1. RuleModel 测试 ==========")
try:
    from models.rule_model import RuleModel
    rm = RuleModel()
    report("RuleModel 导入 & 实例化", True)
except Exception as e:
    report("RuleModel 导入 & 实例化", False, str(e))
    traceback.print_exc()

# 简单交易数据
transactions = [
    ["面包", "牛奶"],
    ["面包", "尿布", "啤酒", "鸡蛋"],
    ["牛奶", "尿布", "啤酒", "可乐"],
    ["面包", "牛奶", "尿布", "啤酒"],
    ["面包", "牛奶", "尿布", "可乐"],
    ["面包", "牛奶", "啤酒"],
    ["面包", "尿布", "啤酒"],
    ["牛奶", "尿布", "啤酒"],
    ["面包", "牛奶", "尿布"],
    ["面包", "牛奶", "可乐"],
]

try:
    rules = rm.generate_rules(transactions, min_support=0.2, min_confidence=0.4, min_lift=1.0, max_len=3)
    report("generate_rules 运行", True, f"生成 {len(rules)} 条规则")

    if rules:
        r = rules[0]
        keys_ok = all(k in r for k in ["antecedents", "consequents", "support", "confidence", "lift"])
        report("规则字段完整性", keys_ok, f"首条规则字段: {list(r.keys())}")
    else:
        report("规则字段完整性", False, "未生成任何规则")
except Exception as e:
    report("generate_rules 运行", False, str(e))
    traceback.print_exc()

try:
    filtered = rm.filter_rules(rules, min_support=0.3)
    report("filter_rules", True, f"过滤后 {len(filtered)} 条")
except Exception as e:
    report("filter_rules", False, str(e))

try:
    sorted_r = rm.sort_rules(rules, sort_by="lift")
    lifts = [r["lift"] for r in sorted_r]
    is_desc = all(lifts[i] >= lifts[i+1] for i in range(len(lifts)-1))
    report("sort_rules (lift 降序)", is_desc, f"前3 lift: {[round(l,2) for l in lifts[:3]]}")
except Exception as e:
    report("sort_rules", False, str(e))

# ============================================================
# 2. AlgorithmService 测试
# ============================================================
print("\n========== 2. AlgorithmService 测试 ==========")
try:
    from services.algorithm_service import AlgorithmService
    algo = AlgorithmService()
    report("AlgorithmService 导入 & 实例化", True)
except Exception as e:
    report("AlgorithmService 导入 & 实例化", False, str(e))
    traceback.print_exc()

# 2a. 关联规则挖掘（含诊断）
try:
    params = {"min_support": 0.05, "min_confidence": 0.3, "min_lift": 1.0}
    result = algo.mine_association_with_diagnostics(df_test, params)
    ok = "association_rules" in result and "summary" in result and "mining_diagnostics" in result
    n_rules = len(result.get("association_rules", []))
    report("mine_association_with_diagnostics", ok, f"规则数={n_rules}, readiness={result['summary'].get('readiness_level')}")
except Exception as e:
    report("mine_association_with_diagnostics", False, str(e))
    traceback.print_exc()

# 2b. 适配度评估
try:
    diag = algo.assess_mining_suitability(df_test, params)
    ok = "readiness_score" in diag and "readiness_level" in diag
    report("assess_mining_suitability", ok,
           f"score={diag.get('readiness_score')}, level={diag.get('readiness_level')}, "
           f"selected_cols={len(diag.get('selected_columns', []))}")
except Exception as e:
    report("assess_mining_suitability", False, str(e))

# 2c. 空数据处理
try:
    empty_df = pd.DataFrame()
    result_empty = algo.mine_association_with_diagnostics(empty_df, params)
    ok = result_empty["summary"]["total_rules"] == 0
    report("空数据边界处理", ok)
except Exception as e:
    report("空数据边界处理", False, str(e))

# 2d. 非参数检验 (Mann-Whitney U)
try:
    np_params = {"test_method": "mannwhitney", "alpha": 0.05, "var1": "age", "var2": "income"}
    np_result = algo.nonparametric_test(df_test, np_params)
    ok = "p_value" in np_result and "statistic" in np_result
    report("nonparametric_test (Mann-Whitney)", ok,
           f"stat={np_result.get('statistic'):.2f}, p={np_result.get('p_value'):.4f}")
except Exception as e:
    report("nonparametric_test (Mann-Whitney)", False, str(e))

# 2e. 非参数检验 (卡方)
try:
    chi_params = {"test_method": "chi2", "alpha": 0.05, "var1": "gender", "var2": "level"}
    chi_result = algo.nonparametric_test(df_test, chi_params)
    ok = "p_value" in chi_result and "statistic" in chi_result
    report("nonparametric_test (Chi-Square)", ok,
           f"stat={chi_result.get('statistic'):.2f}, p={chi_result.get('p_value'):.4f}")
except Exception as e:
    report("nonparametric_test (Chi-Square)", False, str(e))

# 2f. 非参数检验 (KS)
try:
    ks_params = {"test_method": "ks", "alpha": 0.05, "var1": "age", "var2": "score"}
    ks_result = algo.nonparametric_test(df_test, ks_params)
    ok = "p_value" in ks_result and "statistic" in ks_result
    report("nonparametric_test (KS)", ok,
           f"stat={ks_result.get('statistic'):.2f}, p={ks_result.get('p_value'):.4f}")
except Exception as e:
    report("nonparametric_test (KS)", False, str(e))

# 2g. 自动检验方法选择
try:
    auto_params = {"test_method": "auto", "alpha": 0.05, "var1": "gender", "var2": "city"}
    auto_result = algo.nonparametric_test(df_test, auto_params)
    ok = auto_result.get("test_method") == "chi2"
    report("nonparametric_test (auto -> chi2)", ok, f"method={auto_result.get('test_method')}")
except Exception as e:
    report("nonparametric_test (auto)", False, str(e))

# ============================================================
# 3. StatisticalTestService 测试
# ============================================================
print("\n========== 3. StatisticalTestService 测试 ==========")
try:
    from services.statistical_test_service import StatisticalTestService
    sts = StatisticalTestService()
    report("StatisticalTestService 导入 & 实例化", True)
except Exception as e:
    report("StatisticalTestService 导入 & 实例化", False, str(e))
    traceback.print_exc()

# 3a. 综合检验
try:
    st_result = sts.perform_statistical_tests(
        df_test,
        target_col="gender",
        feature_cols=["age", "income", "score"],
        test_methods=["mann_whitney", "chi2", "spearman"],
        p_value_threshold=0.05
    )
    ok = "tests" in st_result and "summary" in st_result
    n_tests = st_result["summary"]["total_tests"]
    n_sig = st_result["summary"]["significant_tests"]
    report("perform_statistical_tests (综合)", ok,
           f"总检验数={n_tests}, 显著={n_sig}")
except Exception as e:
    report("perform_statistical_tests (综合)", False, str(e))
    traceback.print_exc()

# 3b. Kruskal-Wallis
try:
    kw_result = sts.perform_statistical_tests(
        df_test,
        target_col="city",
        feature_cols=["age", "income", "score"],
        test_methods=["kruskal_wallis"],
        p_value_threshold=0.05
    )
    ok = len(kw_result.get("tests", [])) > 0
    report("Kruskal-Wallis 检验", ok, f"结果数={len(kw_result.get('tests', []))}")
except Exception as e:
    report("Kruskal-Wallis 检验", False, str(e))

# 3c. Spearman 相关
try:
    sp_result = sts.perform_statistical_tests(
        df_test,
        target_col="gender",
        feature_cols=["age", "income", "score"],
        test_methods=["spearman"],
        p_value_threshold=0.05
    )
    ok = len(sp_result.get("tests", [])) > 0
    report("Spearman 相关", ok, f"配对数={len(sp_result.get('tests', []))}")
except Exception as e:
    report("Spearman 相关", False, str(e))

# 3d. 相关性矩阵
try:
    corr = st_result.get("correlation_matrix")
    ok = corr is not None and "columns" in corr and "values" in corr
    report("相关性矩阵计算", ok, f"维度={corr.get('shape') if corr else 'N/A'}")
except Exception as e:
    report("相关性矩阵计算", False, str(e))

# 3e. 空数据处理
try:
    empty_result = sts.perform_statistical_tests(pd.DataFrame())
    ok = "error" in empty_result
    report("StatisticalTestService 空数据处理", ok)
except Exception as e:
    report("StatisticalTestService 空数据处理", False, str(e))

# ============================================================
# 汇总
# ============================================================
print("\n" + "=" * 50)
print(f"总计: {PASS + FAIL} 项 | 通过: {PASS} | 失败: {FAIL}")
if FAIL == 0:
    print("全部通过!")
else:
    print(f"有 {FAIL} 项未通过，请检查上方输出。")
print("=" * 50)

sys.exit(0 if FAIL == 0 else 1)
