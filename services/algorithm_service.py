from collections import Counter
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from models.rule_model import RuleModel

rule_model = RuleModel()


class AlgorithmService:
    """算法服务类"""
    
    def __init__(self):
        self.rule_model = rule_model
    
    def mine_association(self, df: pd.DataFrame, params: dict) -> list:
        """挖掘关联规则的服务层封装"""
        result = self.mine_association_with_diagnostics(df, params)
        return result.get('association_rules', [])

    def mine_association_with_diagnostics(self, df: pd.DataFrame, params: dict) -> dict:
        """
        自适应关联规则挖掘：
        - 先评估当前数据集是否适合挖掘
        - 若初始参数无规则/规则过弱，则自动执行回退方案
        - 返回结构化诊断信息，便于前端解释“为什么没有结果”
        """
        diagnostics = self.assess_mining_suitability(df, params)
        weak_rule_threshold = int(params.get('weak_rule_threshold', 3) or 3)
        attempt_specs = self._build_attempt_specs(params, diagnostics)

        attempts_with_rules: List[Dict[str, Any]] = []
        for idx, spec in enumerate(attempt_specs):
            attempt_snapshot, rules = self._run_mining_attempt(df, params, spec)
            attempts_with_rules.append({
                'snapshot': attempt_snapshot,
                'rules': rules
            })

            if idx == 0 and attempt_snapshot['rules_found'] >= weak_rule_threshold:
                break

            if idx > 0 and attempt_snapshot['rules_found'] >= weak_rule_threshold:
                break

        if not attempts_with_rules:
            return {
                'association_rules': [],
                'summary': {
                    'total_rules': 0,
                    'significant_rules': 0,
                    'avg_confidence': 0.0,
                    'avg_support': 0.0,
                    'p_value_threshold': float(params.get('p_value_threshold', 0.05) or 0.05),
                    'adaptive_mode_used': False,
                    'selected_attempt_name': '未执行',
                    'selected_attempt_strategy': 'none',
                    'readiness_score': diagnostics.get('readiness_score', 0.0),
                    'readiness_level': diagnostics.get('readiness_level', 'poor')
                },
                'mining_diagnostics': diagnostics,
                'warnings': ['未执行任何有效的挖掘尝试。'],
                'fallback_attempts': [],
                'selected_attempt': None
            }

        selected_index = self._select_output_attempt(attempts_with_rules, weak_rule_threshold)
        selected_rules = attempts_with_rules[selected_index]['rules']

        final_attempts = []
        for idx, attempt in enumerate(attempts_with_rules):
            snapshot = dict(attempt['snapshot'])
            snapshot['selected_for_output'] = idx == selected_index
            final_attempts.append(snapshot)

        selected_attempt = dict(final_attempts[selected_index])
        p_value_threshold = float(params.get('p_value_threshold', 0.05) or 0.05)
        significant_rules = len([
            rule for rule in selected_rules
            if float(rule.get('p_value', 1.0)) <= p_value_threshold
        ])
        avg_confidence = float(
            sum(float(rule.get('confidence', 0.0)) for rule in selected_rules) / len(selected_rules)
        ) if selected_rules else 0.0
        avg_support = float(
            sum(float(rule.get('support', 0.0)) for rule in selected_rules) / len(selected_rules)
        ) if selected_rules else 0.0

        runtime_warnings = self._build_runtime_warnings(final_attempts, weak_rule_threshold)
        warnings = self._dedupe_strings(diagnostics.get('warnings', []) + runtime_warnings)
        suggestions = diagnostics.get('suggestions', [])
        if not selected_rules:
            suggestions = self._dedupe_strings(suggestions + [
                '优先降低最小支持度，或在预处理阶段合并稀有类别后重新挖掘。',
                '排除订单号、流水号、时间戳等高基数字段，保留重复出现较多的业务特征。',
                '如果样本量偏小，可先增加样本或减少参与挖掘的列数。'
            ])

        selected_attempt_params = selected_attempt.get('params', {})
        diagnostics = {
            **diagnostics,
            'selected_columns': list(selected_attempt.get('selected_columns', diagnostics.get('selected_columns', []))),
            'transaction_summary': {
                'transaction_count': int(selected_attempt.get('transaction_count', 0)),
                'avg_items_per_transaction': float(selected_attempt.get('avg_items_per_transaction', 0.0)),
                'min_items_per_transaction': int(selected_attempt.get('min_items_per_transaction', 0)),
                'max_items_per_transaction': int(selected_attempt.get('max_items_per_transaction', 0)),
                'empty_transactions': int(selected_attempt.get('empty_transactions', 0)),
                'frequent_single_items_at_threshold': int(selected_attempt.get('frequent_single_items_at_threshold', 0))
            },
            'top_items': selected_attempt.get('top_items', []),
            'effective_params': selected_attempt_params,
            'attempts_run': len(final_attempts),
            'suggestions': suggestions
        }

        return {
            'association_rules': selected_rules,
            'summary': {
                'total_rules': int(len(selected_rules)),
                'significant_rules': int(significant_rules),
                'avg_confidence': round(avg_confidence, 4),
                'avg_support': round(avg_support, 4),
                'p_value_threshold': p_value_threshold,
                'adaptive_mode_used': selected_attempt.get('strategy') != 'initial',
                'selected_attempt_name': selected_attempt.get('name'),
                'selected_attempt_strategy': selected_attempt.get('strategy'),
                'readiness_score': float(diagnostics.get('readiness_score', 0.0)),
                'readiness_level': diagnostics.get('readiness_level', 'poor')
            },
            'mining_diagnostics': diagnostics,
            'warnings': warnings,
            'fallback_attempts': final_attempts,
            'selected_attempt': selected_attempt
        }

    def assess_mining_suitability(self, df: pd.DataFrame, params: dict) -> dict:
        """评估数据集是否适合进行关联规则挖掘。"""
        if df is None or getattr(df, "empty", True):
            return {
                'readiness_score': 0.0,
                'readiness_level': 'poor',
                'summary': '当前数据集为空，无法进行关联规则挖掘。',
                'dataset_shape': {'rows': 0, 'cols': 0},
                'candidate_columns': [],
                'selected_columns': [],
                'preferred_columns': [],
                'excluded_columns': [],
                'warnings': ['当前数据集为空。'],
                'suggestions': ['请先上传或完成预处理后再执行挖掘。'],
                'recommended_params': {
                    'min_support': 0.05,
                    'min_confidence': 0.5,
                    'min_lift': 1.0
                }
            }

        rows = int(df.shape[0])
        cols = int(df.shape[1])
        selection = self._select_mining_columns(df, params)
        selected_columns = selection['selected_columns']
        excluded_columns = selection['excluded_columns']
        high_cardinality_columns = [
            item for item in excluded_columns
            if '高基数' in item.get('reason', '') or '分散' in item.get('reason', '')
        ]
        constant_columns = [
            item for item in excluded_columns
            if '单一' in item.get('reason', '')
        ]

        recommended_support = self._recommend_support_threshold(rows, selection['average_unique_ratio'])
        recommended_confidence = self._recommend_confidence_threshold(rows)
        warnings: List[str] = []
        suggestions: List[str] = []
        score = 100.0

        if rows < 80:
            score -= 35
            warnings.append(f'样本量仅 {rows} 行，规则稳定性会明显受限。')
            suggestions.append('尽量扩充样本量后再进行正式挖掘。')
        elif rows < 200:
            score -= 20
            warnings.append(f'样本量为 {rows} 行，适合做探索性挖掘，但稳定性一般。')
        elif rows < 500:
            score -= 10

        if len(selected_columns) < 2:
            score -= 45
            warnings.append('可用于挖掘的有效列少于 2 个，无法形成稳定的共现规则。')
            suggestions.append('请保留至少 2 个具有重复取值的特征列。')
        elif len(selected_columns) < 4:
            score -= 18
            warnings.append(f'当前仅有 {len(selected_columns)} 个候选列，规则空间偏窄。')
            suggestions.append('可增加更多低基数或可分箱的业务字段参与挖掘。')
        elif len(selected_columns) < 6:
            score -= 8

        if high_cardinality_columns:
            penalty = min(18, len(high_cardinality_columns) * 3)
            score -= penalty
            names = '、'.join(item['name'] for item in high_cardinality_columns[:3])
            warnings.append(f'检测到 {len(high_cardinality_columns)} 个高基数/低重复列（如 {names}），它们不适合直接挖掘。')
            suggestions.append('优先排除 ID、订单号、精确时间戳等高基数字段。')

        if constant_columns:
            score -= min(12, len(constant_columns) * 2)

        average_unique_ratio = selection['average_unique_ratio']
        if average_unique_ratio > 0.9:
            score -= 25
            warnings.append('候选列整体重复模式较弱，多数字段取值过于分散。')
            suggestions.append(f'建议先将最小支持度降到约 {recommended_support:.3f}，并合并稀有类别。')
        elif average_unique_ratio > 0.8:
            score -= 15
            warnings.append('候选列重复度一般，可能需要放宽支持度或减少字段范围。')
        elif average_unique_ratio > 0.7:
            score -= 8

        if selection['categorical_candidate_count'] == 0 and selection['numeric_candidate_count'] < 2:
            score -= 15
            warnings.append('当前缺少可形成稳定模式的分类字段，挖掘结果可能较弱。')
            suggestions.append('优先保留具有业务分层含义的分类列，或对连续数值进行更粗粒度分箱。')

        score = max(0.0, min(100.0, round(score, 1)))
        readiness_level = self._score_to_level(score)
        if readiness_level == 'good':
            readiness_text = '重复模式较充分，适合直接进行关联规则挖掘。'
        elif readiness_level == 'limited':
            readiness_text = '可以挖掘，但可能需要适度放宽阈值或筛掉噪声字段。'
        elif readiness_level == 'weak':
            readiness_text = '可探索性较弱，建议先优化字段选择和阈值。'
        else:
            readiness_text = '当前数据不适合直接挖掘，需优先处理字段和样本问题。'

        summary = (
            f'当前数据共 {rows} 行、{cols} 列，可用于挖掘的候选列 {len(selected_columns)} 个。'
            f' 适配度评分 {score:.1f} 分，{readiness_text}'
        )

        return {
            'readiness_score': float(score),
            'readiness_level': readiness_level,
            'summary': summary,
            'dataset_shape': {
                'rows': rows,
                'cols': cols
            },
            'candidate_columns': list(selection['candidate_columns']),
            'selected_columns': list(selected_columns),
            'preferred_columns': list(selection['preferred_columns']),
            'excluded_columns': list(excluded_columns),
            'warnings': self._dedupe_strings(warnings),
            'suggestions': self._dedupe_strings(suggestions),
            'recommended_params': {
                'min_support': round(recommended_support, 4),
                'min_confidence': round(recommended_confidence, 4),
                'min_lift': 1.0
            },
            'candidate_overview': {
                'candidate_count': int(len(selection['candidate_columns'])),
                'selected_count': int(len(selected_columns)),
                'excluded_count': int(len(excluded_columns)),
                'categorical_candidate_count': int(selection['categorical_candidate_count']),
                'numeric_candidate_count': int(selection['numeric_candidate_count']),
                'average_unique_ratio': float(selection['average_unique_ratio'])
            }
        }

    def _build_transactions(self, df: pd.DataFrame, params: dict) -> list[list[str]]:
        """
        将 DataFrame 转为交易数据（transactions）。

        关键优化：
        - 使用 “列名=取值/分箱” 作为 item，避免不同列相同数值被误判为同一 item
        - 数值列做分箱（默认 5 份），避免连续值导致 item 爆炸、Apriori 卡死
        - 过滤高基数分类列/限制参与挖掘的列数，避免组合爆炸
        """
        transactions, _ = self._build_transactions_with_metadata(df, params)
        return transactions

    def _build_transactions_with_metadata(self, df: pd.DataFrame, params: dict) -> Tuple[List[List[str]], Dict[str, Any]]:
        if df is None or getattr(df, "empty", True):
            return [], {
                'selected_columns': [],
                'candidate_columns': [],
                'preferred_columns': [],
                'excluded_columns': [],
                'transaction_count': 0,
                'avg_items_per_transaction': 0.0,
                'min_items_per_transaction': 0,
                'max_items_per_transaction': 0,
                'empty_transactions': 0,
                'frequent_single_items_at_threshold': 0,
                'top_items': []
            }

        max_bins, _, _ = self._get_mining_limits(params)
        selection = self._select_mining_columns(df, params)
        cols = selection['selected_columns']
        if not cols:
            return [], {
                'selected_columns': [],
                'candidate_columns': list(selection['candidate_columns']),
                'preferred_columns': list(selection['preferred_columns']),
                'excluded_columns': list(selection['excluded_columns']),
                'transaction_count': 0,
                'avg_items_per_transaction': 0.0,
                'min_items_per_transaction': 0,
                'max_items_per_transaction': 0,
                'empty_transactions': int(len(df)),
                'frequent_single_items_at_threshold': 0,
                'top_items': []
            }

        work = df[cols].copy()
        numeric_cols = work.select_dtypes(include=[np.number]).columns.tolist()
        binned = {}
        for col in numeric_cols:
            series = work[col]
            if series.dropna().nunique() <= 1:
                continue
            try:
                bins = pd.qcut(series, q=max_bins, duplicates="drop")
            except Exception:
                try:
                    bins = pd.cut(series, bins=max_bins)
                except Exception:
                    continue
            binned[col] = bins.astype(str)

        # ---- 向量化构建 transactions（避免逐行 iterrows，大数据集提速 10-50x）----
        # 先把每列转成 "列名=值" 的字符串 Series，NaN 位置保持为 NaN
        tagged_columns: Dict[str, pd.Series] = {}
        for col in cols:
            if col in binned:
                series = binned[col]
                tagged_columns[col] = col + "=" + series
                tagged_columns[col] = tagged_columns[col].where(series != "nan", other=np.nan)
            else:
                series = work[col].astype(str).str.strip()
                tagged_columns[col] = (col + "=" + series).where(
                    work[col].notna() & (series != "") & (series != "nan"),
                    other=np.nan
                )

        tagged_df = pd.DataFrame(tagged_columns, index=work.index)

        transactions: List[List[str]] = []
        transaction_sizes: List[int] = []
        item_counter: Counter = Counter()
        empty_transactions = 0

        # 使用 numpy 数组直接遍历，避免 itertuples 的 Python 对象开销
        arr = tagged_df.values  # ndarray，NaN 位置仍为 float NaN
        for row in arr:
            items: List[str] = [v for v in row if isinstance(v, str)]
            if items:
                deduped_items = list(dict.fromkeys(items))
                transactions.append(deduped_items)
                transaction_sizes.append(len(deduped_items))
                item_counter.update(deduped_items)
            else:
                empty_transactions += 1

        transaction_count = int(len(transactions))
        min_support = float(params.get('min_support', 0.1) or 0.1)
        top_items = []
        if transaction_count > 0:
            for item, count in item_counter.most_common(8):
                top_items.append({
                    'item': item,
                    'count': int(count),
                    'support': round(float(count / transaction_count), 4)
                })

        frequent_single_items_at_threshold = 0
        if transaction_count > 0:
            frequent_single_items_at_threshold = int(sum(
                1 for count in item_counter.values()
                if (count / transaction_count) >= min_support
            ))

        return transactions, {
            'selected_columns': list(cols),
            'candidate_columns': list(selection['candidate_columns']),
            'preferred_columns': list(selection['preferred_columns']),
            'excluded_columns': list(selection['excluded_columns']),
            'transaction_count': transaction_count,
            'avg_items_per_transaction': round(
                float(sum(transaction_sizes) / transaction_count), 4
            ) if transaction_count else 0.0,
            'min_items_per_transaction': int(min(transaction_sizes)) if transaction_sizes else 0,
            'max_items_per_transaction': int(max(transaction_sizes)) if transaction_sizes else 0,
            'empty_transactions': int(empty_transactions),
            'frequent_single_items_at_threshold': frequent_single_items_at_threshold,
            'top_items': top_items
        }

    def _get_mining_limits(self, params: dict) -> Tuple[int, int, int]:
        max_bins = int(params.get("numeric_bins", 5) or 5)
        max_bins = max(2, min(max_bins, 20))
        max_unique_cat = int(params.get("max_unique_per_categorical", 50) or 50)
        max_unique_cat = max(5, min(max_unique_cat, 500))
        max_cols = int(params.get("max_columns_for_mining", 30) or 30)
        max_cols = max(5, min(max_cols, 200))
        return max_bins, max_unique_cat, max_cols

    def _select_mining_columns(self, df: pd.DataFrame, params: dict) -> Dict[str, Any]:
        rows = int(len(df))
        _, max_unique_cat, max_cols = self._get_mining_limits(params)
        numeric_cols = set(df.select_dtypes(include=[np.number]).columns.tolist())

        requested_columns = params.get("selected_columns")
        if isinstance(requested_columns, list) and requested_columns:
            columns_to_inspect = [col for col in requested_columns if col in df.columns]
            has_user_selection = True
        else:
            columns_to_inspect = df.columns.tolist()
            has_user_selection = False

        candidate_stats: List[Dict[str, Any]] = []
        excluded_columns: List[Dict[str, Any]] = []
        for col in columns_to_inspect:
            series = df[col]
            non_null_count = int(series.notna().sum())
            non_null_ratio = float(round((non_null_count / rows), 4)) if rows else 0.0
            unique_count = int(series.nunique(dropna=True))
            unique_ratio = float(round((unique_count / max(non_null_count, 1)), 4)) if non_null_count else 0.0
            base_info = {
                'name': col,
                'dtype': str(series.dtype),
                'non_null_count': non_null_count,
                'non_null_ratio': non_null_ratio,
                'unique_count': unique_count,
                'unique_ratio': unique_ratio
            }

            if non_null_count == 0:
                excluded_columns.append({
                    **base_info,
                    'reason': '列值全部为空'
                })
                continue

            if unique_count <= 1:
                excluded_columns.append({
                    **base_info,
                    'reason': '列取值单一，无法形成模式'
                })
                continue

            if col not in numeric_cols:
                if unique_count > max_unique_cat:
                    excluded_columns.append({
                        **base_info,
                        'reason': f'高基数分类列（唯一值 {unique_count} > {max_unique_cat}）'
                    })
                    continue
                if non_null_count >= 20 and unique_ratio > 0.9:
                    excluded_columns.append({
                        **base_info,
                        'reason': '分类值过于分散，重复模式不足'
                    })
                    continue
                repeat_score = float(round((1 - min(unique_ratio, 1.0)) * max(non_null_ratio, 0.1), 4))
                role = 'categorical'
            else:
                repeat_score = float(round(min(0.85, 0.45 + min(non_null_ratio, 1.0) * 0.35), 4))
                role = 'numeric_binned'

            candidate_stats.append({
                **base_info,
                'role': role,
                'repeat_score': repeat_score
            })

        if has_user_selection:
            ordered_candidates = candidate_stats
        else:
            categorical_candidates = sorted(
                [item for item in candidate_stats if item['role'] == 'categorical'],
                key=lambda item: (-item['repeat_score'], item['unique_count'], item['name'])
            )
            numeric_candidates = sorted(
                [item for item in candidate_stats if item['role'] == 'numeric_binned'],
                key=lambda item: (-item['repeat_score'], item['unique_count'], item['name'])
            )
            ordered_candidates = categorical_candidates + numeric_candidates

        selected_candidates = ordered_candidates[:max_cols]
        overflow_candidates = ordered_candidates[max_cols:]
        for item in overflow_candidates:
            excluded_columns.append({
                'name': item['name'],
                'dtype': item['dtype'],
                'non_null_count': item['non_null_count'],
                'non_null_ratio': item['non_null_ratio'],
                'unique_count': item['unique_count'],
                'unique_ratio': item['unique_ratio'],
                'reason': f'超出最大参与列数 {max_cols}'
            })

        preferred_candidates = sorted(
            candidate_stats,
            key=lambda item: (
                0 if item['role'] == 'categorical' else 1,
                -item['repeat_score'],
                item['unique_ratio'],
                item['name']
            )
        )

        return {
            'candidate_columns': [item['name'] for item in ordered_candidates],
            'selected_columns': [item['name'] for item in selected_candidates],
            'preferred_columns': [
                item['name']
                for item in preferred_candidates[:max(2, min(12, len(preferred_candidates)))]
            ] if preferred_candidates else [],
            'excluded_columns': sorted(
                excluded_columns,
                key=lambda item: item['name']
            ),
            'categorical_candidate_count': int(sum(1 for item in ordered_candidates if item['role'] == 'categorical')),
            'numeric_candidate_count': int(sum(1 for item in ordered_candidates if item['role'] == 'numeric_binned')),
            'average_unique_ratio': round(
                float(np.mean([item['unique_ratio'] for item in selected_candidates])),
                4
            ) if selected_candidates else 1.0
        }

    def _build_attempt_specs(self, params: dict, diagnostics: dict) -> List[Dict[str, Any]]:
        max_bins, max_unique_cat, max_cols = self._get_mining_limits(params)
        current_support = float(params.get('min_support', 0.1) or 0.1)
        current_confidence = float(params.get('min_confidence', 0.5) or 0.5)
        current_lift = float(params.get('min_lift', 1.0) or 1.0)
        preferred_columns = diagnostics.get('preferred_columns', [])

        raw_specs = [
            {
                'name': '原始参数',
                'strategy': 'initial',
                'reason': '按当前配置直接执行挖掘。',
                'overrides': {}
            },
            {
                'name': '放宽阈值',
                'strategy': 'relaxed_thresholds',
                'reason': '初始阈值偏严格时，适度降低支持度和置信度门槛。',
                'overrides': {
                    'min_support': round(max(0.005, current_support * 0.6), 4),
                    'min_confidence': round(max(0.25, current_confidence * 0.85), 4),
                    'min_lift': round(max(0.8, current_lift * 0.9), 4),
                    'numeric_bins': max(2, max_bins - 1)
                }
            }
        ]

        if preferred_columns:
            focused_columns = preferred_columns[:max(4, min(12, len(preferred_columns)))]
            raw_specs.append({
                'name': '聚焦高重复字段',
                'strategy': 'focused_columns',
                'reason': '仅保留重复模式更明显的字段，并进一步放宽阈值。',
                'overrides': {
                    'selected_columns': focused_columns,
                    'min_support': round(max(0.003, current_support * 0.4), 4),
                    'min_confidence': round(max(0.2, current_confidence * 0.75), 4),
                    'min_lift': round(max(0.7, current_lift * 0.8), 4),
                    'numeric_bins': max(2, max_bins - 2),
                    'max_columns_for_mining': min(max_cols, max(4, len(focused_columns))),
                    'max_unique_per_categorical': min(max_unique_cat, 30)
                }
            })

        unique_specs = []
        seen_signatures = set()
        for spec in raw_specs:
            effective_params = dict(params)
            effective_params.update(spec.get('overrides', {}))
            signature = (
                round(float(effective_params.get('min_support', 0.1) or 0.1), 4),
                round(float(effective_params.get('min_confidence', 0.5) or 0.5), 4),
                round(float(effective_params.get('min_lift', 1.0) or 1.0), 4),
                int(effective_params.get('max_len', 5) or 5),
                int(effective_params.get('numeric_bins', max_bins) or max_bins),
                int(effective_params.get('max_columns_for_mining', max_cols) or max_cols),
                int(effective_params.get('max_unique_per_categorical', max_unique_cat) or max_unique_cat),
                tuple(effective_params.get('selected_columns') or [])
            )
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            unique_specs.append(spec)

        return unique_specs

    def _run_mining_attempt(self, df: pd.DataFrame, params: dict, spec: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        attempt_params = dict(params)
        attempt_params.update(spec.get('overrides', {}))

        transactions, tx_meta = self._build_transactions_with_metadata(df, attempt_params)
        rules: List[Dict[str, Any]] = []
        frequent_single_items = int(tx_meta.get('frequent_single_items_at_threshold', 0))
        if transactions and frequent_single_items >= 2:
            generated_rules = self.rule_model.generate_rules(
                transactions,
                min_support=float(attempt_params.get('min_support', 0.1)),
                min_confidence=float(attempt_params.get('min_confidence', 0.5)),
                min_lift=float(attempt_params.get('min_lift', 1.0)),
                max_len=int(attempt_params.get('max_len', 5))
            )
            rules = self.rule_model.sort_rules(
                self.rule_model.filter_rules(
                    generated_rules,
                    float(attempt_params.get('min_support', 0.1))
                ),
                sort_by='lift'
            )

        warnings: List[str] = []
        if not tx_meta.get('selected_columns'):
            warnings.append('没有可用于挖掘的有效字段。')
        if tx_meta.get('avg_items_per_transaction', 0.0) < 2:
            warnings.append('单条记录可用项过少，难以形成稳定的共现模式。')
        if frequent_single_items < 2:
            warnings.append('满足当前支持度阈值的单项不足 2 个，无法形成规则。')
        if not rules:
            warnings.append('该轮策略未生成关联规则。')

        top_lift = float(max((float(rule.get('lift', 0.0)) for rule in rules), default=0.0))
        top_confidence = float(max((float(rule.get('confidence', 0.0)) for rule in rules), default=0.0))
        snapshot = {
            'name': spec.get('name', '未命名尝试'),
            'strategy': spec.get('strategy', 'unknown'),
            'reason': spec.get('reason', ''),
            'params': {
                'min_support': round(float(attempt_params.get('min_support', 0.1) or 0.1), 4),
                'min_confidence': round(float(attempt_params.get('min_confidence', 0.5) or 0.5), 4),
                'min_lift': round(float(attempt_params.get('min_lift', 1.0) or 1.0), 4),
                'max_len': int(attempt_params.get('max_len', 5) or 5),
                'numeric_bins': int(attempt_params.get('numeric_bins', 5) or 5),
                'max_columns_for_mining': int(attempt_params.get('max_columns_for_mining', 30) or 30),
                'selected_columns': list(attempt_params.get('selected_columns') or tx_meta.get('selected_columns') or [])
            },
            'rules_found': int(len(rules)),
            'selected_columns': list(tx_meta.get('selected_columns', [])),
            'excluded_columns_count': int(len(tx_meta.get('excluded_columns', []))),
            'excluded_columns_preview': list(tx_meta.get('excluded_columns', [])[:8]),
            'transaction_count': int(tx_meta.get('transaction_count', 0)),
            'avg_items_per_transaction': float(tx_meta.get('avg_items_per_transaction', 0.0)),
            'min_items_per_transaction': int(tx_meta.get('min_items_per_transaction', 0)),
            'max_items_per_transaction': int(tx_meta.get('max_items_per_transaction', 0)),
            'empty_transactions': int(tx_meta.get('empty_transactions', 0)),
            'frequent_single_items_at_threshold': frequent_single_items,
            'top_items': list(tx_meta.get('top_items', [])),
            'top_lift': round(top_lift, 4),
            'top_confidence': round(top_confidence, 4),
            'warnings': self._dedupe_strings(warnings)
        }
        return snapshot, rules

    def _select_output_attempt(self, attempts_with_rules: List[Dict[str, Any]], weak_rule_threshold: int) -> int:
        if not attempts_with_rules:
            return 0

        initial_rules_found = attempts_with_rules[0]['snapshot'].get('rules_found', 0)
        if initial_rules_found >= weak_rule_threshold:
            return 0

        best_index = 0
        best_key = self._attempt_sort_key(attempts_with_rules[0]['snapshot'], weak_rule_threshold)
        for idx, attempt in enumerate(attempts_with_rules[1:], start=1):
            current_key = self._attempt_sort_key(attempt['snapshot'], weak_rule_threshold)
            if current_key > best_key:
                best_index = idx
                best_key = current_key
        return best_index

    def _attempt_sort_key(self, snapshot: Dict[str, Any], weak_rule_threshold: int) -> Tuple[int, int, float, float]:
        rules_found = int(snapshot.get('rules_found', 0))
        return (
            1 if rules_found >= weak_rule_threshold else 0,
            rules_found,
            float(snapshot.get('top_lift', 0.0)),
            float(snapshot.get('top_confidence', 0.0))
        )

    def _build_runtime_warnings(self, attempts: List[Dict[str, Any]], weak_rule_threshold: int) -> List[str]:
        if not attempts:
            return []

        selected_attempt = next(
            (attempt for attempt in attempts if attempt.get('selected_for_output')),
            attempts[0]
        )
        initial_attempt = attempts[0]
        warnings: List[str] = []

        if selected_attempt.get('strategy') != 'initial':
            warnings.append(
                f"初始参数仅生成 {initial_attempt.get('rules_found', 0)} 条规则，系统已自动切换为“{selected_attempt.get('name')}”并输出 {selected_attempt.get('rules_found', 0)} 条规则。"
            )

        if int(selected_attempt.get('rules_found', 0)) == 0:
            warnings.append(f"系统共执行 {len(attempts)} 轮挖掘尝试，仍未发现满足阈值的规则。")
        elif int(selected_attempt.get('rules_found', 0)) < weak_rule_threshold:
            warnings.append(
                f"当前仅得到 {selected_attempt.get('rules_found', 0)} 条规则，结果更适合做探索性分析。"
            )

        if int(selected_attempt.get('frequent_single_items_at_threshold', 0)) < 2:
            warnings.append('当前支持度阈值下可成对组合的频繁单项太少。')

        return self._dedupe_strings(warnings)

    def _recommend_support_threshold(self, rows: int, average_unique_ratio: float) -> float:
        if rows < 200:
            support = 0.08
        elif rows < 1000:
            support = 0.05
        elif rows < 5000:
            support = 0.03
        else:
            support = 0.01

        if average_unique_ratio > 0.85:
            support *= 0.7
        elif average_unique_ratio > 0.75:
            support *= 0.85
        return max(0.003, round(support, 4))

    def _recommend_confidence_threshold(self, rows: int) -> float:
        if rows < 300:
            return 0.55
        if rows < 2000:
            return 0.6
        if rows < 10000:
            return 0.65
        return 0.7

    def _score_to_level(self, score: float) -> str:
        if score >= 80:
            return 'good'
        if score >= 60:
            return 'limited'
        if score >= 40:
            return 'weak'
        return 'poor'

    def _dedupe_strings(self, values: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            if not value:
                continue
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result
    
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
                is_var1_categorical = not pd.api.types.is_numeric_dtype(df[var1])
                is_var2_categorical = not pd.api.types.is_numeric_dtype(df[var2])
                if is_var1_categorical or is_var2_categorical:
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
                stat, p_value, dof, expected = stats.chi2_contingency(
                    contingency_table.to_numpy(dtype=float)
                )
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
                'significant': bool(p_value < alpha),
                'var1': var1,
                'var2': var2,
                'test_method': test_method
            }
            
        except Exception as e:
            results = {
                'error': str(e),
                'var1': var1,
                'var2': var2,
                'test_method': test_method
            }
        
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
