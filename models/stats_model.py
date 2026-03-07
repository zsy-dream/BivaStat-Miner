import pandas as pd
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)


def perform_test(df: pd.DataFrame, test_type: str = 'chi2'):
    """
    执行统计检验
    """
    result = {
        'test_name': test_type,
        'statistic': 0.0,
        'p_value': 1.0,
        'conclusion': '无法执行检验 (数据不足或类型不符)'
    }

    try:
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        if len(numeric_cols) >= 2:
            valid_data = df[[numeric_cols[0], numeric_cols[1]]].dropna()
            c1 = valid_data[numeric_cols[0]]
            c2 = valid_data[numeric_cols[1]]

            if test_type == 'chi2':
                contingency = pd.crosstab(c1 > c1.mean(), c2 > c2.mean())
                if contingency.size > 0:
                    stat, p, _, _ = stats.chi2_contingency(contingency)
                    result = {
                        'test_name': 'Chi-Square Test',
                        'statistic': round(stat, 4),
                        'p_value': round(p, 4),
                        'conclusion': '显著相关' if p < 0.05 else '无显著相关'
                    }

    except Exception as e:
        logger.warning(f"Stats Error: {e}")

    return result


def calculate_ci(df: pd.DataFrame, confidence: float = 0.95):
    """
    计算置信区间
    """
    ci_results = {}
    try:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            data = df[col].dropna()
            if len(data) > 1:
                mean = np.mean(data)
                sem = stats.sem(data)
                interval = stats.t.interval(confidence, len(data) - 1, loc=mean, scale=sem)
                ci_results[col] = {
                    'mean': round(mean, 2),
                    'lower': round(interval[0], 2),
                    'upper': round(interval[1], 2)
                }
    except Exception as e:
        logger.warning(f"置信区间计算失败: {e}")

    return ci_results
