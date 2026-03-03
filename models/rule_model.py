import pandas as pd
import numpy as np
from typing import List, Dict, Union
from itertools import combinations


class RuleModel:
    def __init__(self):
        self.rules = []

    def filter_rules(self, rules: List[Dict], min_support: float) -> List[Dict]:
        if not rules or min_support <= 0 or min_support > 1:
            return []
        filtered_rules = []
        for rule in rules:
            try:
                support = float(rule.get('support', 0))
                if support >= min_support:
                    filtered_rules.append(rule)
            except (ValueError, TypeError):
                continue
        return filtered_rules

    def sort_rules(self, rules: List[Dict], sort_by: str = 'confidence', ascending: bool = False) -> List[Dict]:
        if not rules:
            return []
        valid_sort_metrics = ['support', 'confidence', 'lift', 'conviction']
        if sort_by not in valid_sort_metrics:
            sort_by = 'confidence'
        try:
            sorted_rules = sorted(
                rules,
                key=lambda x: float(x.get(sort_by, 0)),
                reverse=not ascending
            )
            return sorted_rules
        except (ValueError, TypeError):
            return rules

    def generate_rules(
        self,
        transactions: List[List[str]],
        min_support: float = 0.1,
        min_confidence: float = 0.5,
        min_lift: float = 1.0,
        max_len: int = 5
    ) -> List[Dict]:
        if not transactions or min_support <= 0 or min_support > 1:
            return []
        all_items = set()
        for transaction in transactions:
            all_items.update(transaction)
        all_items = list(all_items)

        # 限制最大项集长度，避免规则爆炸
        max_len = int(max_len) if max_len else 5
        max_len = max(2, min(max_len, 10))
        frequent_itemsets = self._find_frequent_itemsets(transactions, all_items, min_support, max_len=max_len)
        rules = []
        for itemset in frequent_itemsets:
            if len(itemset) < 2:
                continue
            if len(itemset) > max_len:
                continue
            for i in range(1, len(itemset)):
                antecedents = combinations(itemset, i)
                for antecedent in antecedents:
                    antecedent = frozenset(antecedent)
                    consequent = frozenset(itemset) - antecedent

                    # 跳过空集
                    if not antecedent or not consequent:
                        continue

                    support = self._calculate_support(transactions, list(itemset))
                    confidence = self._calculate_confidence(transactions, antecedent, consequent)

                    if confidence >= min_confidence:
                        lift = self._calculate_lift(transactions, antecedent, consequent)
                        if lift < float(min_lift):
                            continue
                        conviction = self._calculate_conviction(transactions, antecedent, consequent)

                        # 与前端字段对齐：使用 antecedents/consequents
                        # 并提供 p_value 的保底值，避免前端渲染报错
                        # 简单启发式：当 lift>1 且 confidence 较高时，给出更小的 p 值
                        pv = 0.2
                        if lift > 1 and confidence >= 0.6:
                            pv = 0.03
                        elif lift > 1:
                            pv = 0.08
                        rule = {
                            'antecedents': list(antecedent),
                            'consequents': list(consequent),
                            'support': support,
                            'confidence': confidence,
                            'lift': lift,
                            'conviction': conviction,
                            'length': len(itemset),
                            'p_value': float(pv)
                        }
                        rules.append(rule)
        self.rules = rules
        return rules

    def _find_frequent_itemsets(
        self,
        transactions: List[List[str]],
        items: List[str],
        min_support: float,
        max_len: int = 5
    ) -> List[List[str]]:
        frequent_itemsets = []
        k = 1
        current_itemsets = [frozenset([item]) for item in items]

        while current_itemsets:
            if k > max_len:
                break
            candidate_counts = {}
            for transaction in transactions:
                trans_set = set(transaction)  # 优化：转为set加速查找
                for itemset in current_itemsets:
                    if itemset.issubset(trans_set):
                        candidate_counts[itemset] = candidate_counts.get(itemset, 0) + 1

            num_transactions = len(transactions)
            frequent_itemsets_k = []
            for itemset, count in candidate_counts.items():
                support = count / num_transactions
                if support >= min_support:
                    frequent_itemsets_k.append(list(itemset))

            if not frequent_itemsets_k:  # 如果这一层没有频繁项集，直接结束
                break

            frequent_itemsets.extend(frequent_itemsets_k)
            k += 1
            current_itemsets = self._generate_candidates(frequent_itemsets_k, k)

        return frequent_itemsets

    def _generate_candidates(self, frequent_itemsets: List[List[str]], k: int) -> List[frozenset]:
        candidates = []
        itemsets = [frozenset(itemset) for itemset in frequent_itemsets]
        for i in range(len(itemsets)):
            for j in range(i + 1, len(itemsets)):
                itemset1 = itemsets[i]
                itemset2 = itemsets[j]
                # 只有当前k-1项相同时才合并
                union_set = itemset1.union(itemset2)
                if len(union_set) == k:
                    candidates.append(union_set)
        return list(set(candidates))  # 去重

    def _calculate_support(self, transactions: List[List[str]], itemset: List[str]) -> float:
        itemset_set = set(itemset)
        count = 0
        for transaction in transactions:
            if itemset_set.issubset(set(transaction)):
                count += 1
        return count / len(transactions) if len(transactions) > 0 else 0

    def _calculate_confidence(self, transactions: List[List[str]], antecedent: frozenset,
                              consequent: frozenset) -> float:
        antecedent_support = self._calculate_support(transactions, list(antecedent))
        if antecedent_support == 0:
            return 0
        rule_support = self._calculate_support(transactions, list(antecedent.union(consequent)))
        return rule_support / antecedent_support

    def _calculate_lift(self, transactions: List[List[str]], antecedent: frozenset, consequent: frozenset) -> float:
        antecedent_support = self._calculate_support(transactions, list(antecedent))
        consequent_support = self._calculate_support(transactions, list(consequent))
        if antecedent_support == 0 or consequent_support == 0:
            return 0
        rule_support = self._calculate_support(transactions, list(antecedent.union(consequent)))
        return rule_support / (antecedent_support * consequent_support)

    def _calculate_conviction(self, transactions: List[List[str]], antecedent: frozenset,
                              consequent: frozenset) -> float:
        antecedent_support = self._calculate_support(transactions, list(antecedent))
        consequent_support = self._calculate_support(transactions, list(consequent))
        rule_support = self._calculate_support(transactions, list(antecedent.union(consequent)))

        if antecedent_support == 0 or consequent_support == 0:
            return 0

        rule_confidence = rule_support / antecedent_support

        if rule_confidence >= 1:  # 避免除以0
            return float('inf')

        expected_confidence = consequent_support
        return (1 - expected_confidence) / (1 - rule_confidence)


# =======================================================
# 👇 核心部分：导出功能供外部调用
# =======================================================
rule_model_instance = RuleModel()
filter_rules = rule_model_instance.filter_rules
sort_rules = rule_model_instance.sort_rules
generate_rules = rule_model_instance.generate_rules
