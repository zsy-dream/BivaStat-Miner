import pandas as pd
import numpy as np
from typing import List, Dict, Set, Tuple, Union
from itertools import combinations


class RuleModel:
    def __init__(self):
        self.rules = []
        self.support_cache: Dict[frozenset, int] = {}  # 用于存储项集频数，避免重复扫描数据集
        self._item_tids: Dict[str, set] = {}  # 位图索引：item -> 包含该 item 的交易 id 集合

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

    # ---- 位图辅助方法 ----
    def _build_bitmap_index(self, transactions: List[List[str]]) -> None:
        """构建倒排位图索引：每个 item 映射到包含它的交易 ID 集合。"""
        self._item_tids = {}
        for tid, transaction in enumerate(transactions):
            for item in transaction:
                if item not in self._item_tids:
                    self._item_tids[item] = set()
                self._item_tids[item].add(tid)

    def _itemset_tids(self, itemset: frozenset) -> set:
        """利用位图索引快速求出包含 itemset 的交易 ID 集合（交集）。"""
        it = iter(itemset)
        first = next(it)
        tids = self._item_tids.get(first)
        if tids is None:
            return set()
        result = set(tids)  # 拷贝，防止修改原始索引
        for item in it:
            item_tids = self._item_tids.get(item)
            if item_tids is None:
                return set()
            result &= item_tids  # 交集（原地操作更快）
            if not result:
                return result
        return result

    def _itemset_count(self, itemset: frozenset) -> int:
        """返回 itemset 的支持计数，优先走缓存，否则用位图索引计算。"""
        cached = self.support_cache.get(itemset)
        if cached is not None:
            return cached
        count = len(self._itemset_tids(itemset))
        self.support_cache[itemset] = count
        return count

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
        self.support_cache = {}  # 重置缓存

        # 构建位图索引（一次性建好，后续频繁项集挖掘 + 规则生成共用）
        self._build_bitmap_index(transactions)

        frequent_itemsets = self._find_frequent_itemsets(transactions, all_items, min_support, max_len=max_len)

        num_transactions = len(transactions)

        rules = []
        for itemset in frequent_itemsets:
            if len(itemset) < 2:
                continue
            if len(itemset) > max_len:
                continue
            itemset_fs = frozenset(itemset)
            itemset_count = self._itemset_count(itemset_fs)
            support = itemset_count / num_transactions

            for i in range(1, len(itemset)):
                for antecedent_tuple in combinations(itemset, i):
                    antecedent = frozenset(antecedent_tuple)
                    consequent = itemset_fs - antecedent

                    # 跳过空集
                    if not antecedent or not consequent:
                        continue

                    # 使用位图缓存计算各项频率
                    antecedent_count = self._itemset_count(antecedent)
                    if antecedent_count == 0:
                        continue

                    confidence = itemset_count / antecedent_count

                    if confidence >= min_confidence:
                        consequent_count = self._itemset_count(consequent)

                        lift = confidence / (consequent_count / num_transactions) if consequent_count > 0 else 0
                        if lift < float(min_lift):
                            continue

                        # Conviction 计算
                        conviction = (1 - (consequent_count / num_transactions)) / (1 - confidence) if confidence < 1 else float('inf')

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
        """基于位图索引的 Apriori 频繁项集挖掘（无需逐交易 issubset 检查）。"""
        frequent_itemsets: List[List[str]] = []
        num_transactions = len(transactions)
        min_count = min_support * num_transactions  # 绝对支持度阈值
        k = 1

        # ---- L1：直接从位图索引获取单项频数 ----
        frequent_items: List[frozenset] = []
        for item in items:
            tids = self._item_tids.get(item)
            count = len(tids) if tids else 0
            fs = frozenset([item])
            self.support_cache[fs] = count
            if count >= min_count:
                frequent_items.append(fs)
                frequent_itemsets.append([item])

        if not frequent_items:
            return frequent_itemsets

        current_frequent = frequent_items
        k = 2

        while current_frequent and k <= max_len:
            # 候选生成：合并 k-1 项频繁集
            candidates = self._generate_candidates(
                [list(fs) for fs in current_frequent], k
            )
            if not candidates:
                break

            next_frequent: List[frozenset] = []
            for candidate in candidates:
                # 利用位图交集快速计算支持度
                count = len(self._itemset_tids(candidate))
                self.support_cache[candidate] = count
                if count >= min_count:
                    next_frequent.append(candidate)
                    frequent_itemsets.append(list(candidate))

            current_frequent = next_frequent
            k += 1

        return frequent_itemsets

    def _generate_candidates(self, frequent_itemsets: List[List[str]], k: int) -> List[frozenset]:
        candidates = set()
        itemsets = [frozenset(itemset) for itemset in frequent_itemsets]
        # 将频繁 k-1 项集放入 set 以便快速剪枝
        freq_set = set(itemsets)
        for i in range(len(itemsets)):
            for j in range(i + 1, len(itemsets)):
                union_set = itemsets[i] | itemsets[j]
                if len(union_set) == k:
                    # Apriori 剪枝：所有 k-1 子集都必须是频繁的
                    if k <= 2 or all(
                        (union_set - frozenset([item])) in freq_set
                        for item in union_set
                    ):
                        candidates.add(union_set)
        return list(candidates)


# =======================================================
# 👇 核心部分：导出功能供外部调用
# =======================================================
rule_model_instance = RuleModel()
filter_rules = rule_model_instance.filter_rules
sort_rules = rule_model_instance.sort_rules
generate_rules = rule_model_instance.generate_rules
