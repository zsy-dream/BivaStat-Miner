import pandas as pd
from models.rule_model import RuleModel
from scipy import stats

rule_model = RuleModel()


class AlgorithmService:
    """算法服务类"""
    
    def __init__(self):
        self.rule_model = rule_model
    
    def mine_association(self, df: pd.DataFrame, params: dict) -> list:
        """挖掘关联规则的服务层封装"""
        transactions = df.apply(lambda x: list(x.dropna().astype(str)), axis=1).tolist()
        
        rules = self.rule_model.generate_rules(
            transactions,
            min_support=float(params.get('min_support', 0.1)),
            min_confidence=float(params.get('min_confidence', 0.5)),
            min_lift=float(params.get('min_lift', 1.0)),
            max_len=int(params.get('max_len', 5))
        )
        
        return rules
    
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
