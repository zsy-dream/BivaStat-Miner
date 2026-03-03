"""
增强的非参数统计检验服务
提供Mann-Whitney U、Kruskal-Wallis、Chi-Square、Kolmogorov-Smirnov等检验方法
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class StatisticalTestService:
    """非参数统计检验服务"""
    
    def __init__(self):
        self.test_methods = {
            'mann_whitney': self._mann_whitney_test,
            'kruskal_wallis': self._kruskal_wallis_test,
            'chi2': self._chi_square_test,
            'ks': self._kolmogorov_smirnov_test,
            'spearman': self._spearman_correlation,
            'wilcoxon': self._wilcoxon_signed_rank
        }
    
    def perform_statistical_tests(
        self,
        df: pd.DataFrame,
        target_col: Optional[str] = None,
        feature_cols: Optional[List[str]] = None,
        test_methods: List[str] = None,
        p_value_threshold: float = 0.05
    ) -> Dict[str, Any]:
        """
        执行综合统计检验
        
        Args:
            df: 数据框
            target_col: 目标变量列名
            feature_cols: 特征列名列表
            test_methods: 检验方法列表
            p_value_threshold: P值阈值
            
        Returns:
            统计检验结果字典
        """
        if df is None or df.empty:
            return {'error': '数据为空', 'tests': []}
        
        # 自动识别数值列和分类列
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # 如果未指定特征列，使用所有数值列
        if feature_cols is None:
            feature_cols = numeric_cols
        
        # 如果未指定目标列，使用第一个分类列或创建二元分组
        if target_col is None and categorical_cols:
            target_col = categorical_cols[0]
        
        if test_methods is None:
            test_methods = ['mann_whitney', 'chi2', 'spearman']
        
        results = {
            'summary': {
                'total_tests': 0,
                'significant_tests': 0,
                'p_value_threshold': p_value_threshold,
                'data_shape': df.shape
            },
            'tests': [],
            'correlation_matrix': None,
            'feature_importance': []
        }
        
        # 执行各种检验
        for method in test_methods:
            if method in self.test_methods:
                try:
                    test_result = self.test_methods[method](
                        df, target_col, feature_cols, p_value_threshold
                    )
                    if test_result:
                        results['tests'].extend(test_result if isinstance(test_result, list) else [test_result])
                except Exception as e:
                    logger.warning(f"检验方法 {method} 执行失败: {str(e)}")
                    continue
        
        # 计算相关性矩阵
        try:
            results['correlation_matrix'] = self._calculate_correlation_matrix(df, numeric_cols)
        except Exception as e:
            logger.warning(f"相关性矩阵计算失败: {str(e)}")
        
        # 计算特征重要性
        try:
            results['feature_importance'] = self._calculate_feature_importance(
                df, numeric_cols, target_col
            )
        except Exception as e:
            logger.warning(f"特征重要性计算失败: {str(e)}")
        
        # 更新汇总信息
        results['summary']['total_tests'] = len(results['tests'])
        results['summary']['significant_tests'] = sum(
            1 for t in results['tests'] 
            if t.get('is_significant', False)
        )
        
        return results
    
    def _mann_whitney_test(
        self,
        df: pd.DataFrame,
        target_col: Optional[str],
        feature_cols: List[str],
        p_value_threshold: float
    ) -> List[Dict]:
        """Mann-Whitney U检验 - 比较两组独立样本"""
        results = []
        
        if target_col is None or target_col not in df.columns:
            return results
        
        # 获取目标变量的唯一值
        unique_values = df[target_col].dropna().unique()
        if len(unique_values) != 2:
            return results
        
        group_a = df[df[target_col] == unique_values[0]]
        group_b = df[df[target_col] == unique_values[1]]
        
        for col in feature_cols:
            if col == target_col or col not in df.columns:
                continue
            
            try:
                data_a = group_a[col].dropna()
                data_b = group_b[col].dropna()
                
                if len(data_a) < 2 or len(data_b) < 2:
                    continue
                
                statistic, p_value = stats.mannwhitneyu(data_a, data_b, alternative='two-sided')
                
                # 计算效应量 (r = Z / sqrt(N))
                n1, n2 = len(data_a), len(data_b)
                z_score = (statistic - n1 * n2 / 2) / np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
                effect_size = abs(z_score) / np.sqrt(n1 + n2)
                
                results.append({
                    'test_name': 'Mann-Whitney U检验',
                    'test_method': 'mann_whitney',
                    'feature': col,
                    'target': target_col,
                    'group_a': str(unique_values[0]),
                    'group_b': str(unique_values[1]),
                    'statistic': round(statistic, 4),
                    'p_value': round(p_value, 6),
                    'is_significant': p_value < p_value_threshold,
                    'effect_size': round(effect_size, 4),
                    'effect_interpretation': self._interpret_effect_size(effect_size),
                    'conclusion': '显著差异' if p_value < p_value_threshold else '无显著差异',
                    'recommendation': self._generate_recommendation(col, target_col, p_value < p_value_threshold)
                })
                
            except Exception as e:
                logger.debug(f"Mann-Whitney检验失败 ({col}): {str(e)}")
                continue
        
        return results
    
    def _kruskal_wallis_test(
        self,
        df: pd.DataFrame,
        target_col: Optional[str],
        feature_cols: List[str],
        p_value_threshold: float
    ) -> List[Dict]:
        """Kruskal-Wallis H检验 - 比较多组独立样本"""
        results = []
        
        if target_col is None or target_col not in df.columns:
            return results
        
        unique_values = df[target_col].dropna().unique()
        if len(unique_values) < 2:
            return results
        
        for col in feature_cols:
            if col == target_col or col not in df.columns:
                continue
            
            try:
                groups = [df[df[target_col] == val][col].dropna().values for val in unique_values]
                groups = [g for g in groups if len(g) > 0]
                
                if len(groups) < 2:
                    continue
                
                statistic, p_value = stats.kruskal(*groups)
                
                # 计算Eta平方效应量
                n = sum(len(g) for g in groups)
                eta_squared = (statistic - len(groups) + 1) / (n - len(groups)) if n > len(groups) else 0
                
                results.append({
                    'test_name': 'Kruskal-Wallis H检验',
                    'test_method': 'kruskal_wallis',
                    'feature': col,
                    'target': target_col,
                    'groups': [str(v) for v in unique_values],
                    'statistic': round(statistic, 4),
                    'p_value': round(p_value, 6),
                    'is_significant': p_value < p_value_threshold,
                    'effect_size': round(eta_squared, 4),
                    'effect_interpretation': self._interpret_eta_squared(eta_squared),
                    'conclusion': '多组间存在显著差异' if p_value < p_value_threshold else '多组间无显著差异',
                    'recommendation': self._generate_recommendation(col, target_col, p_value < p_value_threshold)
                })
                
            except Exception as e:
                logger.debug(f"Kruskal-Wallis检验失败 ({col}): {str(e)}")
                continue
        
        return results
    
    def _chi_square_test(
        self,
        df: pd.DataFrame,
        target_col: Optional[str],
        feature_cols: List[str],
        p_value_threshold: float
    ) -> List[Dict]:
        """卡方检验 - 检验分类变量独立性"""
        results = []
        
        if target_col is None or target_col not in df.columns:
            return results
        
        categorical_features = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        for col in categorical_features:
            if col == target_col or col not in df.columns:
                continue
            
            try:
                # 创建列联表
                contingency_table = pd.crosstab(df[col], df[target_col])
                
                if contingency_table.shape[0] < 2 or contingency_table.shape[1] < 2:
                    continue
                
                chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)
                
                # 计算Cramér's V效应量
                n = contingency_table.sum().sum()
                cramers_v = np.sqrt(chi2 / (n * (min(contingency_table.shape) - 1))) if n > 0 else 0
                
                results.append({
                    'test_name': '卡方独立性检验',
                    'test_method': 'chi2',
                    'feature': col,
                    'target': target_col,
                    'chi2_statistic': round(chi2, 4),
                    'p_value': round(p_value, 6),
                    'degrees_of_freedom': dof,
                    'is_significant': p_value < p_value_threshold,
                    'effect_size': round(cramers_v, 4),
                    'effect_interpretation': self._interpret_cramers_v(cramers_v),
                    'conclusion': '变量间存在显著关联' if p_value < p_value_threshold else '变量间无显著关联',
                    'contingency_table': contingency_table.to_dict(),
                    'recommendation': self._generate_recommendation(col, target_col, p_value < p_value_threshold)
                })
                
            except Exception as e:
                logger.debug(f"卡方检验失败 ({col}): {str(e)}")
                continue
        
        return results
    
    def _kolmogorov_smirnov_test(
        self,
        df: pd.DataFrame,
        target_col: Optional[str],
        feature_cols: List[str],
        p_value_threshold: float
    ) -> List[Dict]:
        """Kolmogorov-Smirnov检验 - 检验分布差异"""
        results = []
        
        if target_col is None or target_col not in df.columns:
            return results
        
        unique_values = df[target_col].dropna().unique()
        if len(unique_values) != 2:
            return results
        
        group_a = df[df[target_col] == unique_values[0]]
        group_b = df[df[target_col] == unique_values[1]]
        
        for col in feature_cols:
            if col == target_col or col not in df.columns:
                continue
            
            try:
                data_a = group_a[col].dropna()
                data_b = group_b[col].dropna()
                
                if len(data_a) < 2 or len(data_b) < 2:
                    continue
                
                statistic, p_value = stats.ks_2samp(data_a, data_b)
                
                results.append({
                    'test_name': 'Kolmogorov-Smirnov检验',
                    'test_method': 'ks',
                    'feature': col,
                    'target': target_col,
                    'group_a': str(unique_values[0]),
                    'group_b': str(unique_values[1]),
                    'ks_statistic': round(statistic, 4),
                    'p_value': round(p_value, 6),
                    'is_significant': p_value < p_value_threshold,
                    'conclusion': '两组分布存在显著差异' if p_value < p_value_threshold else '两组分布无显著差异',
                    'recommendation': self._generate_recommendation(col, target_col, p_value < p_value_threshold)
                })
                
            except Exception as e:
                logger.debug(f"KS检验失败 ({col}): {str(e)}")
                continue
        
        return results
    
    def _spearman_correlation(
        self,
        df: pd.DataFrame,
        target_col: Optional[str],
        feature_cols: List[str],
        p_value_threshold: float
    ) -> List[Dict]:
        """Spearman等级相关 - 非参数相关分析"""
        results = []
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                try:
                    data1 = df[col1].dropna()
                    data2 = df[col2].dropna()
                    
                    # 对齐数据
                    common_index = data1.index.intersection(data2.index)
                    if len(common_index) < 3:
                        continue
                    
                    data1_aligned = data1.loc[common_index]
                    data2_aligned = data2.loc[common_index]
                    
                    correlation, p_value = stats.spearmanr(data1_aligned, data2_aligned)
                    
                    results.append({
                        'test_name': 'Spearman等级相关',
                        'test_method': 'spearman',
                        'feature_1': col1,
                        'feature_2': col2,
                        'correlation': round(correlation, 4),
                        'p_value': round(p_value, 6),
                        'is_significant': p_value < p_value_threshold,
                        'correlation_strength': self._interpret_correlation(abs(correlation)),
                        'conclusion': f"{'显著' if p_value < p_value_threshold else '不显著'}{self._interpret_correlation(abs(correlation))}相关",
                        'recommendation': self._generate_correlation_recommendation(col1, col2, correlation, p_value < p_value_threshold)
                    })
                    
                except Exception as e:
                    logger.debug(f"Spearman相关失败 ({col1}-{col2}): {str(e)}")
                    continue
        
        return results
    
    def _wilcoxon_signed_rank(
        self,
        df: pd.DataFrame,
        target_col: Optional[str],
        feature_cols: List[str],
        p_value_threshold: float
    ) -> List[Dict]:
        """Wilcoxon符号秩检验 - 配对样本比较"""
        results = []
        
        # 需要找到成对的列（如前后测数据）
        pair_patterns = [
            ('_before', '_after'),
            ('_pre', '_post'),
            ('_t1', '_t2'),
            ('start_', 'end_')
        ]
        
        for pattern in pair_patterns:
            for col in feature_cols:
                if pattern[0] in col:
                    paired_col = col.replace(pattern[0], pattern[1])
                    if paired_col in feature_cols and paired_col in df.columns:
                        try:
                            data1 = df[col].dropna()
                            data2 = df[paired_col].dropna()
                            
                            common_index = data1.index.intersection(data2.index)
                            if len(common_index) < 3:
                                continue
                            
                            data1_aligned = data1.loc[common_index]
                            data2_aligned = data2.loc[common_index]
                            
                            statistic, p_value = stats.wilcoxon(data1_aligned, data2_aligned)
                            
                            # 计算效应量
                            z_score = (statistic - len(common_index) * (len(common_index) + 1) / 4) / \
                                     np.sqrt(len(common_index) * (len(common_index) + 1) * (2 * len(common_index) + 1) / 24)
                            effect_size = abs(z_score) / np.sqrt(len(common_index))
                            
                            results.append({
                                'test_name': 'Wilcoxon符号秩检验',
                                'test_method': 'wilcoxon',
                                'feature_before': col,
                                'feature_after': paired_col,
                                'statistic': round(statistic, 4),
                                'p_value': round(p_value, 6),
                                'is_significant': p_value < p_value_threshold,
                                'effect_size': round(effect_size, 4),
                                'effect_interpretation': self._interpret_effect_size(effect_size),
                                'conclusion': '配对样本存在显著差异' if p_value < p_value_threshold else '配对样本无显著差异',
                                'recommendation': self._generate_recommendation(col, paired_col, p_value < p_value_threshold)
                            })
                            
                        except Exception as e:
                            logger.debug(f"Wilcoxon检验失败 ({col}-{paired_col}): {str(e)}")
                            continue
        
        return results
    
    def _calculate_correlation_matrix(self, df: pd.DataFrame, numeric_cols: List[str]) -> Dict:
        """计算相关性矩阵"""
        try:
            if len(numeric_cols) < 2:
                return None
            
            corr_matrix = df[numeric_cols].corr(method='spearman')
            
            return {
                'columns': corr_matrix.columns.tolist(),
                'values': corr_matrix.values.tolist(),
                'shape': corr_matrix.shape
            }
        except Exception as e:
            logger.warning(f"相关性矩阵计算失败: {str(e)}")
            return None
    
    def _calculate_feature_importance(
        self,
        df: pd.DataFrame,
        numeric_cols: List[str],
        target_col: Optional[str]
    ) -> List[Dict]:
        """计算特征重要性"""
        importance_list = []
        
        if target_col is None or target_col not in df.columns:
            return importance_list
        
        try:
            # 对于分类目标，使用ANOVA F-value近似
            if df[target_col].dtype == 'object' or df[target_col].nunique() < 10:
                for col in numeric_cols:
                    if col == target_col:
                        continue
                    
                    groups = [group[col].dropna().values for name, group in df.groupby(target_col)]
                    groups = [g for g in groups if len(g) > 1]
                    
                    if len(groups) >= 2:
                        try:
                            f_stat, p_value = stats.f_oneway(*groups)
                            importance_list.append({
                                'feature': col,
                                'importance_score': round(f_stat, 4),
                                'p_value': round(p_value, 6),
                                'is_significant': p_value < 0.05
                            })
                        except:
                            continue
            
            # 按重要性排序
            importance_list.sort(key=lambda x: x['importance_score'], reverse=True)
            
        except Exception as e:
            logger.warning(f"特征重要性计算失败: {str(e)}")
        
        return importance_list[:10]  # 返回前10个
    
    def _interpret_effect_size(self, r: float) -> str:
        """解释效应量r"""
        if r < 0.1:
            return '可忽略'
        elif r < 0.3:
            return '小效应'
        elif r < 0.5:
            return '中等效应'
        else:
            return '大效应'
    
    def _interpret_eta_squared(self, eta2: float) -> str:
        """解释Eta平方"""
        if eta2 < 0.01:
            return '可忽略'
        elif eta2 < 0.06:
            return '小效应'
        elif eta2 < 0.14:
            return '中等效应'
        else:
            return '大效应'
    
    def _interpret_cramers_v(self, v: float) -> str:
        """解释Cramér's V"""
        if v < 0.1:
            return '可忽略'
        elif v < 0.3:
            return '小效应'
        elif v < 0.5:
            return '中等效应'
        else:
            return '大效应'
    
    def _interpret_correlation(self, r: float) -> str:
        """解释相关系数"""
        if r < 0.1:
            return '可忽略'
        elif r < 0.3:
            return '弱'
        elif r < 0.5:
            return '中等'
        elif r < 0.7:
            return '强'
        else:
            return '很强'
    
    def _generate_recommendation(self, feature: str, target: str, is_significant: bool) -> str:
        """生成建议"""
        if is_significant:
            return f"变量 '{feature}' 与 '{target}' 存在显著关联，建议在后续分析中重点关注此变量"
        else:
            return f"变量 '{feature}' 与 '{target}' 关联不显著，可考虑从模型中排除或进一步探索"
    
    def _generate_correlation_recommendation(self, col1: str, col2: str, corr: float, is_significant: bool) -> str:
        """生成相关性建议"""
        if not is_significant:
            return f"'{col1}' 与 '{col2}' 相关性不显著"
        
        if abs(corr) > 0.8:
            return f"'{col1}' 与 '{col2}' 存在很强相关，可能存在多重共线性，建议只保留其中一个变量"
        elif abs(corr) > 0.5:
            return f"'{col1}' 与 '{col2}' 中等相关，两个变量可能提供相似信息"
        elif corr > 0:
            return f"'{col1}' 与 '{col2}' 正相关，一个变量增加时另一个也倾向于增加"
        else:
            return f"'{col1}' 与 '{col2}' 负相关，一个变量增加时另一个倾向于减少"


# 创建全局实例
statistical_test_service = StatisticalTestService()
