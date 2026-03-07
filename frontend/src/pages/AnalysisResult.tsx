import { useState, useEffect, useRef, useCallback, memo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
    Layers, RefreshCw, CheckCircle2, AlertCircle,
    FileCode, BarChart3, TerminalSquare, StopCircle, Clock, ArrowRight, Activity,
    Search, ArrowUpDown, Sparkles, Brain, Zap, Info, MessageSquare, Loader2,
    Copy, ChevronDown, ChevronUp, RotateCcw, Link2, type LucideIcon
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { cn } from '../utils/cn';
import { algorithmService, aiService, extractErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { Button } from '../components/ui/button';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger
} from '../components/ui/dropdown-menu';
import { useAbortEffect } from '../hooks/useAbortEffect';
import {
    getRuleMetric, getMiningReadinessStyle, formatMiningReadinessLevel,
    formatCompactNumber, formatAttemptParams, parseAiAnalysis,
    getAiSectionStyle, formatAiInline, prepareRadarData,
    type SortKey, type RuleSortConfig,
} from '../utils/analysisHelpers';
import type { Task, AssociationRule } from '../types';
const LAST_TASK_ID_STORAGE_KEY = 'analysis:last-task-id';

type QuickActionButtonProps = {
    icon: LucideIcon;
    label: string;
    onClick: () => void;
    accentClassName: string;
};

function RuleActionGuide() {
    return (
        <div className="group/action-guide relative flex items-center">
            <button
                type="button"
                aria-label="查看操作说明"
                className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-[#dbe7ff] bg-white text-[#7c8aa5] shadow-sm transition-all hover:bg-[#f8fbff] hover:text-[#2383e2] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/30"
            >
                <Info size={13} />
            </button>
            <div className="pointer-events-none absolute bottom-full right-0 z-30 mb-2 w-64 translate-y-1 rounded-xl border border-[#dbe7ff] bg-white/95 p-3 text-left text-[11px] leading-relaxed text-[#5f6b7a] opacity-0 shadow-[0_12px_30px_rgba(35,131,226,0.14)] backdrop-blur-sm transition-all duration-200 group-hover/action-guide:pointer-events-auto group-hover/action-guide:translate-y-0 group-hover/action-guide:opacity-100 group-focus-within/action-guide:pointer-events-auto group-focus-within/action-guide:translate-y-0 group-focus-within/action-guide:opacity-100">
                <div className="text-[10px] font-black uppercase tracking-widest text-[#2383e2]">功能说明</div>
                <div className="mt-2 space-y-1.5">
                    <p><span className="font-semibold text-[#37352f]">想看图：</span>选“查看关系图”</p>
                    <p><span className="font-semibold text-[#37352f]">想看整体网络：</span>选“进入规则网络”</p>
                    <p><span className="font-semibold text-[#37352f]">想直接分享：</span>选“复制摘要和链接”</p>
                </div>
            </div>
        </div>
    );
}

function QuickActionButton({ icon: Icon, label, onClick, accentClassName }: QuickActionButtonProps) {
    return (
        <button
            type="button"
            onClick={onClick}
            aria-label={label}
            title={label}
            className={cn(
                "group/quick relative inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/80 bg-white/92 shadow-sm transition-all duration-200 ease-out hover:-translate-y-0.5 hover:scale-[1.03] active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/30 max-[420px]:h-7 max-[420px]:w-7",
                accentClassName
            )}
        >
            <Icon size={13} />
            <span className="pointer-events-none absolute left-1/2 top-0 z-20 -translate-x-1/2 -translate-y-[calc(100%+8px)] scale-95 whitespace-nowrap rounded-md bg-[#111827] px-2 py-1 text-[10px] font-semibold text-white opacity-0 shadow-lg transition-all duration-200 ease-out group-hover/quick:scale-100 group-hover/quick:opacity-100 group-hover/quick:translate-y-[calc(-100%-10px)] group-focus-visible/quick:scale-100 group-focus-visible/quick:opacity-100 group-focus-visible/quick:translate-y-[calc(-100%-10px)]">
                {label}
            </span>
        </button>
    );
}

export default function AnalysisResult() {
    const { toast, confirm } = useToast();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const taskId = searchParams.get('task_id');
    const focusRuleKey = searchParams.get('focus_rule');
    const [task, setTask] = useState<Task | null>(null);
    const [statusError, setStatusError] = useState('');
    const [logs, setLogs] = useState<string[]>([]);
    const logEndRef = useRef<HTMLDivElement>(null);
    const logsLengthRef = useRef(0); // 避免闭包陷阱

    const [currentPage, setCurrentPage] = useState(0);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortConfig, setSortConfig] = useState<RuleSortConfig>({ key: 'lift', direction: 'desc' });
    const rowsPerPage = 12;

    const [aiAnalysis, setAiAnalysis] = useState<string>('');
    const [aiLoading, setAiLoading] = useState(false);
    const [aiExpanded, setAiExpanded] = useState(false);
    const [aiAvailable, setAiAvailable] = useState(false);
    const [aiLastUpdated, setAiLastUpdated] = useState('');
    const [aiCopied, setAiCopied] = useState(false);
    const [stopping, setStopping] = useState(false);
    const [activeFocusedRuleKey, setActiveFocusedRuleKey] = useState('');
    const [lastTaskSnapshot, setLastTaskSnapshot] = useState<Task | null>(null);
    const ruleRowRefs = useRef<Record<string, HTMLTableRowElement | null>>({});
    const ruleCardRefs = useRef<Record<string, HTMLDivElement | null>>({});

    // 检查 AI 服务可用性
    useAbortEffect((signal) => {
        aiService.checkStatus(signal)
            .then(res => setAiAvailable(res.available))
            .catch(() => setAiAvailable(false));
    }, []);

    // 轮询任务状态 —— 任务完成/失败/停止后自动停止
    const taskRef = useRef<Task | null>(null);
    const fetchAttemptRef = useRef(0);
    const fetchStatus = useCallback(async (signal?: AbortSignal) => {
        if (!taskId) return;
        try {
            const res = await algorithmService.getTaskStatus(taskId, signal);
            fetchAttemptRef.current = 0;
            setStatusError('');
            setTask(res);
            taskRef.current = res;
            const nextLogs = Array.isArray(res.logs) ? res.logs : [];
            setLogs(nextLogs);
            logsLengthRef.current = nextLogs.length;
        } catch (e) {
            fetchAttemptRef.current += 1;
            const msg = extractErrorMessage(e, '任务状态读取失败');
            // 首次加载时后端可能还未就绪，至少失败 2 次才显示错误界面，避免短暂闪现
            if (fetchAttemptRef.current >= 2) {
                setStatusError(msg);
            }
            if (msg.includes('任务不存在')) {
                try {
                    localStorage.removeItem(LAST_TASK_ID_STORAGE_KEY);
                } catch {
                    // ignore
                }
            }
        }
    }, [taskId]);

    useEffect(() => {
        if (!taskId) return;
        try {
            localStorage.setItem(LAST_TASK_ID_STORAGE_KEY, taskId);
        } catch {
            // ignore
        }
    }, [taskId]);

    useEffect(() => {
        if (!taskId) return;

        setTask(null);
        setLogs([]);
        setStatusError('');
        logsLengthRef.current = 0;
        taskRef.current = null;
        fetchAttemptRef.current = 0;

        const controller = new AbortController();
        let disposed = false;
        let timer: number | null = null;

        const poll = async () => {
            await fetchStatus(controller.signal);
            if (disposed) return;

            const s = taskRef.current?.status;
            if (s === 'completed' || s === 'failed' || s === 'stopped' || s === 'cancelled') {
                return;
            }

            timer = window.setTimeout(poll, 1500);
        };

        void poll();

        return () => {
            disposed = true;
            if (timer !== null) {
                window.clearTimeout(timer);
            }
            controller.abort();
        };
    }, [taskId, fetchStatus]);

    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    useEffect(() => {
        setAiAnalysis('');
        setAiExpanded(false);
        setAiLastUpdated('');
        setAiCopied(false);
    }, [taskId]);

    useEffect(() => {
        const storedAnalysis = task?.result?.ai_analysis;
        if (storedAnalysis) {
            setAiAnalysis(storedAnalysis);
            setAiLastUpdated(
                task?.result?.ai_analysis_updated_at
                    ? new Date(task.result.ai_analysis_updated_at).toLocaleString('zh-CN', { hour12: false })
                    : ''
            );
        }
    }, [task?.result?.ai_analysis, task?.result?.ai_analysis_updated_at]);

    useEffect(() => {
        if (!task || (task.status !== 'cancelled' && task.status !== 'stopped')) return;
        const timer = window.setTimeout(() => {
            navigate('/history', { replace: true });
        }, 1000);  // 缩短到 1s，让用户更快看到历史里的已取消状态
        return () => window.clearTimeout(timer);
    }, [task, navigate]);

    const handleAction = async (action: 'stop' | 'pause' | 'resume') => {
        try {
            if (!taskId) return;
            if (action === 'stop') {
                const ok = await confirm('确定要终止当前任务吗？终止后本次计算结果不会继续生成。');
                if (!ok) return;
                setStopping(true);
                setTask(prev => prev ? {
                    ...prev,
                    status: 'cancelled',
                    logs: [...prev.logs, `[${new Date().toLocaleTimeString('zh-CN', { hour12: false })}] 已发送终止指令，正在等待引擎停止...`]
                } : prev);
            }
            await algorithmService.controlTask(action, taskId);
            await fetchStatus();
            if (action === 'stop') {
                toast.info('终止指令已下达，正在刷新任务状态...');
            }
        } catch (e) {
            toast.error(extractErrorMessage(e, '任务控制失败'));
        } finally {
            if (action === 'stop') setStopping(false);
        }
    };

    // 如果没有 task_id，仅查询最近任务用于提示，不再自动跳转，避免页面状态乱跳
    const [autoLoading, setAutoLoading] = useState(false);
    useAbortEffect((signal) => {
        if (taskId) return;
        setAutoLoading(true);
        algorithmService.getLastTask(signal)
            .then(res => {
                setLastTaskSnapshot(res.success ? (res.task ?? null) : null);
            })
            .catch(() => {})
            .finally(() => setAutoLoading(false));
    }, [taskId]);

    const results = task?.result;
    const rules = results?.rules ?? [];
    const miningDiagnostics = results?.mining_diagnostics;
    const miningWarnings = results?.warnings ?? [];
    const fallbackAttempts = results?.fallback_attempts ?? [];
    const selectedAttempt = results?.selected_attempt;
    const readinessLevel = miningDiagnostics?.readiness_level ?? results?.summary?.readiness_level ?? 'poor';
    const readinessScore = miningDiagnostics?.readiness_score ?? results?.summary?.readiness_score ?? 0;
    const adaptiveUsed = Boolean(results?.summary?.adaptive_mode_used || (selectedAttempt && selectedAttempt.strategy !== 'initial'));
    const selectedColumnsCount = miningDiagnostics?.candidate_overview?.selected_count
        ?? miningDiagnostics?.selected_columns?.length
        ?? 0;
    const excludedColumnsCount = miningDiagnostics?.candidate_overview?.excluded_count
        ?? miningDiagnostics?.excluded_columns?.length
        ?? 0;
    const readinessStyle = getMiningReadinessStyle(readinessLevel);
    const readinessNoticeTone = readinessLevel === 'good'
        ? {
            container: 'border-emerald-200/80 bg-emerald-50/95 text-emerald-900',
            icon: 'border-emerald-200 text-emerald-600',
            badge: 'border-emerald-200/80 bg-white/80 text-emerald-700',
            subCard: 'border-emerald-200/70 bg-white/65 text-emerald-900',
            muted: 'text-emerald-800/80',
        }
        : readinessLevel === 'limited'
            ? {
                container: 'border-sky-200/80 bg-sky-50/95 text-sky-900',
                icon: 'border-sky-200 text-sky-600',
                badge: 'border-sky-200/80 bg-white/80 text-sky-700',
                subCard: 'border-sky-200/70 bg-white/65 text-sky-900',
                muted: 'text-sky-900/75',
            }
            : readinessLevel === 'weak'
                ? {
                    container: 'border-amber-200/80 bg-amber-50/95 text-amber-900',
                    icon: 'border-amber-200 text-amber-600',
                    badge: 'border-amber-200/80 bg-white/80 text-amber-700',
                    subCard: 'border-amber-200/70 bg-white/65 text-amber-900',
                    muted: 'text-amber-900/75',
                }
                : {
                    container: 'border-rose-200/80 bg-rose-50/95 text-rose-900',
                    icon: 'border-rose-200 text-rose-600',
                    badge: 'border-rose-200/80 bg-white/80 text-rose-700',
                    subCard: 'border-rose-200/70 bg-white/65 text-rose-900',
                    muted: 'text-rose-900/75',
                };

    const filteredRules = rules.filter((rule) =>
        rule.antecedents.join(' ').toLowerCase().includes(searchTerm.toLowerCase()) ||
        rule.consequents.join(' ').toLowerCase().includes(searchTerm.toLowerCase())
    );

    const sortedRules = [...filteredRules].sort((a, b) => {
        const aVal = getRuleMetric(a, sortConfig.key);
        const bVal = getRuleMetric(b, sortConfig.key);
        if (sortConfig.direction === 'asc') return aVal - bVal;
        return bVal - aVal;
    });

    const paginatedRules = sortedRules.slice(currentPage * rowsPerPage, (currentPage + 1) * rowsPerPage);

    const getRuleKey = (rule: AssociationRule) => `${rule.antecedents.join('__')}=>${rule.consequents.join('__')}`;
    const getRuleSummary = (rule: AssociationRule) => `${rule.antecedents.join(' & ')} → ${rule.consequents.join(' & ')}`;
    const focusedReturnRule = focusRuleKey
        ? (rules.find(rule => getRuleKey(rule) === focusRuleKey) ?? null)
        : null;

    const buildVisualizationUrl = (rule: AssociationRule, mode: 'auto' | 'network' = 'auto') => {
        const params = new URLSearchParams();
        const ruleKey = getRuleKey(rule);
        if (taskId) params.set('task_id', taskId);
        params.set('source_rule_key', ruleKey);
        params.set('source_rule', getRuleSummary(rule));
        if (mode === 'network') {
            params.set('preset', 'rule_network');
            params.set('auto', '1');
            return `/visualization?${params.toString()}`;
        }

        const xCol = rule.antecedents[0] ?? '';
        const yCol = rule.consequents[0] ?? rule.antecedents[1] ?? '';
        params.set('preset', 'rule_auto');
        params.set('auto', '1');
        if (xCol) params.set('x', xCol);
        if (yCol) params.set('y', yCol);
        return `/visualization?${params.toString()}`;
    };

    const hasRulePair = (rule: AssociationRule) => Boolean(rule.antecedents[0] && (rule.consequents[0] || rule.antecedents[1]));

    useEffect(() => {
        if (!focusRuleKey || !sortedRules.length) return;
        const targetIndex = sortedRules.findIndex(rule => getRuleKey(rule) === focusRuleKey);
        if (targetIndex < 0) return;

        const targetPage = Math.floor(targetIndex / rowsPerPage);
        if (currentPage !== targetPage) {
            setCurrentPage(targetPage);
        }
        setActiveFocusedRuleKey(focusRuleKey);
    }, [focusRuleKey, sortedRules, currentPage]);

    useEffect(() => {
        if (!activeFocusedRuleKey) return;
        const timer = window.setTimeout(() => {
            const row = ruleRowRefs.current[activeFocusedRuleKey];
            const card = ruleCardRefs.current[activeFocusedRuleKey];
            const target = row ?? card;
            target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 120);

        const clearTimer = window.setTimeout(() => {
            setActiveFocusedRuleKey('');
        }, 3200);

        return () => {
            window.clearTimeout(timer);
            window.clearTimeout(clearTimer);
        };
    }, [activeFocusedRuleKey, currentPage]);

    const handleSort = (key: SortKey) => {
        setSortConfig(prev => ({
            key,
            direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
        }));
        setCurrentPage(0);
    };

    if (!taskId) {
        const lastTaskStatusLabel = lastTaskSnapshot?.status === 'running' || lastTaskSnapshot?.status === 'pending'
            ? '最近任务仍在进行中'
            : lastTaskSnapshot?.status === 'completed'
                ? '最近任务已完成'
                : lastTaskSnapshot?.status === 'failed'
                    ? '最近任务执行失败'
                    : lastTaskSnapshot?.status === 'cancelled' || lastTaskSnapshot?.status === 'stopped'
                        ? '最近任务已终止'
                        : '暂无可继续的任务';
        return (
            <div className="flex flex-col items-center justify-center p-20 text-[#787774] bg-white rounded-xl border border-[#e9e9e8] shadow-sm max-w-2xl mx-auto mt-20 text-center space-y-6 animate-in fade-in slide-in-from-bottom-4">
                <div className="w-20 h-20 bg-emerald-50 rounded-full flex items-center justify-center text-emerald-500 shadow-inner">
                    {autoLoading ? <RefreshCw size={40} className="animate-spin" /> : <Activity size={40} />}
                </div>
                <div className="space-y-2">
                    <h3 className="text-xl font-black text-[#37352f]">{autoLoading ? '正在检索最近任务...' : '当前没有指定任务'}</h3>
                    {!autoLoading && (
                        <p className="text-sm max-w-sm mx-auto leading-relaxed">
                            结果页不会再自动跳转到旧任务。请手动选择最近任务或历史记录，避免“网络错误后又跳到旧任务”的混乱情况。
                        </p>
                    )}
                </div>
                {!autoLoading && lastTaskSnapshot?.task_id && (
                    <div className="w-full rounded-xl border border-[#e9e9e8] bg-[#fafafa] p-4 text-left">
                        <div className="text-[11px] font-black uppercase tracking-widest text-[#9b9a97]">最近任务</div>
                        <div className="mt-2 text-sm font-semibold text-[#37352f]">{lastTaskStatusLabel}</div>
                        <div className="mt-1 text-xs text-[#787774] break-all">UUID: {lastTaskSnapshot.task_id}</div>
                        <div className="mt-1 text-xs text-[#787774]">
                            当前进度 {Number(lastTaskSnapshot.progress ?? 0).toFixed(1)}%
                            {lastTaskSnapshot.start_time ? ` · 启动于 ${new Date(lastTaskSnapshot.start_time).toLocaleString('zh-CN', { hour12: false })}` : ''}
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                            <Button size="sm" onClick={() => navigate(`/analysis_result?task_id=${lastTaskSnapshot.task_id}`)}>
                                打开最近任务
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => navigate('/history')}>
                                去历史记录筛选状态
                            </Button>
                        </div>
                    </div>
                )}
                {!autoLoading && (
                    <div className="flex items-center gap-3">
                        <Button
                            onClick={() => navigate('/algorithm')}
                        >
                            前往算法配置 <ArrowRight size={16} />
                        </Button>
                        <Button
                            variant="outline"
                            onClick={() => navigate('/history')}
                        >
                            查看历史
                        </Button>
                    </div>
                )}
            </div>
        );
    }

    if (task && (task.status === 'cancelled' || task.status === 'stopped')) {
        return (
            <div className="max-w-2xl mx-auto mt-20 p-8 border border-amber-200 bg-amber-50 rounded-xl flex flex-col items-center">
                <StopCircle className="w-16 h-16 text-amber-500 mb-4" />
                <h2 className="text-xl font-bold text-amber-900 mb-2">任务已终止</h2>
                <p className="text-amber-800 text-sm mb-6 max-w-lg text-center">
                    当前任务已由用户终止，不会继续计算。可重新配置后发起新任务。
                </p>
                <p className="text-[12px] text-amber-700 mb-4">2 秒后将自动返回历史记录页面...</p>
                <div className="w-full bg-black/10 p-4 rounded text-xs text-amber-900 font-mono break-all">
                    {logs.slice(-3).join('\n') || '无可用日志'}
                </div>
                <div className="mt-6 flex items-center gap-3">
                    <Button variant="outline" onClick={() => navigate('/history')}>查看历史</Button>
                    <Button onClick={() => navigate('/algorithm')}>重新配置分析</Button>
                </div>
            </div>
        );
    }


    if (!task) {
        if (statusError) {
            return (
                <div className="max-w-2xl mx-auto mt-20 p-8 border border-amber-200 bg-amber-50 rounded-xl flex flex-col items-center text-center">
                    <AlertCircle className="w-12 h-12 text-amber-500 mb-3" />
                    <h2 className="text-lg font-bold text-amber-900 mb-2">任务状态不可用</h2>
                    <p className="text-amber-800 text-sm mb-5">{statusError}</p>
                    <p className="text-amber-700 text-xs mb-5">如果这是刚启动的新任务，通常刷新一次或回到历史记录重新进入即可；如果多次都失败，再按失败任务处理。</p>
                    <div className="flex items-center gap-3">
                        <Button variant="outline" onClick={() => navigate('/history')}>查看历史</Button>
                        <Button onClick={() => navigate('/algorithm')}>重新发起任务</Button>
                    </div>
                </div>
            );
        }
        return (
            <div className="flex flex-col items-center justify-center p-20 text-[#2383e2]">
                <RefreshCw className="w-8 h-8 mb-4 animate-spin" />
                <p className="font-medium animate-pulse">正在挂载后端非参数协程管线...</p>
            </div>
        );
    }

    // 阶段三：算法运行监控大屏模式 -----------------------------------------------------
    if (task.status === 'running' || task.status === 'pending') {
        const fallbackSteps = ['数据挂载校验', '增强预处理洗清', '启发式规则提取', '统计学非参检验判定', '报告序列化与清理'];
        const normalizedSteps = (task.steps && task.steps.length > 0)
            ? task.steps
            : fallbackSteps.map((name) => ({ name, status: 'pending' }));
        const steps = normalizedSteps.map((step, idx) => step.name || fallbackSteps[idx] || `阶段 ${idx + 1}`);
        const runningIdx = normalizedSteps.findIndex((step) => step.status === 'running');
        const failedIdx = normalizedSteps.findIndex((step) => step.status === 'failed');
        const cancelledIdx = normalizedSteps.findIndex((step) => step.status === 'cancelled');
        const firstPendingIdx = normalizedSteps.findIndex((step) => step.status === 'pending');
        const completedCount = normalizedSteps.filter((step) => step.status === 'completed').length;
        const currentStepIndex = runningIdx >= 0
            ? runningIdx
            : failedIdx >= 0
                ? failedIdx
                : cancelledIdx >= 0
                    ? cancelledIdx
                    : firstPendingIdx >= 0
                        ? Math.max(0, firstPendingIdx - 1)
                        : Math.max(steps.length - 1, 0);
        const hasRuntimeStepSignal = Boolean(task.steps && task.steps.length > 0);
        const segmentCount = Math.max(steps.length - 1, 1);
        const progressPercent = Math.min(100, Math.max(0, task.progress || 0));
        const railFillPercent = hasRuntimeStepSignal
            ? Math.min(100, Math.max(0, ((completedCount + (runningIdx >= 0 ? 0.35 : 0)) / segmentCount) * 100))
            : progressPercent;

        return (
        <div className="max-w-5xl mx-auto py-4 sm:py-6 px-1 sm:px-4 h-full flex flex-col">
                <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                        <div className="bg-[#2383e2]/10 p-2.5 rounded-xl text-[#2383e2] shrink-0">
                            <TerminalSquare size={24} />
                        </div>
                        <div className="min-w-0">
                            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#37352f]">算力引擎运行中</h1>
                            <p className="text-[#787774] text-xs sm:text-sm mt-0.5 break-all">UUID: <span className="font-mono">{taskId}</span></p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto">
                        <button
                            onClick={() => handleAction('stop')}
                            disabled={stopping}
                            className="w-full sm:w-auto justify-center p-2.5 border border-red-200 text-red-600 bg-red-50 hover:bg-red-100 rounded text-sm transition-colors flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
                            title="强行终止销毁作业"
                        >
                            <StopCircle size={16} /> {stopping ? '终止中...' : '终止任务'}
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-6 mb-5 sm:mb-6">
                    {/* 指标监控卡片 */}
                    <div className="notion-card p-5 border-[#e9e9e8] bg-white flex flex-col justify-center relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-16 h-16 bg-[#2383e2]/5 rounded-bl-full pointer-events-none" />
                        <p className="text-xs text-[#787774] font-medium mb-1">系统作业进度占比</p>
                        <div className="flex items-end gap-2">
                            <span className="text-2xl sm:text-3xl font-bold font-mono text-[#2383e2]">{(task.progress || 0).toFixed(1)}%</span>
                        </div>
                    </div>
                    <div className="notion-card p-5 border-[#e9e9e8] bg-white flex flex-col justify-center">
                        <p className="text-xs text-[#787774] font-medium mb-1 flex items-center gap-1"><Clock size={12} /> 预测生命周期倒计时</p>
                        <span className="text-2xl sm:text-3xl font-bold font-mono text-[#37352f]">{task.eta_seconds ? `${task.eta_seconds}s` : '计算中...'}</span>
                    </div>
                    <div className="notion-card p-5 border-[#e9e9e8] bg-white flex flex-col justify-center">
                        <p className="text-xs text-[#787774] font-medium mb-1">节点内存占用水位</p>
                        <span className="text-2xl sm:text-3xl font-bold font-mono text-[#ea5b5c]">
                            {task.memory_usage !== undefined ? `${task.memory_usage.toFixed(1)} MB` : '—'}
                        </span>
                    </div>
                </div>

                {/* 阶段穿梭轨道 */}
                <div className="notion-card p-4 sm:p-6 bg-white border border-[#e9e9e8] mb-6 shadow-sm">
                    <h3 className="text-sm font-bold text-[#37352f] mb-4 sm:mb-6 flex items-center gap-2">执行拓扑管线阶段</h3>
                    <div className="overflow-x-auto pb-2 custom-scrollbar">
                    <div className="flex items-center justify-between relative px-2 min-w-[360px] sm:min-w-[480px]">
                        <div className="absolute left-[3%] right-[3%] top-1/2 -translate-y-1/2 h-1 bg-[#efefee] -z-10 rounded-full"></div>
                        <div className="absolute left-[3%] top-1/2 -translate-y-1/2 h-1 bg-[#2383e2] -z-10 rounded-full transition-all duration-500" style={{ width: `${railFillPercent}%` }}></div>

                        {steps.map((step, idx) => (
                            <div key={idx} className="flex flex-col items-center gap-2 sm:gap-3 w-20 sm:w-32 relative">
                                {(() => {
                                    const stepStatus = normalizedSteps[idx]?.status
                                        ?? (idx < currentStepIndex ? 'completed' : idx === currentStepIndex ? 'running' : 'pending');
                                    const nodeClass = stepStatus === 'completed'
                                        ? "bg-[#2383e2] text-white border-2 border-transparent scale-100"
                                        : stepStatus === 'running'
                                            ? "bg-white text-[#2383e2] border-[3px] border-[#2383e2] scale-110 shadow-[0_0_15px_rgba(35,131,226,0.3)]"
                                            : stepStatus === 'failed' || stepStatus === 'cancelled'
                                                ? "bg-white text-red-500 border-[3px] border-red-400 scale-105 shadow-[0_0_12px_rgba(239,68,68,0.2)]"
                                                : "bg-white text-[#d3d3d3] border-2 border-[#e9e9e8] scale-100";
                                    const labelClass = stepStatus === 'completed'
                                        ? "text-[#37352f] opacity-80"
                                        : stepStatus === 'running'
                                            ? "text-[#2383e2] font-semibold"
                                            : stepStatus === 'failed' || stepStatus === 'cancelled'
                                                ? "text-red-500 font-semibold"
                                                : "text-[#d3d3d3]";
                                    return (
                                        <>
                                <div className={cn(
                                    "w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300 font-mono text-xs sm:text-sm shadow",
                                    nodeClass
                                ) + " text-[11px] sm:text-xs leading-relaxed"}>
                                    {stepStatus === 'completed' ? <CheckCircle2 size={16} /> : (idx + 1)}
                                </div>
                                <span className={cn(
                                    "text-[10px] sm:text-xs text-center transition-colors font-medium leading-snug",
                                    labelClass
                                )}>{step}</span>
                                        </>
                                    );
                                })()}
                            </div>
                        ))}
                    </div>
                    </div>
                </div>

                {/* 黑客骇客终端打字机日志输出区 */}
                <div className="notion-card border-[#e9e9e8] bg-[#0d1117] flex-1 flex flex-col min-h-[220px] sm:min-h-[250px] overflow-hidden shadow-inner font-mono text-xs text-[#b3b1b5]">
                    <div className="bg-[#161b22] px-3 sm:px-4 py-2 border-b border-[#30363d] flex flex-wrap justify-between items-center gap-2 text-[#787774] shrink-0 shadow-sm">
                        <div className="flex items-center gap-3 min-w-0">
                            <span className="flex items-center gap-1.5 min-w-0 truncate"><div className="w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse shrink-0" /> 系统标准输出日志 (STD_OUT)</span>
                        </div>
                        <div className="flex gap-1.5">
                            <div className="w-3 h-3 rounded-full bg-[#ff5f56]" />
                            <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
                            <div className="w-3 h-3 rounded-full bg-[#27c93f]" />
                        </div>
                    </div>
                    <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-1.5 max-h-[320px] sm:max-h-[400px] custom-scrollbar">
                        {logs.map((log, idx) => (
                            <div key={idx} className="flex gap-2 sm:gap-3 hover:bg-[#161b22] px-1 rounded transition-colors break-words">
                                <span className="text-[#30363d] select-none shrink-0 w-8 sm:w-10 text-right text-[10px] sm:text-xs">{String(idx + 1).padStart(3, '0')} |</span>
                                <span className={cn(
                                    log.includes('ERROR') || log.includes('失败') ? 'text-red-400 font-medium' :
                                        log.includes('WARN') || log.includes('警告') ? 'text-yellow-400' :
                                            log.includes('SUCCESS') || log.includes('成功') ? 'text-green-400 font-medium' :
                                                log.includes('==>') ? 'text-blue-300 font-bold' : 'text-[#c9d1d9]'
                                )}>
                                    {log}
                                </span>
                            </div>
                        ))}
                        <div ref={logEndRef} className="h-4 pointer-events-none" />
                        <div className="px-1 text-[#27c93f] animate-pulse text-[11px] sm:text-xs">_ 引擎持续吞吐演算中...</div>
                    </div>
                </div>
            </div>
        );
    }

    if (task.status === 'failed') {
        return (
            <div className="max-w-2xl mx-auto mt-20 p-8 border border-red-200 bg-red-50 rounded-xl flex flex-col items-center">
                <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
                <h2 className="text-xl font-bold text-red-900 mb-2">架构算力崩溃，作业被中止</h2>
                <p className="text-red-700 text-sm mb-6 max-w-lg text-center">{task.message}</p>
                <div className="w-full bg-black/10 p-4 rounded text-xs text-red-900 font-mono break-all">{logs.slice(-3).join('\n')}</div>
                <Button variant="destructive" onClick={() => navigate('/algorithm')} className="mt-6">重新配置分析</Button>
            </div>
        );
    }

    // 第四阶段：成果展示与图表聚合分析大屏 ------------------------------------------

    const handleCopyRuleSummary = async (rule: AssociationRule) => {
        try {
            await navigator.clipboard.writeText(getRuleSummary(rule));
            toast.success('规则摘要已复制');
        } catch {
            toast.error('复制失败，请手动复制');
        }
    };

    const handleCopyVisualizationLink = async (rule: AssociationRule, mode: 'auto' | 'network' = 'auto') => {
        try {
            const relativeUrl = buildVisualizationUrl(rule, mode);
            const absoluteUrl = `${window.location.origin}${relativeUrl}`;
            await navigator.clipboard.writeText(absoluteUrl);
            toast.success(mode === 'network' ? '规则网络链接已复制' : '联动图链接已复制');
        } catch {
            toast.error('链接复制失败，请手动复制');
        }
    };

    const handleCopyRuleShare = async (rule: AssociationRule) => {
        try {
            const mode = hasRulePair(rule) ? 'auto' : 'network';
            const relativeUrl = buildVisualizationUrl(rule, mode);
            const absoluteUrl = `${window.location.origin}${relativeUrl}`;
            const shareText = `规则摘要：${getRuleSummary(rule)}\n联动链接：${absoluteUrl}`;
            await navigator.clipboard.writeText(shareText);
            toast.success('规则分享内容已复制');
        } catch {
            toast.error('分享内容复制失败，请手动复制');
        }
    };

    const handleScrollToFocusedRule = () => {
        const targetKey = focusRuleKey || activeFocusedRuleKey;
        if (!targetKey) return;
        const row = ruleRowRefs.current[targetKey];
        const card = ruleCardRefs.current[targetKey];
        const target = card ?? row;
        target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    };


    // 如果没有返回规则
    if (rules.length === 0) {
        return (
            <div className="max-w-6xl mx-auto py-16 px-4 space-y-6">
                <div className="notion-card p-8 bg-white border border-[#e9e9e8]">
                    <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-6">
                        <div className="flex items-start gap-4">
                            <div className={cn("w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 border", readinessStyle.iconWrap)}>
                                <AlertCircle className="w-7 h-7" />
                            </div>
                            <div className="space-y-3">
                                <div className="flex flex-wrap items-center gap-2">
                                    <h2 className="text-2xl font-black tracking-tight text-[#37352f]">本轮未挖掘到关联规则</h2>
                                    <span className={cn("inline-flex items-center rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-widest", readinessStyle.badge)}>
                                        {formatMiningReadinessLevel(readinessLevel)}
                                    </span>
                                </div>
                                <p className="text-sm leading-relaxed text-[#5f5e58] max-w-3xl">
                                    {miningDiagnostics?.summary ?? '当前阈值和数据重复模式不足，算法没有找到满足条件的关联规则。'}
                                </p>
                                {adaptiveUsed && selectedAttempt && (
                                    <p className="text-sm text-[#2383e2] font-medium">
                                        系统已自动尝试 {Math.max(fallbackAttempts.length, 1)} 轮策略，最终停在“{selectedAttempt.name}”。
                                    </p>
                                )}
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3 xl:min-w-[360px]">
                            <ResultMetricCard
                                label="适配度"
                                value={`${Math.round(readinessScore)} 分`}
                                hint="数据重复模式与字段条件"
                            />
                            <ResultMetricCard
                                label="候选字段"
                                value={`${selectedColumnsCount} 列`}
                                hint="当前仍可参与挖掘"
                            />
                            <ResultMetricCard
                                label="频繁单项"
                                value={`${miningDiagnostics?.transaction_summary?.frequent_single_items_at_threshold ?? 0}`}
                                hint="达到当前支持度阈值"
                            />
                            <ResultMetricCard
                                label="策略尝试"
                                value={`${Math.max(fallbackAttempts.length, 1)} 轮`}
                                hint={selectedAttempt?.name ?? '原始参数'}
                            />
                        </div>
                    </div>
                </div>

                {fallbackAttempts.length > 0 && (
                    <section className="notion-card p-6 bg-white border border-[#e9e9e8]">
                        <div className="flex items-center justify-between gap-3 flex-wrap">
                            <div>
                                <h3 className="text-sm font-black text-[#37352f]">自适应回退轨迹</h3>
                                <p className="mt-1 text-sm text-[#787774]">系统按顺序尝试不同阈值与字段组合，帮助区分“参数太严”还是“数据本身模式不足”。</p>
                            </div>
                            {selectedAttempt && (
                                <span className="inline-flex items-center rounded-full bg-[#eef6ff] px-3 py-1 text-[11px] font-black text-[#2383e2]">
                                    当前输出：{selectedAttempt.name}
                                </span>
                            )}
                        </div>

                        <div className="mt-4 grid gap-4 lg:grid-cols-3">
                            {fallbackAttempts.map((attempt) => (
                                <div
                                    key={`${attempt.name}-${attempt.strategy}`}
                                    className={cn(
                                        "rounded-2xl border px-4 py-4",
                                        attempt.selected_for_output
                                            ? "border-[#2383e2] bg-[#eef6ff]"
                                            : "border-[#eef1f4] bg-[#fafbfc]"
                                    )}
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <div className="text-sm font-black text-[#37352f]">{attempt.name}</div>
                                            <p className="mt-1 text-[12px] leading-relaxed text-[#787774]">{attempt.reason || '系统自动调整挖掘策略。'}</p>
                                        </div>
                                        {attempt.selected_for_output && (
                                            <span className="rounded-full bg-[#2383e2] px-2 py-1 text-[10px] font-black text-white">当前</span>
                                        )}
                                    </div>

                                    <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                                        <MiniStat label="规则" value={`${attempt.rules_found}`} />
                                        <MiniStat label="字段" value={`${attempt.selected_columns.length}`} />
                                        <MiniStat label="均项" value={formatCompactNumber(attempt.avg_items_per_transaction)} />
                                    </div>

                                    <div className="mt-4 text-[11px] leading-relaxed text-[#5f5e58]">
                                        {formatAttemptParams(attempt.params)}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
                    <section className="notion-card p-6 bg-white border border-[#e9e9e8]">
                        <h3 className="text-sm font-black text-[#37352f]">为什么这次没有结果</h3>
                        {miningWarnings.length ? (
                            <div className="mt-4 flex flex-wrap gap-2">
                                {miningWarnings.map((warning) => (
                                    <span
                                        key={warning}
                                        className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-[11px] font-medium text-amber-700"
                                    >
                                        {warning}
                                    </span>
                                ))}
                            </div>
                        ) : (
                            <p className="mt-4 text-sm text-[#787774]">当前没有返回额外告警，建议优先检查字段重复度与支持度阈值。</p>
                        )}

                        {excludedColumnsCount > 0 && miningDiagnostics?.excluded_columns?.length ? (
                            <div className="mt-5 rounded-2xl border border-[#eef1f4] bg-[#fafbfc] px-4 py-4">
                                <div className="text-[11px] font-black uppercase tracking-widest text-[#787774]">被自动排除的弱信号字段</div>
                                <div className="mt-3 flex flex-wrap gap-2">
                                    {miningDiagnostics.excluded_columns.slice(0, 6).map((item) => (
                                        <span
                                            key={`${item.name}-${item.reason}`}
                                            className="inline-flex items-center rounded-full border border-[#e6e9ed] bg-white px-3 py-1 text-[11px] text-[#5f5e58]"
                                        >
                                            {item.name}：{item.reason}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ) : null}
                    </section>

                    <section className="notion-card p-6 bg-white border border-[#e9e9e8]">
                        <h3 className="text-sm font-black text-[#37352f]">建议你下一步这样做</h3>
                        {miningDiagnostics?.suggestions?.length ? (
                            <div className="mt-4 space-y-3">
                                {miningDiagnostics.suggestions.map((suggestion) => (
                                    <div key={suggestion} className="flex items-start gap-2 text-sm text-[#4f4e49] leading-relaxed">
                                        <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[#2383e2] shrink-0" />
                                        <span>{suggestion}</span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="mt-4 text-sm text-[#787774]">建议返回算法配置页，优先降低支持度并减少高基数字段。</p>
                        )}

                        <div className="mt-6 flex flex-wrap gap-3">
                            <Button onClick={() => navigate('/algorithm')}>
                                调整参数再试
                            </Button>
                            <Button variant="outline" onClick={() => navigate('/data')}>
                                返回数据管理
                            </Button>
                        </div>
                    </section>
                </div>
            </div>
        );
    }

    // 生成“启发式专家见解”文本
    const getSmartInsight = () => {
        if (rules.length === 0) return null;
        const topRule = [...rules].sort((a, b) => b.lift - a.lift)[0];
        const significantCount = rules.filter((rule) => rule.significant).length;

        return {
            title: "启发式统计推断摘要",
            content: `系统在当前数据集下共淬炼出 ${rules.length} 条关联特征。其中 ${significantCount} 条规则在 P < ${results?.summary?.p_value_threshold || 0.05} 的水平下表现出极强的统计显著性。`,
            highlight: `核心发现：变量集 [${topRule.antecedents.join(' & ')}] 对 [${topRule.consequents.join(' & ')}] 的预测提升度高达 ${topRule.lift.toFixed(2)}，这暗示了在排除随机性干扰后，两者存在深层的非线性耦合。`
        };
    };

    const insight = getSmartInsight();
    const { radarData, maxValue } = prepareRadarData(rules);
    const significantRules = rules.filter((rule) => rule.significant);
    const significanceRate = rules.length ? Math.round((significantRules.length / rules.length) * 100) : 0;
    const bestLift = rules.length ? Math.max(...rules.map((rule) => rule.lift)) : 0;
    const pValueThreshold = results?.summary?.p_value_threshold ?? 0.05;
    const aiSections = parseAiAnalysis(aiAnalysis);
    const hasAiReport = Boolean(aiAnalysis) && !aiAnalysis.startsWith('⚠️');
    const aiInsightTitle = insight?.title ?? '启发式统计推断摘要';
    const aiInsightContent = insight?.content ?? 'AI 总览会围绕规则强度、统计显著性和后续验证路径组织核心结论。';
    const aiInsightHighlight = insight?.highlight ?? '可优先关注高提升度且具显著性支撑的规则，再结合业务语境做验证。';
    const aiOverviewStatus = aiLoading
        ? {
            label: '推理中',
            badgeClassName: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300',
            hint: '模型正在生成结构化分析',
        }
        : hasAiReport
            ? {
                label: '已生成',
                badgeClassName: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300',
                hint: aiLastUpdated || '可查看或重生成',
            }
            : aiAvailable
                ? {
                    label: '待生成',
                    badgeClassName: 'border-sky-400/20 bg-sky-400/10 text-sky-300',
                    hint: '可按需生成 AI 解读',
                }
                : {
                    label: '未配置',
                    badgeClassName: 'border-amber-400/20 bg-amber-400/10 text-amber-300',
                    hint: '当前环境未启用 AI 服务',
                };

    /**
     * 调用后端 AI 接口获取深度解读
     * 传入当前任务的规则和摘要，由 DeepSeek-V3.2 生成专业分析
     */
    const fetchAIAnalysis = async (force = false) => {
        if (!force && hasAiReport) {
            setAiExpanded(true);
            return;
        }
        setAiLoading(true);
        setAiExpanded(true);
        setAiCopied(false);
        try {
            const res = await aiService.analyzeRules({
                task_id: taskId,
                rules: rules,
                summary: results?.summary || {}
            });
            if (res.success && typeof res.analysis === 'string' && res.analysis.trim()) {
                setAiAnalysis(res.analysis.trim());
                setAiLastUpdated(new Date().toLocaleString('zh-CN', { hour12: false }));
                toast.success('AI 深度解读已生成');
            } else {
                setAiAnalysis(`⚠️ AI 分析失败：${res.error}`);
                toast.error(`AI 分析失败：${res.error || '未返回有效内容'}`);
            }
        } catch (error) {
            setAiAnalysis(`⚠️ 请求失败：${extractErrorMessage(error, 'AI 服务请求失败')}`);
            toast.error(extractErrorMessage(error, 'AI 服务请求失败'));
        } finally {
            setAiLoading(false);
        }
    };

    const handleCopyAIAnalysis = async () => {
        if (!aiAnalysis) return;

        try {
            await navigator.clipboard.writeText(aiAnalysis);
            setAiCopied(true);
            toast.success('AI 解读内容已复制');
            window.setTimeout(() => setAiCopied(false), 1800);
        } catch {
            toast.error('复制失败，请手动选择文本');
        }
    };

    return (
        <div className="max-w-7xl mx-auto py-8 px-4 h-full overflow-y-auto">
            {/* 智能见解组件 - 浮动入场 */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-8 p-6 bg-gradient-to-r from-[#37352f] to-[#25242a] rounded-2xl text-white shadow-xl relative overflow-hidden"
            >
                <div className="absolute top-0 right-0 p-8 opacity-10 rotate-12">
                    <Brain size={120} />
                </div>
                <div className="relative z-10 flex flex-col gap-6">
                    <div className="flex flex-col xl:flex-row gap-6 xl:items-start">
                        <div className="flex-1">
                            <div className="rounded-2xl border border-white/10 bg-black/10 p-5">
                                <div className="flex items-start gap-4">
                                <div className="bg-emerald-400/20 p-4 rounded-2xl border border-emerald-400/30 shrink-0">
                                    <Sparkles className="text-emerald-400 w-8 h-8" />
                                </div>
                                <div className="flex-1">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <span className="inline-flex items-center rounded-full border border-white/10 bg-white/10 px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.2em] text-gray-300">
                                            ai overview
                                        </span>
                                        <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-black", aiOverviewStatus.badgeClassName)}>
                                            {aiOverviewStatus.label}
                                        </span>
                                        <span className="inline-flex items-center rounded-full border border-white/10 bg-white/10 px-2 py-0.5 text-[10px] font-black text-gray-300">
                                            Rules + Stats
                                        </span>
                                    </div>
                                    <h2 className="mt-3 text-2xl font-black tracking-tight text-white">
                                        {aiInsightTitle}
                                    </h2>
                                    <p className="mt-2 text-sm leading-relaxed text-gray-300/90">{aiInsightContent}</p>
                                    <div className="mt-3 rounded-xl border border-white/10 bg-white/5 px-3 py-3">
                                        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-emerald-300">
                                            <Zap size={12} />
                                            关键提示
                                        </div>
                                        <div className="mt-1 text-[12px] leading-relaxed text-emerald-200/90">
                                            {aiInsightHighlight}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            </div>

                            <div className="mt-4 grid grid-cols-2 xl:grid-cols-4 gap-3">
                                {[
                                    { label: '规则总数', value: `${rules.length}`, hint: '进入 AI 解读的样本池' },
                                    { label: '显著规则占比', value: `${significanceRate}%`, hint: `阈值 α = ${pValueThreshold}` },
                                    { label: '最高提升度', value: bestLift.toFixed(2), hint: '优先识别高价值规则' },
                                    { label: '当前状态', value: aiOverviewStatus.label, hint: aiOverviewStatus.hint }
                                ].map((item) => (
                                    <div key={item.label} className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3">
                                        <div className="text-[10px] uppercase tracking-widest text-gray-400 font-black">{item.label}</div>
                                        {item.label === '当前状态' ? (
                                            <div className="mt-2">
                                                <span className={cn("inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-black", aiOverviewStatus.badgeClassName)}>
                                                    {item.value}
                                                </span>
                                            </div>
                                        ) : (
                                            <div className="mt-1 text-xl font-black text-white">{item.value}</div>
                                        )}
                                        <div className="mt-1 text-[10px] text-gray-400 leading-relaxed">{item.hint}</div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="w-full xl:w-[250px] shrink-0 rounded-2xl border border-white/10 bg-white/5 p-4">
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="inline-flex items-center rounded-full border border-white/10 bg-white/10 px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.2em] text-gray-300">
                                    system notice
                                </span>
                                <span className="inline-flex items-center rounded-full border border-white/10 bg-white/10 px-2 py-0.5 text-[10px] font-black text-emerald-300">
                                    AI 工作台
                                </span>
                            </div>
                            <div className="mt-2 text-sm font-black text-white">结构化分析输出</div>
                            <div className="mt-1 text-[11px] text-gray-400 leading-relaxed">
                                输出会按“总体判断 / 高价值规则 / 统计校验 / 风险与限制 / 建议动作 / 后续验证”六段组织。
                            </div>

                            <div className="mt-4 flex flex-col gap-2">
                                {aiAvailable ? (
                                    <>
                                        <Button
                                            onClick={() => fetchAIAnalysis(Boolean(aiAnalysis))}
                                            disabled={aiLoading}
                                            className="w-full bg-emerald-500 hover:bg-emerald-600 text-white"
                                        >
                                            {aiLoading ? <Loader2 size={14} className="animate-spin" /> : (hasAiReport ? <RotateCcw size={14} /> : <MessageSquare size={14} />)}
                                            {aiLoading ? 'AI 推理中...' : (hasAiReport ? '重新生成解读' : 'AI 深度解读')}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => setAiExpanded((prev) => !prev)}
                                            className="w-full border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white"
                                        >
                                            {aiExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                            {aiExpanded ? '收起分析面板' : '展开分析面板'}
                                        </Button>
                                        {hasAiReport && (
                                            <Button
                                                variant="outline"
                                                onClick={handleCopyAIAnalysis}
                                                className="w-full border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white"
                                            >
                                                <Copy size={14} />
                                                {aiCopied ? '已复制内容' : '复制分析文本'}
                                            </Button>
                                        )}
                                    </>
                                ) : (
                                    <div className="rounded-xl border border-amber-400/20 bg-amber-400/10 px-3 py-3 text-amber-100">
                                        <div className="flex items-start gap-3">
                                            <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-amber-300/30 bg-white/10 text-amber-200 shadow-sm">
                                                <AlertCircle size={14} />
                                            </div>
                                            <div className="min-w-0 flex-1">
                                                <div className="flex flex-wrap items-center gap-2">
                                                    <span className="inline-flex items-center rounded-full border border-amber-300/20 bg-white/10 px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.2em] text-amber-100">
                                                        system notice
                                                    </span>
                                                    <span className="inline-flex items-center rounded-full border border-amber-300/20 bg-white/10 px-2 py-0.5 text-[10px] font-black text-amber-100">
                                                        服务未就绪
                                                    </span>
                                                </div>
                                                <div className="mt-1 text-[12px] font-bold text-amber-50">当前未检测到 AI 服务配置</div>
                                                <div className="mt-1 text-[11px] leading-relaxed text-amber-100/85">
                                                    结果页仍可查看规则、图表与统计指标，但不会生成自动解读。
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* AI 深度解读展开区域 */}
                    <AnimatePresence>
                        {aiExpanded && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                className="overflow-hidden"
                            >
                                <div className="mt-2 pt-4 border-t border-white/10">
                                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <Brain size={16} className="text-emerald-400" />
                                                <span className="text-sm font-black text-emerald-400">DeepSeek-V3.2 深度解析报告</span>
                                                <span className="text-[9px] bg-white/10 px-2 py-0.5 rounded-full text-gray-400">华为云 ModelArts MaaS</span>
                                            </div>
                                            <div className="mt-1 text-[11px] text-gray-400">
                                                {hasAiReport
                                                    ? `最近生成：${aiLastUpdated || '刚刚'} · 基于 ${rules.length} 条规则与统计证据`
                                                    : '将基于规则强度、显著性阈值和统计检验结果生成结构化说明'}
                                            </div>
                                        </div>
                                        {hasAiReport && (
                                            <div className="flex flex-wrap gap-2">
                                                <span className="rounded-full bg-white/5 border border-white/10 px-3 py-1 text-[10px] text-gray-300">
                                                    {aiSections.length || 1} 个主题分段
                                                </span>
                                                <span className="rounded-full bg-white/5 border border-white/10 px-3 py-1 text-[10px] text-gray-300">
                                                    显著规则 {significantRules.length} 条
                                                </span>
                                            </div>
                                        )}
                                    </div>

                                    {aiLoading ? (
                                        <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/5 px-4 py-5">
                                            <div className="flex items-start gap-3">
                                                <div className="relative mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-emerald-400/20 bg-white/5 text-emerald-300 shadow-sm">
                                                    <Loader2 size={16} className="animate-spin" />
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <div className="flex flex-wrap items-center gap-2">
                                                        <span className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.2em] text-gray-300">
                                                            system notice
                                                        </span>
                                                        <span className="inline-flex items-center rounded-full border border-emerald-400/20 bg-white/5 px-2 py-0.5 text-[10px] font-black text-emerald-300">
                                                            推理进行中
                                                        </span>
                                                    </div>
                                                    <div className="mt-1 text-sm font-bold text-emerald-200">大模型正在深度推理中</div>
                                                    <div className="mt-1 text-[11px] leading-relaxed text-gray-400">
                                                        正在综合规则强度、统计检验和风险提示，生成可直接展示的结构化结论。
                                                    </div>
                                                    <div className="mt-3 rounded-xl border border-white/10 bg-white/5 px-3 py-3">
                                                        <div className="flex flex-wrap gap-2 text-[10px] text-gray-300">
                                                            <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
                                                                <Clock size={10} />
                                                                整体判断
                                                            </span>
                                                            <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
                                                                <Sparkles size={10} />
                                                                统计校验
                                                            </span>
                                                            <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
                                                                <Zap size={10} />
                                                                建议动作
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ) : hasAiReport ? (
                                        <div className="grid gap-3 md:grid-cols-2">
                                            {aiSections.map((section) => {
                                                const style = getAiSectionStyle(section.title);
                                                return (
                                                    <section
                                                        key={section.title}
                                                        className={cn(
                                                            "rounded-2xl border px-4 py-4",
                                                            style.container
                                                        )}
                                                    >
                                                        <div className="flex items-center gap-2 mb-3">
                                                            <span className={cn("w-2 h-2 rounded-full", style.dot)} />
                                                            <h4 className="text-sm font-black text-white">{section.title}</h4>
                                                        </div>
                                                        <div className="space-y-3 text-[13px] leading-[1.8]">
                                                            {section.blocks.map((block, index) => {
                                                                if (block.type === 'subheading') {
                                                                    return (
                                                                        <h5 key={`${section.title}-${index}`} className="text-[11px] uppercase tracking-widest text-gray-400 font-black">
                                                                            {block.content}
                                                                        </h5>
                                                                    );
                                                                }

                                                                if (block.type === 'bullet') {
                                                                    return (
                                                                        <div key={`${section.title}-${index}`} className="flex items-start gap-2.5 text-gray-200">
                                                                            <span className={cn("w-1.5 h-1.5 rounded-full mt-[9px] shrink-0", style.dot)} />
                                                                            <span dangerouslySetInnerHTML={{ __html: formatAiInline(block.content) }} />
                                                                        </div>
                                                                    );
                                                                }

                                                                if (block.type === 'ordered') {
                                                                    return (
                                                                        <div key={`${section.title}-${index}`} className="flex items-start gap-2.5 text-gray-200">
                                                                            <span className={cn("w-5 h-5 rounded-md flex items-center justify-center shrink-0 mt-0.5 text-[10px] font-black", style.badge)}>
                                                                                {block.order}
                                                                            </span>
                                                                            <span dangerouslySetInnerHTML={{ __html: formatAiInline(block.content) }} />
                                                                        </div>
                                                                    );
                                                                }

                                                                return (
                                                                    <p
                                                                        key={`${section.title}-${index}`}
                                                                        className="text-gray-300"
                                                                        dangerouslySetInnerHTML={{ __html: formatAiInline(block.content) }}
                                                                    />
                                                                );
                                                            })}
                                                        </div>
                                                    </section>
                                                );
                                            })}
                                        </div>
                                    ) : aiAnalysis ? (
                                        <div className="rounded-2xl border border-red-400/20 bg-red-400/10 px-4 py-4 text-sm text-red-100 leading-relaxed">
                                            {aiAnalysis.replace(/^⚠️\s*/, '')}
                                        </div>
                                    ) : (
                                        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                                            <div className="flex items-start gap-3">
                                                <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-cyan-300 shadow-sm">
                                                    <MessageSquare size={16} />
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <div className="flex flex-wrap items-center gap-2">
                                                        <span className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.2em] text-gray-300">
                                                            system notice
                                                        </span>
                                                        <span className="inline-flex items-center rounded-full border border-cyan-400/20 bg-white/5 px-2 py-0.5 text-[10px] font-black text-cyan-300">
                                                            待生成
                                                        </span>
                                                    </div>
                                                    <div className="mt-1 text-sm font-bold text-white">AI 分析尚未生成</div>
                                                    <div className="mt-1 text-[12px] leading-relaxed text-gray-400">
                                                        启动后会输出面向展示与决策的结构化说明，帮助你更快理解当前规则集是否可靠、可用、该先验证什么。
                                                    </div>
                                                    <div className="mt-3 grid gap-3 md:grid-cols-3">
                                                        {[
                                                            { title: '总体判断', desc: '先回答这组规则值不值得信、值不值得用。' },
                                                            { title: '统计校验', desc: '明确哪些结论有显著性支撑，哪些只适合探索参考。' },
                                                            { title: '建议动作', desc: '给出优先验证路径，避免直接过度解读结果。' }
                                                        ].map((item) => (
                                                            <div key={item.title} className="rounded-xl border border-white/10 bg-white/5 px-3 py-3">
                                                                <div className="text-[11px] font-black uppercase tracking-widest text-gray-300">{item.title}</div>
                                                                <div className="mt-1 text-[12px] leading-relaxed text-gray-400">{item.desc}</div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </motion.div>
            {/* 顶栏信息 */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 sm:mb-8 pb-5 sm:pb-6 border-b border-[#e9e9e8] gap-4">
                <div className="flex items-center gap-3 sm:gap-4">
                    <div className="bg-emerald-50 p-2 sm:p-2.5 rounded-xl text-emerald-600 border border-emerald-100 shadow-sm shrink-0">
                        <CheckCircle2 size={24} />
                    </div>
                    <div>
                        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#37352f]">分析结果</h1>
                        <div className="flex flex-wrap items-center gap-2 sm:gap-4 mt-1 text-xs sm:text-sm text-[#787774]">
                            <span className="flex items-center gap-1"><Layers size={12} /> {rules.length} 条关联结构</span>
                            <span className="flex items-center gap-1"><CheckCircle2 size={12} /> {significanceRate}% 显著规则</span>
                        </div>
                    </div>
                </div>
                <div className="flex flex-wrap gap-2">
                    <Button variant="outline" size="sm" onClick={() => navigate('/visualization?preset=rule_network&auto=1')}>
                        <BarChart3 size={14} /> 规则网络
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => navigate('/visualization?preset=correlation_overview')}>
                        <BarChart3 size={14} /> 可视化
                    </Button>
                    <Button size="sm" onClick={() => navigate('/report')}>
                        <FileCode size={14} />
                        生成报告
                    </Button>
                </div>
            </div>

            {focusedReturnRule && (
                <div className="mb-6 rounded-xl border border-blue-100 bg-gradient-to-r from-blue-50 to-indigo-50 px-4 py-3 text-sm text-[#4f4e49] shadow-sm">
                    <div className="flex items-start gap-3">
                        <div className="mt-0.5 rounded-lg border border-blue-100 bg-white p-2 text-[#2383e2]">
                            <RotateCcw size={16} />
                        </div>
                        <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="text-[11px] font-black uppercase tracking-widest text-[#2383e2]">系统关系提示</span>
                                <span className="inline-flex items-center rounded-full bg-[#eef6ff] px-2 py-0.5 text-[10px] font-black text-[#2383e2]">
                                    联动返回
                                </span>
                            </div>
                            <div className="mt-1 font-medium break-words">{getRuleSummary(focusedReturnRule)}</div>
                            <div className="mt-1 text-xs text-[#787774]">
                                你正从可视化页返回，系统已自动定位并高亮对应规则，方便继续核对证据、复制链接或切换下一步浏览动作。
                            </div>
                            <div className="mt-3 flex flex-wrap gap-2">
                                {hasRulePair(focusedReturnRule) && (
                                    <button
                                        type="button"
                                        onClick={() => navigate(buildVisualizationUrl(focusedReturnRule, 'auto'))}
                                    className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-[#2383e2] transition-all hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]"
                                    >
                                        <BarChart3 size={12} />
                                        继续查看关系图
                                    </button>
                                )}
                                <button
                                    type="button"
                                    onClick={() => navigate(buildVisualizationUrl(focusedReturnRule, 'network'))}
                                    className="inline-flex items-center gap-1.5 rounded-lg border border-violet-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-violet-700 transition-all hover:bg-violet-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400/40 active:scale-[0.97]"
                                >
                                    <Activity size={12} />
                                    查看规则网络
                                </button>
                                <button
                                    type="button"
                                    onClick={handleScrollToFocusedRule}
                                    className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-indigo-600 transition-all hover:bg-indigo-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/40 active:scale-[0.97]"
                                >
                                    <RotateCcw size={12} />
                                    回到定位规则
                                </button>
                                <button
                                    type="button"
                                    onClick={() => { void handleCopyVisualizationLink(focusedReturnRule, hasRulePair(focusedReturnRule) ? 'auto' : 'network'); }}
                                    className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-emerald-600 transition-all hover:bg-emerald-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/40 active:scale-[0.97]"
                                >
                                    <Link2 size={12} />
                                    复制联动链接
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {(miningDiagnostics || miningWarnings.length > 0 || adaptiveUsed) && (
                <div className="mb-8 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
                    <section className={cn("rounded-xl border px-5 py-5 shadow-sm backdrop-blur-sm", readinessNoticeTone.container)}>
                        <div className="flex items-start gap-3">
                            <div className={cn("mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border bg-white/80 shadow-sm", readinessNoticeTone.icon)}>
                                {readinessLevel === 'good' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
                            </div>
                            <div className="min-w-0 flex-1">
                                <div className="flex flex-wrap items-center gap-2">
                                    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.2em]", readinessNoticeTone.badge)}>
                                        system notice
                                    </span>
                                    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-black", readinessNoticeTone.badge)}>
                                        适配评估
                                    </span>
                                    <span className="text-[12px] font-bold leading-none">
                                        挖掘适配度与回退说明
                                    </span>
                                </div>
                                <div className="mt-2 flex flex-wrap items-center gap-2">
                                    <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-widest", readinessStyle.badge)}>
                                        {formatMiningReadinessLevel(readinessLevel)}
                                    </span>
                                    {adaptiveUsed && selectedAttempt && (
                                        <span className="inline-flex items-center rounded-full border border-[#dbe7ff] bg-white/80 px-2.5 py-1 text-[10px] font-black text-[#2383e2]">
                                            已切换到 {selectedAttempt.name}
                                        </span>
                                    )}
                                </div>
                                <p className={cn("mt-2 text-sm leading-relaxed", readinessNoticeTone.muted)}>
                                    {miningDiagnostics?.summary ?? '系统已完成当前数据集的适配性评估。'}
                                </p>
                                {(adaptiveUsed || miningWarnings.length > 0) && (
                                    <div className={cn("mt-3 rounded-xl border px-3 py-3", readinessNoticeTone.subCard)}>
                                        {adaptiveUsed && selectedAttempt && (
                                            <div className="text-[11px] font-semibold leading-relaxed">
                                                系统已自动完成多轮参数回退，当前输出使用「{selectedAttempt.name}」作为最终结果策略。
                                            </div>
                                        )}
                                        {miningWarnings.length > 0 && (
                                            <div className={cn(adaptiveUsed ? "mt-2" : "", "flex flex-wrap gap-2")}>
                                                {miningWarnings.slice(0, 3).map((warning) => (
                                                    <span
                                                        key={warning}
                                                        className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-[11px] font-medium text-amber-700"
                                                    >
                                                        {warning}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </section>

                    <section className="rounded-2xl border border-[#e9e9e8] bg-white px-5 py-5 shadow-[0_2px_10px_rgba(0,0,0,0.02)]">
                        <div className="grid grid-cols-2 gap-3">
                            <ResultMetricCard
                                label="适配度"
                                value={`${Math.round(readinessScore)} 分`}
                                hint="规则生成前的综合评估"
                            />
                            <ResultMetricCard
                                label="有效字段"
                                value={`${selectedColumnsCount} 列`}
                                hint="最终参与挖掘"
                            />
                            <ResultMetricCard
                                label="排除字段"
                                value={`${excludedColumnsCount} 列`}
                                hint="自动识别为弱信号"
                            />
                            <ResultMetricCard
                                label="策略尝试"
                                value={`${Math.max(fallbackAttempts.length, 1)} 轮`}
                                hint={selectedAttempt?.name ?? '原始参数'}
                            />
                        </div>
                    </section>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* 雷达图总览 */}
                <div className="lg:col-span-1 border border-[#e9e9e8] bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.02)] overflow-hidden flex flex-col relative group">
                    <div className="p-5 border-b border-[#e9e9e8] bg-[#f9f9f8]">
                        <h3 className="font-bold flex items-center gap-2 text-[#37352f]">
                            <BarChart3 size={18} className="text-[#2383e2]" />
                            置信多维超平面映射
                        </h3>
                    </div>
                    <div className="flex-1 min-h-[300px] p-2 relative bg-white">
                        <ResponsiveContainer width="100%" height="100%">
                            <RadarChart cx="50%" cy="50%" outerRadius="65%" data={radarData}>
                                <PolarGrid stroke="#e9e9e8" />
                                <PolarAngleAxis dataKey="rule" tick={{ fill: '#787774', fontSize: 10, fontWeight: 500 }} />
                                <PolarRadiusAxis angle={30} domain={[0, maxValue]} tick={{ fill: '#d3d3d3', fontSize: 9 }} />
                                <Radar name="置信度 (Conf)" dataKey="confidence" stroke="#2383e2" fill="#2383e2" fillOpacity={0.25} />
                                <Radar name="提升度 (Lift)" dataKey="lift" stroke="#ea5b5c" fill="#ea5b5c" strokeDasharray="3 3" fillOpacity={0.15} />
                                <Tooltip contentStyle={{ fontSize: '11px', borderRadius: '8px', border: '1px solid #e9e9e8', boxShadow: '0 4px 15px rgba(0,0,0,0.05)' }} />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="absolute inset-0 bg-white/60 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <button onClick={() => navigate('/visualization?preset=rule_network&auto=1')} className="bg-[#2383e2] text-white px-4 py-2 rounded-lg text-sm font-medium shadow-lg hover:scale-105 transition-transform">探索规则网络图</button>
                    </div>
                </div>

                {/* 前置关联因素分析 (类似 SHAP) */}
                <div className="lg:col-span-2 notion-card p-6 border-[#e9e9e8] bg-[#fbfbfa]">
                    <h3 className="font-bold mb-6 flex items-center gap-2 text-[#37352f]">
                        <FileCode size={18} className="text-[#2383e2]" />
                        核心驱动因子权重排名 (Top Contributing Factors)
                    </h3>
                    <div className="space-y-4">
                        {rules.slice(0, 5).map((r, idx: number) => {
                            const ruleKey = getRuleKey(r);
                            const isFocused = activeFocusedRuleKey === ruleKey;
                            const quickBrowseMode = hasRulePair(r) ? 'auto' as const : 'network' as const;
                            const quickBrowseLabel = hasRulePair(r) ? '查看关系图' : '进入规则网络';
                            const QuickBrowseIcon = hasRulePair(r) ? BarChart3 : Activity;
                            return (
                            <div
                                key={idx}
                                ref={(node) => { ruleCardRefs.current[ruleKey] = node; }}
                                className={cn(
                                    "group/rule relative flex flex-col gap-2 overflow-visible rounded-xl border px-3 py-3 transition-all duration-300 ease-out",
                                    isFocused
                                        ? "border-[#bfdbfe] bg-blue-50/60 ring-2 ring-[#2383e2] ring-offset-2 shadow-[0_16px_40px_rgba(35,131,226,0.14)]"
                                        : "border-transparent bg-white/70 hover:-translate-y-0.5 hover:border-[#dbe7ff] hover:bg-white hover:shadow-[0_12px_30px_rgba(35,131,226,0.08)] focus-within:border-[#dbe7ff] focus-within:bg-white focus-within:shadow-[0_12px_30px_rgba(35,131,226,0.08)]"
                                )}
                            >
                                <div className={cn(
                                    "pointer-events-none absolute left-3 right-3 top-0 h-[3px] rounded-full bg-gradient-to-r from-[#2383e2] via-[#60a5fa] to-[#a78bfa] transition-all duration-300 ease-out",
                                    isFocused ? "opacity-100" : "opacity-0 group-hover/rule:opacity-100 group-focus-within/rule:opacity-100"
                                )} />
                                <div className={cn(
                                    "pointer-events-none absolute right-3 -top-3.5 z-10 flex max-w-[calc(100%-1.5rem)] origin-top-right items-center justify-end transition-all duration-300 ease-out",
                                    isFocused
                                        ? "translate-y-0 scale-100 opacity-100"
                                        : "scale-95 opacity-0 -translate-y-1 group-hover/rule:scale-100 group-hover/rule:opacity-100 group-hover/rule:translate-y-0 group-focus-within/rule:scale-100 group-focus-within/rule:opacity-100 group-focus-within/rule:translate-y-0"
                                )}>
                                    <div className="pointer-events-auto flex items-center gap-1 rounded-full border border-white/90 bg-white/92 px-1.5 py-1 shadow-[0_10px_28px_rgba(35,131,226,0.14)] backdrop-blur-md transition-all duration-300 ease-out group-hover/rule:shadow-[0_14px_32px_rgba(35,131,226,0.16)] group-focus-within/rule:shadow-[0_14px_32px_rgba(35,131,226,0.16)] max-[420px]:gap-0.5 max-[420px]:px-1 max-[420px]:py-0.5">
                                        <QuickActionButton
                                            icon={QuickBrowseIcon}
                                            label={quickBrowseLabel}
                                            onClick={() => navigate(buildVisualizationUrl(r, quickBrowseMode))}
                                            accentClassName={hasRulePair(r) ? "text-[#2383e2] hover:bg-[#edf5ff]" : "text-violet-700 hover:bg-violet-50"}
                                        />
                                        <QuickActionButton
                                            icon={Copy}
                                            label="复制规则摘要"
                                            onClick={() => { void handleCopyRuleSummary(r); }}
                                            accentClassName="text-emerald-700 hover:bg-emerald-50"
                                        />
                                        <QuickActionButton
                                            icon={Link2}
                                            label="复制联动链接"
                                            onClick={() => { void handleCopyVisualizationLink(r, quickBrowseMode); }}
                                            accentClassName="text-violet-700 hover:bg-violet-50"
                                        />
                                    </div>
                                </div>
                                {isFocused && (
                                    <div className="flex items-center justify-between px-0.5">
                                        <span className="inline-flex items-center rounded-full bg-[#eef6ff] px-2.5 py-1 text-[10px] font-black text-[#2383e2] shadow-sm">
                                            系统定位
                                        </span>
                                    </div>
                                )}
                                <div className="flex justify-between text-xs font-semibold px-0.5">
                                    <span className="text-[#37352f] truncate flex-1 leading-relaxed border border-gray-100 bg-white px-2 py-0.5 rounded shadow-sm mr-2" title={`${r.antecedents.join(' AND ')}  ==>  ${r.consequents.join(' AND ')}`}>
                                        <span className="text-[#ea5b5c] font-mono mx-1">if</span> {r.antecedents.join(' & ')}
                                        <span className="text-[#2383e2] font-mono mx-2">then</span> {r.consequents.join(' & ')}
                                    </span>
                                    <span className={cn(
                                        "w-24 shrink-0 rounded-lg px-2.5 py-0.5 text-right font-mono transition-all duration-300 ease-out",
                                        isFocused
                                            ? "bg-[#e8f2ff] text-[#1d4ed8] shadow-sm"
                                            : "bg-[#efefee] text-[#787774] group-hover/rule:bg-[#eef6ff] group-hover/rule:text-[#1d4ed8] group-hover/rule:shadow-sm group-focus-within/rule:bg-[#eef6ff] group-focus-within/rule:text-[#1d4ed8] group-focus-within/rule:shadow-sm"
                                    )}>
                                        Lift {r.lift.toFixed(2)}
                                    </span>
                                </div>
                                <div className={cn(
                                    "flex h-2.5 w-full items-center overflow-hidden rounded-full bg-[#efefee] shadow-inner transition-all duration-300 ease-out",
                                    isFocused ? "ring-1 ring-[#bfdbfe]" : "group-hover/rule:ring-1 group-hover/rule:ring-[#dbe7ff] group-focus-within/rule:ring-1 group-focus-within/rule:ring-[#dbe7ff]"
                                )}>
                                    <div
                                        className="relative h-full transition-all duration-700 delay-75"
                                        style={{ width: `${Math.min((r.lift / 10) * 100, 100)}%` }}
                                    >
                                        <div className="absolute inset-0 bg-gradient-to-r from-[#2383e2] to-[#40a3ff]"></div>
                                        <div className="absolute top-0 right-0 bottom-0 w-4 bg-gradient-to-l from-white/30 to-transparent"></div>
                                    </div>
                                </div>
                                <div className="flex flex-wrap items-center gap-2 pt-1">
                                    <div className="flex items-center gap-2 text-[10px] text-[#9b9a97] px-0.5">
                                        <span className="inline-flex items-center rounded-full border border-[#e8eefc] bg-[#f8fbff] px-2 py-0.5 font-bold text-[#2383e2]">
                                            <span className="max-[420px]:hidden">高频快捷 / 更多菜单</span>
                                            <span className="hidden max-[420px]:inline">快捷</span>
                                        </span>
                                    </div>
                                    <RuleActionGuide />
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <button
                                                type="button"
                                                className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-[#dbe7ff] bg-white px-3 py-1.5 text-[11px] font-semibold text-[#4f4e49] shadow-sm hover:bg-[#f8fbff] transition-colors max-[420px]:gap-1 max-[420px]:px-2.5"
                                            >
                                                <BarChart3 size={12} />
                                                <span className="max-[420px]:hidden">更多</span>
                                                <ChevronDown size={12} className="max-[420px]:hidden" />
                                            </button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="start" className="w-52">
                                            <DropdownMenuItem disabled className="text-[10px] font-black uppercase tracking-widest text-[#9b9a97] opacity-100">
                                                浏览
                                            </DropdownMenuItem>
                                            {hasRulePair(r) && (
                                                <DropdownMenuItem onClick={() => navigate(buildVisualizationUrl(r, 'auto'))}>
                                                    <BarChart3 size={14} className="text-blue-600" />
                                                    查看关系图
                                                </DropdownMenuItem>
                                            )}
                                            <DropdownMenuItem onClick={() => navigate(buildVisualizationUrl(r, 'network'))}>
                                                <BarChart3 size={14} className="text-purple-600" />
                                                进入规则网络
                                            </DropdownMenuItem>
                                            <DropdownMenuItem disabled className="text-[10px] font-black uppercase tracking-widest text-[#9b9a97] opacity-100">
                                                复制
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => { void handleCopyRuleSummary(r); }}>
                                                <Copy size={14} className="text-emerald-600" />
                                                复制规则摘要
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => { void handleCopyVisualizationLink(r, hasRulePair(r) ? 'auto' : 'network'); }}>
                                                <Link2 size={14} className="text-sky-600" />
                                                复制联动链接
                                            </DropdownMenuItem>
                                            <DropdownMenuItem disabled className="text-[10px] font-black uppercase tracking-widest text-[#9b9a97] opacity-100">
                                                分享
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => { void handleCopyRuleShare(r); }}>
                                                <Copy size={14} className="text-violet-600" />
                                                复制摘要和链接
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </div>
                            </div>
                        )})}
                        {rules.length > 5 && (
                            <div className="pt-4 text-center">
                                <button onClick={() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })} className="text-[#2383e2] text-xs font-medium hover:underline hover:underline-offset-2">查看完整底层规则列表 ↓</button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* 完整规则矩阵表格 */}
            <div className="mt-8 border border-[#e9e9e8] rounded-xl overflow-hidden bg-white shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
                <div className="flex flex-col md:flex-row items-center justify-between p-5 bg-[#fbfbfa] border-b border-[#e9e9e8] gap-4">
                    <h3 className="font-bold flex items-center gap-2 text-[#37352f] shrink-0">
                        <Layers size={18} className="text-[#787774]" />
                        优秀的关联规则深度矩阵 (Mining Matrix)
                    </h3>

                    <div className="relative w-full md:w-80">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#d3d3d3]" size={16} />
                        <input
                            type="text"
                            placeholder="全量语义检索（如输入变量名）..."
                            className="w-full bg-white border border-[#e9e9e8] pl-10 pr-4 py-2 rounded-lg text-sm outline-none focus:border-[#2383e2] focus:ring-2 focus:ring-[#2383e2]/20 shadow-inner transition-all"
                            value={searchTerm}
                            onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(0); }}
                        />
                    </div>
                </div>
                <div className="overflow-x-auto min-h-[400px]">
                    <table className="w-full text-left text-sm whitespace-nowrap">
                        <thead className="bg-[#f9f9f8] text-[#787774] font-medium border-b border-[#e9e9e8] sticky top-0 z-10">
                            <tr>
                                <th className="px-5 py-4 font-bold border-r border-[#efefee]"># 定义内容与映射路径</th>
                                <th className="px-5 py-4 w-28 text-right cursor-pointer hover:bg-[#efefee] transition-colors group" onClick={() => handleSort('support')}>
                                    <div className="flex items-center justify-end gap-1.5">
                                        支持度 <ArrowUpDown size={12} className={sortConfig.key === 'support' ? 'text-[#2383e2]' : 'opacity-20'} />
                                    </div>
                                    <span className="text-[9px] font-normal leading-none opacity-50 uppercase">Support</span>
                                </th>
                                <th className="px-5 py-4 w-28 text-right cursor-pointer hover:bg-[#efefee] transition-colors group" onClick={() => handleSort('confidence')}>
                                    <div className="flex items-center justify-end gap-1.5">
                                        置信度 <ArrowUpDown size={12} className={sortConfig.key === 'confidence' ? 'text-[#2383e2]' : 'opacity-20'} />
                                    </div>
                                    <span className="text-[9px] font-normal leading-none opacity-50 uppercase">Confidence</span>
                                </th>
                                <th className="px-5 py-4 w-28 text-right cursor-pointer hover:bg-[#efefee] transition-colors group" onClick={() => handleSort('lift')}>
                                    <div className="flex items-center justify-end gap-1.5">
                                        提升度 <ArrowUpDown size={12} className={sortConfig.key === 'lift' ? 'text-[#2383e2]' : 'opacity-20'} />
                                    </div>
                                    <span className="text-[9px] font-normal leading-none opacity-50 uppercase">Lift</span>
                                </th>
                                <th className="px-5 py-4 w-32 text-center text-[#ea5b5c]">统计显著性<br /><span className="text-[9px] font-normal leading-none opacity-50 uppercase">Statistical Sig.</span></th>
                                <th className="px-5 py-4 w-40 text-center">联动可视化<br /><span className="text-[9px] font-normal leading-none opacity-50 uppercase">Visualization</span></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#e9e9e8]">
                            <AnimatePresence mode='popLayout'>
                                {paginatedRules.map((r, idx: number) => {
                                    const ruleKey = getRuleKey(r);
                                    const isFocused = activeFocusedRuleKey === ruleKey;
                                    return (
                                    <motion.tr
                                        ref={(node) => { ruleRowRefs.current[ruleKey] = node; }}
                                        layout
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, scale: 0.95 }}
                                        transition={{ duration: 0.2, delay: idx * 0.02 }}
                                        key={ruleKey}
                                        className={cn(
                                            "hover:bg-[#fbfbfa] transition-colors group",
                                            isFocused ? "bg-blue-50/60 ring-1 ring-inset ring-[#2383e2]" : ""
                                        )}
                                    >
                                        <td className="px-5 py-4 border-r border-[#efefee]">
                                            <div className="flex items-center gap-4">
                                                <span className="w-5 h-5 rounded-md flex items-center justify-center bg-[#efefee] text-[#b4b4b3] text-[10px] font-mono shrink-0 shadow-inner group-hover:bg-[#2383e2] group-hover:text-white transition-colors">
                                                    {currentPage * rowsPerPage + idx + 1}
                                                </span>
                                                <div className="flex items-center text-[12px] gap-2">
                                                    {isFocused && (
                                                        <span className="inline-flex items-center rounded-full bg-[#eef6ff] px-2 py-0.5 text-[10px] font-black text-[#2383e2] shrink-0">
                                                            系统定位
                                                        </span>
                                                    )}
                                                    <span className="bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-lg border border-emerald-100 font-medium">{r.antecedents.join(' \u00b7 ')}</span>
                                                    <div className="flex flex-col items-center">
                                                        <ArrowRight size={14} className="text-[#d3d3d3]" />
                                                        <span className="text-[8px] text-[#d3d3d3] font-bold">IMPLY</span>
                                                    </div>
                                                    <span className="bg-blue-50 text-blue-700 px-2.5 py-1 rounded-lg border border-blue-100 font-medium">{r.consequents.join(' \u00b7 ')}</span>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-5 py-4 text-right text-[#787774] font-mono tabular-nums">{(r.support * 100).toFixed(1)}%</td>
                                        <td className="px-5 py-4 text-right font-bold text-[#37352f] font-mono tabular-nums">{(r.confidence * 100).toFixed(1)}%</td>
                                        <td className="px-5 py-4 text-right font-black text-amber-600 font-mono tabular-nums">{(r.lift * 1).toFixed(2)}</td>
                                        <td className="px-5 py-4 text-center">
                                            {r.significant ? (
                                                <div className="flex justify-center" title={`P Value: ${Number(r.p_value).toExponential(2)}`}>
                                                    <div className="inline-flex items-center px-3 py-1 rounded-full text-[10px] font-black bg-emerald-500 text-white shadow-sm gap-1.5 shadow-emerald-500/20">
                                                        <CheckCircle2 size={10} /> 显著
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="flex justify-center">
                                                    <div className="inline-flex items-center px-3 py-1 rounded-full text-[10px] font-bold bg-gray-100 text-gray-400 gap-1.5 border border-gray-200">
                                                        <Info size={10} /> 随机
                                                    </div>
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-5 py-4">
                                            <div className="flex items-center justify-center">
                                                <div className="mr-2">
                                                    <RuleActionGuide />
                                                </div>
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger asChild>
                                                        <button
                                                            type="button"
                                                            className="inline-flex items-center gap-1.5 rounded-lg border border-[#dbe7ff] bg-white px-3 py-1.5 text-[11px] font-semibold text-[#4f4e49] shadow-sm hover:bg-[#f8fbff] transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]"
                                                        >
                                                            <BarChart3 size={12} />
                                                            操作
                                                            <ChevronDown size={12} />
                                                        </button>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end" className="w-52">
                                                        <DropdownMenuItem disabled className="text-[10px] font-black uppercase tracking-widest text-[#9b9a97] opacity-100">
                                                            浏览
                                                        </DropdownMenuItem>
                                                        {hasRulePair(r) && (
                                                            <DropdownMenuItem onClick={() => navigate(buildVisualizationUrl(r, 'auto'))}>
                                                                <BarChart3 size={14} className="text-blue-600" />
                                                                查看关系图
                                                            </DropdownMenuItem>
                                                        )}
                                                        <DropdownMenuItem onClick={() => navigate(buildVisualizationUrl(r, 'network'))}>
                                                            <BarChart3 size={14} className="text-purple-600" />
                                                            进入规则网络
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem disabled className="text-[10px] font-black uppercase tracking-widest text-[#9b9a97] opacity-100">
                                                            复制
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem onClick={() => { void handleCopyRuleSummary(r); }}>
                                                            <Copy size={14} className="text-emerald-600" />
                                                            复制规则摘要
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem onClick={() => { void handleCopyVisualizationLink(r, hasRulePair(r) ? 'auto' : 'network'); }}>
                                                            <Link2 size={14} className="text-sky-600" />
                                                            复制联动链接
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem disabled className="text-[10px] font-black uppercase tracking-widest text-[#9b9a97] opacity-100">
                                                            分享
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem onClick={() => { void handleCopyRuleShare(r); }}>
                                                            <Copy size={14} className="text-violet-600" />
                                                            复制摘要和链接
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </div>
                                        </td>
                                    </motion.tr>
                                )})}
                            </AnimatePresence>
                            {paginatedRules.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="py-20 text-center text-[#d3d3d3]">
                                        <div className="animate-in fade-in slide-in-from-bottom-3 duration-300">
                                            <Search size={48} className="mx-auto mb-4 opacity-20 animate-pulse" />
                                            <p className="text-sm font-medium">无匹配挖掘结果，请尝试简化检索词</p>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
                {/* 分页控制 */}
                {sortedRules.length > rowsPerPage && (
                    <div className="flex flex-col sm:flex-row items-center justify-between p-5 bg-[#fbfbfa] border-t border-[#e9e9e8] gap-4">
                        <span className="text-xs text-[#787774] font-medium">
                            展示 <span className="text-[#37352f]">{currentPage * rowsPerPage + 1}</span> 至 <span className="text-[#37352f]">{Math.min((currentPage + 1) * rowsPerPage, sortedRules.length)}</span> 项核心结果，在 <span className="text-[#2383e2]">{sortedRules.length}</span> 条发现中
                        </span>
                        <div className="flex items-center gap-1">
                            <button
                                className="px-3 py-1.5 text-xs font-bold bg-white border border-[#e9e9e8] rounded-lg hover:bg-[#f5f5f4] disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40"
                                onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                                disabled={currentPage === 0}
                            >
                                上一页
                            </button>
                            <div className="flex gap-1 px-4">
                                <span className="text-xs font-black text-[#2383e2]">{currentPage + 1}</span>
                                <span className="text-[10px] text-[#d3d3d3] font-bold">/</span>
                                <span className="text-xs font-bold text-[#787774]">{Math.ceil(sortedRules.length / rowsPerPage)}</span>
                            </div>
                            <button
                                className="px-3 py-1.5 text-xs font-bold bg-white border border-[#e9e9e8] rounded-lg hover:bg-[#f5f5f4] disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40"
                                onClick={() => setCurrentPage(p => Math.min(Math.ceil(sortedRules.length / rowsPerPage) - 1, p + 1))}
                                disabled={currentPage >= Math.ceil(sortedRules.length / rowsPerPage) - 1}
                            >
                                下一页
                            </button>
                        </div>
                    </div>
                )}
            </div>
            <div className="h-10"></div>
        </div>
    );
}

const ResultMetricCard = memo(function ResultMetricCard({ label, value, hint }: { label: string; value: string; hint: string }) {
    return (
        <div className="rounded-2xl border border-[#eef1f4] bg-[#fafbfc] px-4 py-3">
            <div className="text-[10px] font-black uppercase tracking-widest text-[#9b9a97]">{label}</div>
            <div className="mt-1 text-lg font-black text-[#37352f]">{value}</div>
            <div className="mt-1 text-[10px] leading-relaxed text-[#9b9a97]">{hint}</div>
        </div>
    );
});

const MiniStat = memo(function MiniStat({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-xl border border-[#e6e9ed] bg-white px-3 py-2">
            <div className="text-[10px] font-black uppercase tracking-widest text-[#9b9a97]">{label}</div>
            <div className="mt-1 text-sm font-black text-[#37352f]">{value}</div>
        </div>
    );
});
