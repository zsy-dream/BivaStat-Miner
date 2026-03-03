import pandas as pd
from models.rule_model import RuleModel
from scipy import stats
import numpy as np

rule_model = RuleModel()


class AlgorithmService:
    """算法服务类"""
    
    def __init__(self):
        self.rule_model = rule_model
    
    def mine_association(self, df: pd.DataFrame, params: dict) -> list:
        """挖掘关联规则的服务层封装"""
        transactions = self._build_transactions(df, params)
        
        rules = self.rule_model.generate_rules(
            transactions,
            min_support=float(params.get('min_support', 0.1)),
            min_confidence=float(params.get('min_confidence', 0.5)),
            min_lift=float(params.get('min_lift', 1.0)),
            max_len=int(params.get('max_len', 5))
        )
        
        return rules

    def _build_transactions(self, df: pd.DataFrame, params: dict) -> list[list[str]]:
        """
        将 DataFrame 转为交易数据（transactions）。

        关键优化：
        - 使用 “列名=取值/分箱” 作为 item，避免不同列相同数值被误判为同一 item
        - 数值列做分箱（默认 5 份），避免连续值导致 item 爆炸、Apriori 卡死
        - 过滤高基数分类列/限制参与挖掘的列数，避免组合爆炸
        """
        if df is None or getattr(df, "empty", True):
            return []

        max_bins = int(params.get("numeric_bins", 5) or 5)
        max_bins = max(2, min(max_bins, 20))
        max_unique_cat = int(params.get("max_unique_per_categorical", 50) or 50)
        max_unique_cat = max(5, min(max_unique_cat, 500))
        max_cols = int(params.get("max_columns_for_mining", 30) or 30)
        max_cols = max(5, min(max_cols, 200))

        selected = params.get("selected_columns")
        if isinstance(selected, list) and selected:
            cols = [c for c in selected if c in df.columns]
        else:
            # 默认优先：低基数分类列 + 可分箱数值列（限制列数，避免爆炸）
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            cat_cols = [c for c in df.columns if c not in num_cols]
            # 去掉极高基数分类列（例如 ID/时间戳）
            filtered_cat = [c for c in cat_cols if int(df[c].nunique(dropna=True)) <= max_unique_cat]
            cols = (filtered_cat + num_cols)[:max_cols]

        if not cols:
            return []

        work = df[cols].copy()

        # 预计算数值列分箱（向量化），减少每行处理成本
        num_cols = work.select_dtypes(include=[np.number]).columns.tolist()
        binned = {}
        for col in num_cols:
            s = work[col]
            # 全空/常数列跳过
            if s.dropna().nunique() <= 1:
                continue
            try:
                b = pd.qcut(s, q=max_bins, duplicates="drop")
            except Exception:
                try:
                    b = pd.cut(s, bins=max_bins)
                except Exception:
                    continue
            binned[col] = b.astype(str)

        # 组装 transactions
        transactions: list[list[str]] = []
        for _, row in work.iterrows():
            items: list[str] = []
            for col in cols:
                val = row.get(col)
                if pd.isna(val):
                    continue
                if col in binned:
                    bin_label = binned[col].iloc[row.name] if row.name in binned[col].index else None
                    if bin_label and bin_label != "nan":
                        items.append(f"{col}={bin_label}")
                else:
                    sval = str(val).strip()
                    if not sval:
                        continue
                    items.append(f"{col}={sval}")
            # 去重（同一行同一 item 只保留一次）
            if items:
                transactions.append(list(dict.fromkeys(items)))

        return transactions
    
    def nonparametric_test(self, df: pd.DataFrame, params: dict) -> dict:
        """非参数统计检验的服务层封装"""
        test_method = params.get('test_method', 'auto')
        alpha = float(params.get('alpha', 0.05))
        var1 = params.get('var1')
        var2 = params.get('var2')
        
        if var1 is None or var2 is None:
            return {'error': '需要指定两个变量名'}
        
        if var1 not in df.columns or var2 not in df.columns:
            return {'error': f'变量 {var1} 或 {var2} 不存在'}
        
        try:
            if test_method == 'auto':
                if df[var1].dtype == 'object' or df[var2].dtype == 'object':
                    test_method = 'chi2'
                else:
                    test_method = 'mannwhitney'
            
            if test_method == 'mannwhitney':
                stat, p_value = stats.mannwhitneyu(
                    df[var1].dropna(), 
                    df[var2].dropna(), 
                    alternative='two-sided'
                )
                test_name = 'Mann-Whitney U检验'
            elif test_method == 'chi2':
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
