import pandas as pd
from models.rule_model import RuleModel
# 假设 stats_model 已存在或使用 scipy 替代
from scipy import stats

rule_model = RuleModel()


class AlgorithmService:
    """算法服务类"""
    
    def __init__(self):
        self.rule_model = rule_model
    
    def mine_association(self, df: pd.DataFrame, params: dict) -> list:
        """
        挖掘关联规则的服务层封装
        """
        # 将DataFrame转换为列表格式的事务数据
        transactions = df.apply(lambda x: list(x.dropna().astype(str)), axis=1).tolist()

        # 调用模型层进行挖掘
        rules = self.rule_model.generate_rules(
            transactions,
            min_support=float(params.get('min_support', 0.1)),
            min_confidence=float(params.get('min_confidence', 0.5)),
            min_lift=float(params.get('min_lift', 1.0)),
            max_len=int(params.get('max_len', 5))
        )

        return rules

    def nonparametric_test(self, df: pd.DataFrame, params: dict) -> dict:
        """
        非参数统计检验的服务层封装
        """
        test_method = params.get('test_method', 'auto')
        alpha = float(params.get('alpha', 0.05))
        var1 = params.get('var1')
        var2 = params.get('var2')

        if var1 is None or var2 is None:
            return {'error': '需要指定两个变量名'}

        if var1 not in df.columns or var2 not in df.columns:
            return {'error': f'变量 {var1} 或 {var2} 不存在'}

        try:
            # 自动选择检验方法
            if test_method == 'auto':
                # 简单的自动选择逻辑
                if df[var1].dtype == 'object' or df[var2].dtype == 'object':
                    test_method = 'chi2'
                else:
                    test_method = 'mannwhitney'

            # 执行相应的检验
            if test_method == 'mannwhitney':
                stat, p_value = stats.mannwhitneyu(
                    df[var1].dropna(), 
                    df[var2].dropna(), 
                    alternative='two-sided'
                )
                test_name = 'Mann-Whitney U检验'
            elif test_method == 'chi2':
                # 创建列联表
                contingency_table = pd.crosstab(df[var1], df[var2])
                stat, p_value, dof, expected = stats.chi2_contingency(contingency_table)
                test_name = '卡方检验'
            elif test_method == 'ks':
                stat, p_value = stats.ks_2samp(
                    df[var1].dropna(), 
                    df[var2].dropna()
                )
                test_name = 'Kolmogorov-Smirnov检验'
            else:
                return {'error': f'不支持的检验方法: {test_method}'}

            results = {
                'test_name': test_name,
                'statistic': float(stat),
                'p_value': float(p_value),
                'alpha': alpha,
                'significant': p_value < alpha,
                'var1': var1,
                'var2': var2,
                'test_method': test_method
            }

        except Exception as e:
            results = {'error': str(e)}

        return results


# 创建实例
algorithm_service = AlgorithmService()


# 保持向后兼容的函数接口
def mine_association(df: pd.DataFrame, params: dict) -> list:
    """挖掘关联规则的函数接口"""
    return algorithm_service.mine_association(df, params)


def nonparametric_test(df: pd.DataFrame, params: dict) -> dict:
    """非参数统计检验的函数接口"""
    return algorithm_service.nonparametric_test(df, params)


def nonparametric_test(df: pd.DataFrame, test_type: str = 'chi2'):
    """
    执行非参数统计检验

    参数 test_type 取值（小写）约定：
    - 'mann-whitney'  : Mann-Whitney U 检验
    - 'wilcoxon'      : Wilcoxon 秩和/符号秩检验
    - 'kruskal-wallis': Kruskal-Wallis H 检验
    - 'ks'            : Kolmogorov-Smirnov 检验（两独立样本）
    - 'spearman'      : Spearman 等级相关
    - 'chi2' / 其他   : 卡方检验
    """
    results = {}

    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) < 2 and test_type in ('mann-whitney', 'wilcoxon', 'kruskal-wallis', 'ks', 'spearman'):
        return {'error': '进行该检验至少需要 2 个数值型变量'}

    # 统一去除 NaN，避免部分检验因缺失值报错
    col1, col2 = numeric_cols[0], numeric_cols[1] if len(numeric_cols) > 1 else (numeric_cols[0], numeric_cols[0])
    s1 = df[col1].dropna()
    s2 = df[col2].dropna()

    try:
        if test_type == 'mann-whitney':
            stat, p_value = stats.mannwhitneyu(s1, s2, alternative="two-sided")
            test_name = "Mann-Whitney U Test"
        elif test_type == 'wilcoxon':
            # 需要两组数据长度一致，截取对齐
            min_len = min(len(s1), len(s2))
            stat, p_value = stats.wilcoxon(s1.iloc[:min_len], s2.iloc[:min_len])
            test_name = "Wilcoxon Signed-Rank Test"
        elif test_type == 'kruskal-wallis':
            stat, p_value = stats.kruskal(s1, s2)
            test_name = "Kruskal-Wallis H Test"
        elif test_type == 'ks':
            # 两独立样本的 Kolmogorov-Smirnov 检验
            stat, p_value = stats.ks_2samp(s1, s2)
            test_name = "Kolmogorov-Smirnov Test"
        elif test_type == 'spearman':
            stat, p_value = stats.spearmanr(s1, s2, nan_policy='omit')
            test_name = "Spearman Rank Correlation"
        else:
            # 默认为卡方检验 (用于分类变量)
            contingency_table = pd.crosstab(df[df.columns[0]], df[df.columns[1]])
            stat, p_value, _, _ = stats.chi2_contingency(contingency_table)
            test_name = "Chi-Square Test"

        results = {
            'test_name': test_name,
            'statistic': float(stat),
            'p_value': float(p_value),
            'conclusion': 'Significant difference' if p_value < 0.05 else 'No significant difference'
        }
    except Exception as e:
        results = {'error': str(e)}

    return results
# 创建实例
algorithm_service = type('AlgorithmService', (), {})()