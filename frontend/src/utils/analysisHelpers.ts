import type { AssociationRule, MiningDiagnostics } from '../types';

// ======================== 类型定义 ========================

export type SortKey = 'support' | 'confidence' | 'lift';

export interface RuleSortConfig {
    key: SortKey;
    direction: 'asc' | 'desc';
}

export type AiSectionBlock =
    | { type: 'paragraph'; content: string }
    | { type: 'bullet'; content: string }
    | { type: 'ordered'; content: string; order: number }
    | { type: 'subheading'; content: string };

export interface AiSection {
    title: string;
    blocks: AiSectionBlock[];
}

// ======================== 规则排序 ========================

export function getRuleMetric(rule: AssociationRule, key: SortKey): number {
    if (key === 'support') return rule.support;
    if (key === 'confidence') return rule.confidence;
    return rule.lift;
}

// ======================== 挖掘适配度样式 ========================

export function getMiningReadinessStyle(level: MiningDiagnostics['readiness_level']) {
    if (level === 'good') {
        return {
            badge: 'bg-emerald-50 text-emerald-700',
            iconWrap: 'border-emerald-100 bg-emerald-50 text-emerald-600',
        };
    }

    if (level === 'limited') {
        return {
            badge: 'bg-sky-50 text-sky-700',
            iconWrap: 'border-sky-100 bg-sky-50 text-sky-600',
        };
    }

    if (level === 'weak') {
        return {
            badge: 'bg-amber-50 text-amber-700',
            iconWrap: 'border-amber-100 bg-amber-50 text-amber-600',
        };
    }

    return {
        badge: 'bg-red-50 text-red-700',
        iconWrap: 'border-red-100 bg-red-50 text-red-600',
    };
}

export function formatMiningReadinessLevel(level: MiningDiagnostics['readiness_level'] | string) {
    if (level === 'good') return '适合挖掘';
    if (level === 'limited') return '可挖掘';
    if (level === 'weak') return '结果偏弱';
    return '需先优化';
}

// ======================== 格式化工具 ========================

export function formatCompactNumber(value: number | undefined) {
    if (typeof value !== 'number' || Number.isNaN(value)) return '--';
    return value.toFixed(1);
}

export function formatAttemptParams(params?: Record<string, unknown>) {
    if (!params) return '当前策略未返回详细参数。';

    const parts: string[] = [];
    const support = typeof params.min_support === 'number' ? params.min_support : undefined;
    const confidence = typeof params.min_confidence === 'number' ? params.min_confidence : undefined;
    const lift = typeof params.min_lift === 'number' ? params.min_lift : undefined;
    const bins = typeof params.numeric_bins === 'number' ? params.numeric_bins : undefined;

    if (support !== undefined) parts.push(`支持度 ${support.toFixed(3)}`);
    if (confidence !== undefined) parts.push(`置信度 ${confidence.toFixed(3)}`);
    if (lift !== undefined) parts.push(`提升度 ${lift.toFixed(2)}`);
    if (bins !== undefined) parts.push(`分箱 ${bins}`);

    return parts.length ? parts.join(' · ') : '当前策略未返回详细参数。';
}

// ======================== AI 解读解析 ========================

export function parseAiAnalysis(text: string): AiSection[] {
    if (!text.trim()) return [];

    const lines = text.split('\n');
    const sections: AiSection[] = [];
    let currentSection: AiSection | null = null;

    const ensureSection = () => {
        if (!currentSection) {
            currentSection = { title: '分析摘要', blocks: [] };
            sections.push(currentSection);
        }
        return currentSection;
    };

    for (const rawLine of lines) {
        const trimmed = rawLine.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith('## ')) {
            currentSection = { title: trimmed.slice(3), blocks: [] };
            sections.push(currentSection);
            continue;
        }

        if (trimmed.startsWith('# ')) {
            currentSection = { title: trimmed.slice(2), blocks: [] };
            sections.push(currentSection);
            continue;
        }

        const section = ensureSection();

        if (trimmed.startsWith('### ')) {
            section.blocks.push({ type: 'subheading', content: trimmed.slice(4) });
            continue;
        }

        const orderedMatch = trimmed.match(/^(\d+)[.\uFF0E)\uFF09]\s*(.*)$/);
        if (orderedMatch) {
            section.blocks.push({
                type: 'ordered',
                order: Number(orderedMatch[1]),
                content: orderedMatch[2]
            });
            continue;
        }

        if (/^[-*•]\s/.test(trimmed)) {
            section.blocks.push({ type: 'bullet', content: trimmed.slice(2) });
            continue;
        }

        section.blocks.push({ type: 'paragraph', content: trimmed });
    }

    return sections.filter((section) => section.blocks.length > 0 || section.title.trim().length > 0);
}

export function getAiSectionStyle(title: string) {
    if (title.includes('总体判断')) {
        return {
            container: 'border-sky-400/20 bg-sky-400/5',
            dot: 'bg-sky-300',
            badge: 'bg-sky-400/15 text-sky-100'
        };
    }

    if (title.includes('高价值规则')) {
        return {
            container: 'border-emerald-400/20 bg-emerald-400/5',
            dot: 'bg-emerald-300',
            badge: 'bg-emerald-400/15 text-emerald-100'
        };
    }

    if (title.includes('统计')) {
        return {
            container: 'border-violet-400/20 bg-violet-400/5',
            dot: 'bg-violet-300',
            badge: 'bg-violet-400/15 text-violet-100'
        };
    }

    if (title.includes('风险')) {
        return {
            container: 'border-amber-400/20 bg-amber-400/5',
            dot: 'bg-amber-300',
            badge: 'bg-amber-400/15 text-amber-100'
        };
    }

    if (title.includes('建议')) {
        return {
            container: 'border-cyan-400/20 bg-cyan-400/5',
            dot: 'bg-cyan-300',
            badge: 'bg-cyan-400/15 text-cyan-100'
        };
    }

    return {
        container: 'border-white/10 bg-white/5',
        dot: 'bg-gray-300',
        badge: 'bg-white/10 text-gray-100'
    };
}

export function escapeHtml(text: string): string {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

export function formatAiInline(text: string): string {
    return escapeHtml(text)
        .replace(/\*\*(.+?)\*\*/g, '<strong class="font-bold text-white">$1</strong>')
        .replace(/`([^`]+)`/g, '<code class="rounded bg-white/10 px-1.5 py-0.5 text-[11px] text-sky-200">$1</code>');
}

// ======================== 雷达图数据 ========================

export function prepareRadarData(rules: AssociationRule[]) {
    const topRules = rules.slice(0, 5);
    let maxValue = 0;

    const radarData = topRules.map((r, i) => {
        const confVal = r.confidence * 100;
        const liftVal = Math.min(r.lift * 10, 100);

        maxValue = Math.max(maxValue, confVal, liftVal);

        return {
            rule: `核心驱动子网络 #${i + 1}`,
            confidence: confVal,
            lift: liftVal,
            full_rule: `${r.antecedents.join(', ')} => ${r.consequents.join(', ')}`
        };
    });

    return { radarData, maxValue: Math.ceil(maxValue / 10) * 10 + 10 };
}
