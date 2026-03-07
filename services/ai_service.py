"""
华为云 ModelArts MaaS 平台 DeepSeek-V3.2 AI 服务封装

基于 OpenAI 兼容格式调用华为云代理的 DeepSeek-V3.2 模型，
为平台提供智能分析、报告摘要、自由对话等 AI 推理能力。
"""
import os
import json
import hashlib
import logging
import time
import requests
from collections import Counter
from typing import List, Dict, Any, Optional, Generator

logger = logging.getLogger(__name__)

# NOTE: API 配置统一在此定义，严格遵循华为云 MaaS 平台规范
MAAS_API_URL = "https://api.modelarts-maas.com/v2/chat/completions"
MAAS_MODEL = "deepseek-v3.2"


class AIService:
    """
    华为云 ModelArts MaaS AI 服务封装

    所有对 DeepSeek-V3.2 的调用统一经过此类，
    便于全局控制 temperature、max_tokens 等推理参数。
    """

    # AI 结果缓存 TTL（秒），同一份数据和参数在1小时内不重复调用
    CACHE_TTL = 3600

    def __init__(self) -> None:
        self.api_url: str = MAAS_API_URL
        self.model: str = MAAS_MODEL
        self.api_key: str = self._load_api_key()
        print(f"AI Service initialized: {'Available' if self.api_key else 'Unavailable'}")
        # 默认推理参数，可通过 config.json 的 ai 段覆盖
        self.default_temperature: float = 0.7
        self.default_max_tokens: int = 2048
        self.timeout: int = 120          # 海外部署访问华为云需要更长超时
        self.max_retries: int = 2         # 最大重试次数
        self.retry_delay: float = 2.0     # 重试间隔秒数
        # 缓存：{fingerprint: (timestamp, content)}
        self._cache: Dict[str, tuple[float, str]] = {}

    def _load_api_key(self) -> str:
        """
        从环境变量加载 API Key，优先读取 os.environ，
        其次尝试从项目根目录的 .env 文件中解析。

        Returns:
            API Key 字符串

        Raises:
            ValueError: 未找到 API Key 时抛出
        """
        key = os.environ.get("HUAWEI_MAAS_API_KEY")
        if key:
            return key

        # 尝试从 .env 文件手动解析
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env"
        )
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("HUAWEI_MAAS_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        os.environ["HUAWEI_MAAS_API_KEY"] = key
                        return key

        logger.warning("未找到 HUAWEI_MAAS_API_KEY，AI 功能将不可用")
        return ""

    def is_available(self) -> bool:
        """检查 AI 服务是否已正确配置"""
        return bool(self.api_key)

    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any] | Generator:
        """
        底层 LLM 调用函数，封装对华为云 API 的 HTTP 请求

        Args:
            messages: OpenAI 格式的消息列表 [{"role": "...", "content": "..."}]
            temperature: 推理温度，越高越有创意
            max_tokens: 最大生成 token 数
            stream: 是否启用流式传输

        Returns:
            API 响应的 JSON 字典（非流式），或生成器（流式）

        Raises:
            RuntimeError: API 调用失败时抛出
        """
        if not self.is_available():
            raise RuntimeError("AI 服务未配置：缺少 HUAWEI_MAAS_API_KEY 环境变量")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.default_temperature,
            "max_tokens": max_tokens or self.default_max_tokens,
            "stream": stream
        }

        last_error: Optional[Exception] = None
        attempts = self.max_retries + 1 if not stream else 1  # 流式不重试

        for attempt in range(1, attempts + 1):
            try:
                logger.info(f"AI API 调用 (第{attempt}次): {self.api_url}, model={self.model}")
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                    stream=stream
                )
                response.raise_for_status()

                if stream:
                    return self._parse_stream(response)
                else:
                    return response.json()

            except requests.exceptions.Timeout as e:
                last_error = e
                logger.error(f"AI API 调用超时 (第{attempt}次, timeout={self.timeout}s)")
                if attempt < attempts:
                    logger.info(f"等待 {self.retry_delay}s 后重试...")
                    time.sleep(self.retry_delay)
                    continue
            except requests.exceptions.ConnectionError as e:
                last_error = e
                logger.error(f"AI API 连接失败 (第{attempt}次): {str(e)}")
                if attempt < attempts:
                    logger.info(f"等待 {self.retry_delay}s 后重试...")
                    time.sleep(self.retry_delay)
                    continue
            except requests.exceptions.HTTPError as e:
                logger.error(f"AI API HTTP 错误：{e.response.status_code} - {e.response.text[:500]}")
                raise RuntimeError(
                    f"AI API 返回错误 ({e.response.status_code}): {e.response.text[:200]}"
                )
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.error(f"AI API 网络错误 (第{attempt}次)：{type(e).__name__}: {str(e)}")
                if attempt < attempts:
                    time.sleep(self.retry_delay)
                    continue

        # 所有重试都失败了
        if isinstance(last_error, requests.exceptions.Timeout):
            raise RuntimeError(
                f"AI 推理超时（已重试{attempts}次, 每次{self.timeout}s）。"
                "部署服务器可能无法访问华为云 API，请检查网络连通性。"
            )
        raise RuntimeError(
            f"无法连接到 AI 服务（已重试{attempts}次）: {type(last_error).__name__}: {str(last_error)}"
        )

    def _parse_stream(self, response: requests.Response) -> Generator:
        """
        解析 SSE 流式响应

        Args:
            response: requests 流式响应对象

        Yields:
            每个 chunk 的文本内容
        """
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
            except json.JSONDecodeError:
                continue

    def _extract_content(self, response: Dict[str, Any]) -> str:
        """
        从 API 响应中提取生成文本

        Args:
            response: API 返回的完整 JSON

        Returns:
            模型生成的文本内容
        """
        choices = response.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _format_number(self, value: Any, digits: int = 4, fallback: str = "N/A") -> str:
        if value is None:
            return fallback
        try:
            return f"{float(value):.{digits}f}"
        except (TypeError, ValueError):
            return fallback

    def _extract_rule_items(self, rule: Dict[str, Any]) -> tuple[List[str], List[str]]:
        antecedents = rule.get("antecedents") or rule.get("antecedent") or []
        consequents = rule.get("consequents") or rule.get("consequent") or []

        if not isinstance(antecedents, list):
            antecedents = [str(antecedents)] if antecedents else []
        if not isinstance(consequents, list):
            consequents = [str(consequents)] if consequents else []

        return [str(item) for item in antecedents if str(item).strip()], [str(item) for item in consequents if str(item).strip()]

    def _format_rule_side(self, items: List[str]) -> str:
        return " ∧ ".join(items) if items else "（空）"

    def _normalize_rules_for_prompt(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for rule in rules:
            antecedents, consequents = self._extract_rule_items(rule)
            support = self._safe_float(rule.get("support"))
            confidence = self._safe_float(rule.get("confidence"))
            lift = self._safe_float(rule.get("lift"), 1.0)
            p_value = rule.get("p_value")
            p_value_num = self._safe_float(p_value, 1.0) if p_value is not None else None
            significant = bool(
                rule.get("significant")
                or rule.get("is_significant")
                or (p_value_num is not None and p_value_num <= 0.05)
            )
            evidence_score = (
                (4.0 if significant else 0.0)
                + min(max(lift, 0.0), 5.0) * 1.2
                + min(max(confidence, 0.0), 1.0) * 2.0
                + min(max(support, 0.0), 1.0) * 1.5
                + (1.0 if antecedents and consequents else 0.0)
            )

            normalized.append({
                "antecedents": antecedents,
                "consequents": consequents,
                "support": support,
                "confidence": confidence,
                "lift": lift,
                "p_value": p_value_num,
                "significant": significant,
                "length": int(rule.get("length", len(antecedents) + len(consequents)) or 0),
                "evidence_score": evidence_score
            })

        normalized.sort(
            key=lambda r: (
                r["evidence_score"],
                1 if r["significant"] else 0,
                -r["p_value"] if r["p_value"] is not None else 0.0
            ),
            reverse=True
        )
        return normalized

    def _summarize_rule_landscape(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        normalized = self._normalize_rules_for_prompt(rules)
        total_rules = len(normalized)
        significant_rules = [r for r in normalized if r["significant"]]
        high_lift_rules = [r for r in normalized if r["lift"] >= 1.5]
        high_confidence_rules = [r for r in normalized if r["confidence"] >= 0.8]
        low_support_rules = [r for r in normalized if r["support"] < 0.05]

        item_counter: Counter[str] = Counter()
        for rule in normalized:
            item_counter.update(rule["antecedents"])
            item_counter.update(rule["consequents"])

        top_items = [{"item": item, "count": count} for item, count in item_counter.most_common(6)]
        top_rules = normalized[:12]
        caution_rules = low_support_rules[:5]

        avg_support = sum(r["support"] for r in normalized) / total_rules if total_rules else 0.0
        avg_confidence = sum(r["confidence"] for r in normalized) / total_rules if total_rules else 0.0
        avg_lift = sum(r["lift"] for r in normalized) / total_rules if total_rules else 0.0

        top_rule_lines = []
        for idx, rule in enumerate(top_rules, start=1):
            top_rule_lines.append(
                f"{idx}. {self._format_rule_side(rule['antecedents'])} → {self._format_rule_side(rule['consequents'])} | "
                f"lift={self._format_number(rule['lift'], 2)} | "
                f"confidence={self._format_number(rule['confidence'], 2)} | "
                f"support={self._format_number(rule['support'], 4)} | "
                f"p={self._format_number(rule['p_value'], 4)} | "
                f"significant={'是' if rule['significant'] else '否'}"
            )

        caution_lines = []
        for idx, rule in enumerate(caution_rules, start=1):
            caution_lines.append(
                f"{idx}. {self._format_rule_side(rule['antecedents'])} → {self._format_rule_side(rule['consequents'])} | "
                f"support={self._format_number(rule['support'], 4)} | "
                f"confidence={self._format_number(rule['confidence'], 2)}"
            )

        return {
            "normalized_rules": normalized,
            "top_rules": top_rules,
            "summary_lines": [
                f"总规则数：{total_rules}",
                f"统计显著规则数：{len(significant_rules)}",
                f"高提升度规则数（lift ≥ 1.5）：{len(high_lift_rules)}",
                f"高置信规则数（confidence ≥ 0.80）：{len(high_confidence_rules)}",
                f"低支持度规则数（support < 0.05）：{len(low_support_rules)}",
                f"平均支持度：{self._format_number(avg_support, 4)}",
                f"平均置信度：{self._format_number(avg_confidence, 4)}",
                f"平均提升度：{self._format_number(avg_lift, 4)}",
            ],
            "top_rule_lines": top_rule_lines,
            "caution_lines": caution_lines,
            "top_items": top_items,
            "top_rule": top_rules[0] if top_rules else None
        }

    def _summarize_statistical_tests(self, statistical_tests: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        tests = statistical_tests.get("tests", []) if isinstance(statistical_tests, dict) else []
        normalized_tests = []
        for test in tests:
            p_value = self._safe_float(test.get("p_value"), 1.0)
            effect_size = self._safe_float(test.get("effect_size"), 0.0)
            normalized_tests.append({
                "test_name": str(test.get("test_name", "未命名检验")),
                "feature": str(test.get("feature", "")),
                "target": str(test.get("target", "")),
                "p_value": p_value,
                "effect_size": effect_size,
                "conclusion": str(test.get("conclusion", "")),
                "recommendation": str(test.get("recommendation", "")),
                "is_significant": bool(test.get("is_significant") or p_value <= 0.05),
                "effect_interpretation": str(test.get("effect_interpretation", ""))
            })

        normalized_tests.sort(
            key=lambda t: (
                1 if t["is_significant"] else 0,
                t["effect_size"],
                -t["p_value"]
            ),
            reverse=True
        )
        significant_tests = [t for t in normalized_tests if t["is_significant"]]

        top_test_lines = []
        for idx, test in enumerate(normalized_tests[:6], start=1):
            desc = f"{idx}. {test['test_name']} | {test['feature']} ↔ {test['target']} | p={self._format_number(test['p_value'], 4)}"
            if test["effect_size"] > 0:
                desc += f" | effect={self._format_number(test['effect_size'], 3)}"
            if test["conclusion"]:
                desc += f" | 结论={test['conclusion']}"
            top_test_lines.append(desc)

        return {
            "tests": normalized_tests,
            "summary_lines": [
                f"统计检验总数：{len(normalized_tests)}",
                f"显著检验数：{len(significant_tests)}"
            ],
            "top_test_lines": top_test_lines
        }

    def _build_analysis_prompt(
        self,
        rules: List[Dict[str, Any]],
        summary: Optional[Dict[str, Any]] = None,
        statistical_tests: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        summary = summary or {}
        rule_snapshot = self._summarize_rule_landscape(rules)
        stats_snapshot = self._summarize_statistical_tests(statistical_tests)
        top_items_text = "\n".join(
            f"- {item['item']}：在高价值规则中出现 {item['count']} 次"
            for item in rule_snapshot["top_items"]
        ) or "- 暂无高频因子"

        caution_text = "\n".join(f"- {line}" for line in rule_snapshot["caution_lines"]) or "- 暂无明显低支持度规则"
        top_rules_text = "\n".join(f"- {line}" for line in rule_snapshot["top_rule_lines"]) or "- 无规则可分析"
        stats_text = "\n".join(f"- {line}" for line in stats_snapshot["top_test_lines"]) or "- 暂无统计检验结果"

        system_prompt = (
            "你是「BivaStat-Miner 双变量关联挖掘与非参数统计分析平台」的高级分析引擎。"
            "\n你的职责不是复述指标，而是基于证据给出稳健、可执行、可审计的分析。"
            "\n请严格遵守以下规则："
            "\n1. 只能根据提供的数据下结论，不得虚构数据。"
            "\n2. 必须明确区分相关性与因果性。"
            "\n3. 评价规则时优先综合 lift、confidence、support、p 值与统计显著性。"
            "\n4. 输出必须使用中文 Markdown，但不要使用 Markdown 表格或代码块。"
            "\n5. 输出必须严格按以下标题顺序组织："
            "\n## 总体判断"
            "\n## 高价值规则"
            "\n## 统计校验"
            "\n## 风险与限制"
            "\n## 建议动作"
            "\n## 后续验证"
            "\n6. 每个部分都要尽量引用具体指标，不要只写抽象判断。"
            "\n7. 如果证据不足，要明确写“证据不足”或“建议继续验证”。"
        )

        user_prompt = (
            "### 分析任务概况\n"
            f"- 总规则数：{summary.get('total_rules', len(rules))}\n"
            f"- 显著性阈值 α：{summary.get('p_value_threshold', 0.05)}\n"
            f"- 统计检验方法提示：{summary.get('test_method', '未提供')}\n"
            f"- 总记录数：{summary.get('total_records', '未提供')}\n\n"
            "### 规则总体分布\n"
            + "\n".join(f"- {line}" for line in rule_snapshot["summary_lines"])
            + "\n\n### 高价值规则样本\n"
            + top_rules_text
            + "\n\n### 高频驱动因子\n"
            + top_items_text
            + "\n\n### 需要谨慎解读的规则\n"
            + caution_text
            + "\n\n### 统计检验概况\n"
            + "\n".join(f"- {line}" for line in stats_snapshot["summary_lines"])
            + "\n\n### 统计检验重点结果\n"
            + stats_text
            + "\n\n请输出一份适合直接展示给业务和研究人员的深度分析报告。"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def _build_report_summary_prompt(
        self,
        data_info: Dict[str, Any],
        analysis_results: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        rules = analysis_results.get("association_rules", []) or analysis_results.get("rules", [])
        summary = analysis_results.get("summary", {}) or {}
        statistical_tests = analysis_results.get("statistical_tests", {})

        rule_snapshot = self._summarize_rule_landscape(rules)
        stats_snapshot = self._summarize_statistical_tests(statistical_tests)
        shape = data_info.get("shape", [0, 0]) if isinstance(data_info, dict) else [0, 0]
        quality_score = (
            data_info.get("quality_report", {}).get("overall_score")
            if isinstance(data_info.get("quality_report"), dict)
            else data_info.get("overall_score")
        )
        top_rule = rule_snapshot.get("top_rule")
        top_rule_line = (
            f"{self._format_rule_side(top_rule['antecedents'])} → {self._format_rule_side(top_rule['consequents'])} | "
            f"lift={self._format_number(top_rule['lift'], 2)} | confidence={self._format_number(top_rule['confidence'], 2)} | "
            f"support={self._format_number(top_rule['support'], 4)}"
            if top_rule else "暂无可引用的核心规则"
        )

        system_prompt = (
            "你是一位面向管理层的资深商业分析专家。"
            "\n请根据提供的数据概况与分析结果，输出一份简洁但有证据支撑的执行摘要。"
            "\n输出必须使用中文 Markdown，且严格按以下标题组织："
            "\n## 执行结论"
            "\n## 关键发现"
            "\n## 管理建议"
            "\n## 风险提示"
            "\n要求："
            "\n- 不使用表格和代码块。"
            "\n- 必须引用具体数字。"
            "\n- 不得夸大结论，不得把相关性写成因果性。"
            "\n- 语言保持克制、专业、适合报告正文直接引用。"
        )

        user_prompt = (
            "### 数据资产概览\n"
            f"- 记录数：{shape[0] if isinstance(shape, (list, tuple)) and len(shape) > 0 else 0}\n"
            f"- 特征数：{shape[1] if isinstance(shape, (list, tuple)) and len(shape) > 1 else 0}\n"
            f"- 数值变量数：{len(data_info.get('numeric_columns', []))}\n"
            f"- 分类变量数：{len(data_info.get('categorical_columns', []))}\n"
            f"- 数据质量评分：{quality_score if quality_score is not None else '未提供'}\n\n"
            "### 规则分析概览\n"
            + "\n".join(f"- {line}" for line in rule_snapshot["summary_lines"])
            + "\n\n### 最有代表性的规则\n"
            + f"- {top_rule_line}\n"
            + "\n### 统计检验概览\n"
            + "\n".join(f"- {line}" for line in stats_snapshot["summary_lines"])
            + "\n\n### 统计检验重点\n"
            + ("\n".join(f"- {line}" for line in stats_snapshot["top_test_lines"][:3]) or "- 暂无统计检验结果")
            + "\n\n### 额外摘要字段\n"
            + f"- 分析摘要：{json.dumps(summary, ensure_ascii=False)}\n"
            + "\n请生成适合写入正式报告的执行摘要。"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    # ---- 缓存辅助 ----

    def _fingerprint(self, *args: Any) -> str:
        """根据输入生成稳定的哈希指纹"""
        raw = json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]

    def _get_cached(self, key: str) -> Optional[str]:
        """(命中时返回缓存内容，否则 None"""
        entry = self._cache.get(key)
        if entry and (time.time() - entry[0]) < self.CACHE_TTL:
            logger.info(f"AI 缓存命中: {key}")
            return entry[1]
        return None

    def _set_cached(self, key: str, content: str) -> None:
        self._cache[key] = (time.time(), content)
        # 最多保留 20 条，超出则淘汰最旧的
        if len(self._cache) > 20:
            oldest = min(self._cache, key=lambda k: self._cache[k][0])
            del self._cache[oldest]

    # ---- AI 调用（带缓存） ----

    def analyze_rules(
        self,
        rules: List[Dict[str, Any]],
        summary: Optional[Dict[str, Any]] = None,
        statistical_tests: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        对关联规则挖掘结果进行 AI 深度解读，并结合统计检验进行校准。
        相同输入在 CACHE_TTL 内直接返回缓存结果，不重复调用 API。
        """
        fp = self._fingerprint('analyze_rules', rules, summary, statistical_tests)
        cached = self._get_cached(fp)
        if cached:
            return cached

        messages = self._build_analysis_prompt(rules, summary, statistical_tests)
        response = self._call_llm(messages, temperature=0.25, max_tokens=2200)
        content = self._extract_content(response)
        self._set_cached(fp, content)
        return content

    def generate_report_summary(
        self,
        data_info: Dict[str, Any],
        analysis_results: Dict[str, Any]
    ) -> str:
        """
        为分析报告生成 AI 撰写的执行摘要。
        相同输入在 CACHE_TTL 内直接返回缓存结果，不重复调用 API。
        """
        fp = self._fingerprint('report_summary', data_info, analysis_results)
        cached = self._get_cached(fp)
        if cached:
            return cached

        messages = self._build_report_summary_prompt(data_info, analysis_results)
        response = self._call_llm(messages, temperature=0.2, max_tokens=1200)
        content = self._extract_content(response)
        self._set_cached(fp, content)
        return content

    def chat(
        self,
        user_message: str,
        context: Optional[str] = None
    ) -> str:
        """
        通用 AI 对话接口，支持用户提出关于分析结果的自由问题

        Args:
            user_message: 用户的问题
            context: 可选的上下文信息（例如当前数据集的描述）

        Returns:
            AI 的回答文本
        """
        system_prompt = (
            "你是「BivaStat-Miner 双变量关联挖掘与非参数统计分析平台」的内置 AI 助手。"
            "你精通统计学、数据挖掘、关联分析、非参数检验等领域。"
            "请用专业且友好的中文回答用户的问题。"
            "如果问题涉及具体的数据分析，请给出基于统计学原理的建议。"
        )

        if context:
            system_prompt += f"\n\n当前分析上下文：{context}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = self._call_llm(messages, temperature=0.7, max_tokens=2048)
        return self._extract_content(response)

    def test_connection(self) -> Dict[str, Any]:
        """
        测试与华为云 MaaS API 的连通性（不消耗大量 token）。
        返回诊断信息字典。
        """
        result: Dict[str, Any] = {
            "api_url": self.api_url,
            "model": self.model,
            "api_key_set": bool(self.api_key),
            "timeout": self.timeout,
        }
        if not self.api_key:
            result["status"] = "error"
            result["message"] = "未配置 HUAWEI_MAAS_API_KEY"
            return result

        try:
            start = time.time()
            resp = requests.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5,
                },
                timeout=30,
            )
            elapsed = round(time.time() - start, 2)
            result["latency_seconds"] = elapsed
            result["http_status"] = resp.status_code

            if resp.ok:
                result["status"] = "ok"
                result["message"] = f"连接成功，延迟 {elapsed}s"
            else:
                result["status"] = "error"
                result["message"] = f"HTTP {resp.status_code}: {resp.text[:300]}"
        except requests.exceptions.Timeout:
            result["status"] = "timeout"
            result["message"] = "连接超时（30s），服务器可能无法访问华为云 API"
        except requests.exceptions.ConnectionError as e:
            result["status"] = "unreachable"
            result["message"] = f"无法连接: {str(e)[:300]}"
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"{type(e).__name__}: {str(e)[:300]}"

        return result

    def chat_stream(
        self,
        user_message: str,
        context: Optional[str] = None
    ) -> Generator:
        """
        流式对话接口

        Args:
            user_message: 用户的问题
            context: 可选上下文

        Yields:
            逐字符/逐 token 的文本内容
        """
        system_prompt = (
            "你是「BivaStat-Miner 双变量关联挖掘与非参数统计分析平台」的内置 AI 助手。"
            "你精通统计学、数据挖掘、关联分析、非参数检验等领域。"
            "请用专业且友好的中文回答用户的问题。"
        )

        if context:
            system_prompt += f"\n\n当前分析上下文：{context}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        return self._call_llm(messages, temperature=0.7, max_tokens=2048, stream=True)


# 全局单例
ai_service = AIService()
