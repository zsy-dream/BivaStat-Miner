import pandas as pd
import numpy as np
from scipy import stats
from typing import List, Dict, Any, Union, Tuple
from itertools import combinations
from core.logging import logger

class RuleMiner:
    def __init__(self):
        self.rules = []

    def generate_rules(
        self,
        df: pd.DataFrame,
        min_support: float = 0.05,
        min_confidence: float = 0.4,
        min_lift: float = 1.0,
        max_len: int = 2,  # 默认为 2，专注于双变量
        calculate_p_value: bool = True
    ) -> List[Dict[str, Any]]:
        """
        基于 Apriori 思想的关联规则挖掘，并计算真实的统计显著性 (P-Value)。
        """
        if df is None or df.empty:
            return []

        # 转换为 transactions 结构
        transactions, total_count = self._df_to_transactions(df)
        if total_count == 0:
            return []

        # 1. 寻找频繁项集
        frequent_itemsets = self._find_frequent_itemsets(transactions, total_count, min_support, max_len)
        
        # 2. 生成规则并计算指标
        rules = []
        for itemset, support in frequent_itemsets.items():
            if len(itemset) < 2:
                continue
            
            # 对每一对 (A, B) 生成规则 A -> B
            for i in range(1, len(itemset)):
                for antecedent in combinations(itemset, i):
                    antecedent = frozenset(antecedent)
                    consequent = itemset - antecedent
                    
                    # A -> B
                    rules.append(self._calculate_rule_metrics(
                        transactions, antecedent, consequent, total_count, calculate_p_value
                    ))

        # 3. 过滤
        filtered_rules = [
            r for r in rules 
            if r['confidence'] >= min_confidence and r['lift'] >= min_lift
        ]
        
        return filtered_rules

    def _df_to_transactions(self, df: pd.DataFrame) -> Tuple[Dict[frozenset, int], int]:
        """
        高性能转换：统计每个项集（项的集合）出现的频数。
        """
        # 自动分箱与处理
        processed_items = []
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                # 简单分箱
                try:
                    bins = pd.qcut(df[col], q=5, duplicates='drop', labels=False)
                    processed_items.append(df[col].name + "=" + bins.astype(str))
                except:
                    processed_items.append(df[col].name + "=" + df[col].astype(str))
            else:
                processed_items.append(df[col].name + "=" + df[col].astype(str))
        
        temp_df = pd.concat(processed_items, axis=1)
        transactions_list = temp_df.apply(lambda x: frozenset(x.dropna()), axis=1)
        
        counts = {}
        for t in transactions_list:
            counts[t] = counts.get(t, 0) + 1
            
        return transactions_list.to_list(), len(df)

    def _find_frequent_itemsets(
        self, 
        transactions: List[frozenset], 
        total_count: int, 
        min_support: float, 
        max_len: int
    ) -> Dict[frozenset, float]:
        """
        Apriori 算法实现
        """
        frequent_itemsets = {}
        min_count = min_support * total_count
        
        # L1
        item_counts = {}
        for t in transactions:
            for item in t:
                item_f = frozenset([item])
                item_counts[item_f] = item_counts.get(item_f, 0) + 1
        
        L = {k: v / total_count for k, v in item_counts.items() if v >= min_count}
        frequent_itemsets.update(L)
        
        current_L = list(L.keys())
        for k in range(2, max_len + 1):
            candidates = self._generate_candidates(current_L, k)
            if not candidates:
                break
            
            candidate_counts = {}
            for t in transactions:
                # 优化：只检查在事务中的候选集
                for c in candidates:
                    if c.issubset(t):
                        candidate_counts[c] = candidate_counts.get(c, 0) + 1
            
            current_L = [k for k, v in candidate_counts.items() if v >= min_count]
            if not current_L:
                break
                
            for c in current_L:
                frequent_itemsets[c] = candidate_counts[c] / total_count
        
        return frequent_itemsets

    def _generate_candidates(self, prev_L: List[frozenset], k: int) -> List[frozenset]:
        candidates = set()
        for i in range(len(prev_L)):
            for j in range(i + 1, len(prev_L)):
                union = prev_L[i] | prev_L[j]
                if len(union) == k:
                    candidates.add(union)
        return list(candidates)

    def _calculate_rule_metrics(
        self, 
        transactions: List[frozenset], 
        A: frozenset, 
        B: frozenset, 
        total: int,
        calc_p: bool
    ) -> Dict[str, Any]:
        """
        计算支持度、置信度、提升度及真实 P 值。
        """
        a_count = sum(1 for t in transactions if A.issubset(t))
        b_count = sum(1 for t in transactions if B.issubset(t))
        ab_count = sum(1 for t in transactions if (A | B).issubset(t))
        
        support = ab_count / total
        confidence = ab_count / a_count if a_count > 0 else 0
        lift = confidence / (b_count / total) if b_count > 0 else 0
        
        p_val = 1.0
        if calc_p and total > 0:
            # 构建 2x2 列联表
            #         B发生   B不发生
            # A发生    n11     n12
            # A不发生  n21     n22
            n11 = ab_count
            n12 = a_count - ab_count
            n21 = b_count - ab_count
            n22 = total - (n11 + n12 + n21)
            
            try:
                # 样本量大时用卡方，小时用 Fisher
                if total > 40 and all(x > 5 for x in [n11, n12, n21, n22]):
                    _, p_val, _, _ = stats.chi2_contingency([[n11, n12], [n21, n22]], correction=True)
                else:
                    _, p_val = stats.fisher_exact([[n11, n12], [n21, n22]])
            except:
                p_val = 0.5 # 默认不显著
                
        return {
            'antecedents': list(A),
            'consequents': list(B),
            'support': float(support),
            'confidence': float(confidence),
            'lift': float(lift),
            'p_value': float(p_val),
            'significant': p_val < 0.05
        }

class AlgorithmService:
    def __init__(self):
        self.miner = RuleMiner()

    def mine_association(self, df: pd.DataFrame, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.miner.generate_rules(
            df,
            min_support=float(params.get('min_support', 0.05)),
            min_confidence=float(params.get('min_confidence', 0.4)),
            min_lift=float(params.get('min_lift', 1.0)),
            max_len=int(params.get('max_len', 2))
        )

    def nonparametric_test(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """多种非参数统计检验支持"""
        test_method = params.get('test_method', 'auto')
        alpha = float(params.get('alpha', 0.05))
        var1 = params.get('var1')
        var2 = params.get('var2')
        
        if not var1 or not var2: return {'error': '缺少变量名'}
        
        s1 = df[var1].dropna()
        s2 = df[var2].dropna()
        
        try:
            if test_method == 'auto':
                test_method = 'chi2' if df[var1].dtype == 'object' else 'mannwhitney'
            
            if test_method == 'mannwhitney':
                stat, p = stats.mannwhitneyu(s1, s2, alternative='two-sided')
                name = 'Mann-Whitney U检验'
            elif test_method == 'chi2':
                table = pd.crosstab(df[var1], df[var2])
                stat, p, _, _ = stats.chi2_contingency(table)
                name = '卡方检验'
            elif test_method == 'ks':
                stat, p = stats.ks_2samp(s1, s2)
                name = 'K-S检验'
            elif test_method == 'wilcoxon' and len(s1) == len(s2):
                stat, p = stats.wilcoxon(s1, s2)
                name = 'Wilcoxon配对符号秩检验'
            elif test_method == 'kruskal':
                # 这里假设 var2 是分组变量
                groups = [group[var1].values for _, group in df.groupby(var2)]
                stat, p = stats.kruskal(*groups)
                name = 'Kruskal-Wallis H检验'
            else:
                return {'error': f'不支持或不满足条件的检验: {test_method}'}
                
            return {
                'test_name': name,
                'statistic': float(stat),
                'p_value': float(p),
                'alpha': alpha,
                'significant': p < alpha,
                'var1': var1,
                'var2': var2
            }
        except Exception as e:
            logger.error(f"Statistical test error: {e}")
            return {'error': str(e)}

algorithm_service = AlgorithmService()
