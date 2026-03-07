import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { BarChart3, PieChart, Activity, RefreshCw, ScatterChart, Filter, Type, Sliders, BoxSelect, Maximize2, TrendingUp, Hash, Sigma, ArrowDownUp, Download, ZoomIn, ZoomOut, RotateCcw, ExternalLink, Wand2, GitBranchPlus, X, Copy, CheckCircle2, AlertCircle, BellRing, MoreHorizontal, ChevronLeft, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../utils/cn';
import { visualizationService, dataService, algorithmService, extractErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { Button } from '../components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '../components/ui/dropdown-menu';
import { useAbortEffect } from '../hooks/useAbortEffect';
import type { ChartMeta, ChartGenerationConfig, DataProfile, AssociationRule } from '../types';

const chartTypes = [
    { id: 'correlation_heatmap', name: '全变量相关性热力图', icon: BoxSelect, color: 'text-orange-500' },
    { id: 'scatter', name: '变量相互作用散点分布', icon: ScatterChart, color: 'text-blue-500' },
    { id: 'bar', name: '分类维度柱状统计图', icon: BarChart3, color: 'text-cyan-500' },
    { id: 'network', name: '拓扑关联规则网络', icon: Activity, color: 'text-purple-500' },
    { id: 'distribution', name: '单维度正态与频数分布', icon: BarChart3, color: 'text-emerald-500' },
    { id: 'box', name: '分组四分位异常探测', icon: Sliders, color: 'text-rose-500' },
    { id: 'line', name: '序列特征趋势线', icon: Activity, color: 'text-indigo-400' },
];

const defaultChartConfig: ChartGenerationConfig = {
    x_col: '',
    y_col: '',
    add_trendline: true,
    show_regression_info: true,
    method: 'pearson',
    colorscale: 'RdBu_r',
    bins: 30,
    top_n: 20,
    xaxis_angle: -45,
    show_points: true,
    show_markers: true,
    trendline_window: 5,
};

type DownloadType = '' | 'html' | 'png' | 'svg' | 'pdf';
type DownloadState = 'idle' | 'processing' | 'success' | 'error';
type DownloadStage = '' | 'prepare' | 'generate' | 'write' | 'complete' | 'failed';
type DownloadFailureAction = {
    label: string;
    reason: string;
    onClick: () => void;
};

export default function Visualization() {
    const { toast } = useToast();
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const [loading, setLoading] = useState(false);
    const [profile, setProfile] = useState<DataProfile | null>(null);
    const [rulesData, setRulesData] = useState<AssociationRule[]>([]);
    const [chartHtml, setChartHtml] = useState<string>('');
    const [chartUrl, setChartUrl] = useState<string>('');
    const [chartMeta, setChartMeta] = useState<ChartMeta | null>(null);
    const [sourceRuleText, setSourceRuleText] = useState('');
    const [sourceRuleKey, setSourceRuleKey] = useState('');
    const [sourceTaskId, setSourceTaskId] = useState('');
    const [sourceRuleFields, setSourceRuleFields] = useState<{ x: string; y: string }>({ x: '', y: '' });
    const [zoomLevel, setZoomLevel] = useState(1);
    const [activeDownload, setActiveDownload] = useState<DownloadType>('');
    const [downloadStatus, setDownloadStatus] = useState<{ type: DownloadType; state: DownloadState; stage: DownloadStage; message: string; hint: string }>({ type: '', state: 'idle', stage: '', message: '', hint: '' });
    const [lastDownloadType, setLastDownloadType] = useState<DownloadType>('');
    const viewerRef = useRef<HTMLDivElement | null>(null);
    const iframeRef = useRef<HTMLIFrameElement | null>(null);
    const configMemoryRef = useRef<Record<string, ChartGenerationConfig>>({});
    const lastAppliedQueryRef = useRef('');

    const [selectedType, setSelectedType] = useState('correlation_heatmap');
    const [config, setConfig] = useState<ChartGenerationConfig>(defaultChartConfig);

    const handleLockCurrentFields = () => {
        configMemoryRef.current[selectedType] = config;
        toast.success('当前字段组合已锁定，可继续在此基础上微调。');
    };

    const handleReapplySourceRecommendation = () => {
        if (!sourceRuleFields.x && !sourceRuleFields.y) {
            toast.warning('当前没有可重新应用的来源规则字段。');
            return;
        }
        const applied = resolveAutoRulePreset(sourceRuleFields.x, sourceRuleFields.y);
        configMemoryRef.current[selectedType] = config;
        configMemoryRef.current[applied.type] = applied.config;
        setSelectedType(applied.type);
        setConfig(applied.config);
        toast.success(`已恢复规则推荐：${applied.label}`);
    };

    const buildChartFilename = (extension: string) => {
        const chartName = chartTypes.find(c => c.id === selectedType)?.name || 'chart';
        const normalizedRule = sourceRuleText
            .replace(/[<>:"/\\|?*]+/g, ' ')
            .replace(/\s*→\s*/g, '_to_')
            .replace(/\s*&\s*/g, '_')
            .replace(/\s+/g, '_')
            .trim()
            .slice(0, 48);
        const filenameBase = normalizedRule ? `${chartName}_${normalizedRule}` : chartName;
        return `${filenameBase}.${extension}`;
    };

    const getDownloadLabel = (type: DownloadType) => {
        switch (type) {
            case 'html':
                return '网页图表';
            case 'png':
                return 'PNG 图片';
            case 'svg':
                return 'SVG 矢量图';
            case 'pdf':
                return 'PDF 文档';
            default:
                return '下载任务';
        }
    };

    const getDownloadProgressSteps = (stage: DownloadStage, state: DownloadState) => {
        const steps = [
            { key: 'prepare', label: '准备' },
            { key: 'generate', label: '生成' },
            { key: 'write', label: '写入' },
        ] as const;
        const activeIndex = stage === 'prepare'
            ? 0
            : stage === 'generate'
                ? 1
                : stage === 'write'
                    ? 2
                    : stage === 'complete'
                        ? 2
                        : stage === 'failed'
                            ? 0
                            : 0;

        return steps.map((step, index) => {
            const isComplete = state === 'success' ? true : index < activeIndex;
            const isCurrent = state === 'processing' ? index === activeIndex : state === 'error' ? index === activeIndex : false;
            return { ...step, isComplete, isCurrent };
        });
    };

    const getDownloadFailureHint = (rawMessage: string) => {
        const normalizedMessage = rawMessage.toLowerCase();
        if (
            normalizedMessage.includes('kaleido')
            || normalizedMessage.includes('依赖')
            || normalizedMessage.includes('not installed')
            || normalizedMessage.includes('missing')
        ) {
            return '导出依赖未就绪';
        }
        if (
            normalizedMessage.includes('timeout')
            || normalizedMessage.includes('timed out')
            || normalizedMessage.includes('超时')
            || normalizedMessage.includes('network')
            || normalizedMessage.includes('连接')
        ) {
            return '导出服务响应超时';
        }
        if (
            normalizedMessage.includes('403')
            || normalizedMessage.includes('forbidden')
            || normalizedMessage.includes('denied')
            || normalizedMessage.includes('权限')
            || normalizedMessage.includes('拦截')
        ) {
            return '权限或浏览器拦截';
        }
        if (
            normalizedMessage.includes('500')
            || normalizedMessage.includes('internal server error')
            || normalizedMessage.includes('backend')
            || normalizedMessage.includes('后端')
            || normalizedMessage.includes('服务')
        ) {
            return '后端导出服务异常';
        }
        return '请检查导出依赖或后端日志';
    };

    const getRuleKey = (rule: AssociationRule) => `${rule.antecedents.join('__')}=>${rule.consequents.join('__')}`;
    const getRuleSummary = (rule: AssociationRule) => `${rule.antecedents.join(' & ')} → ${rule.consequents.join(' & ')}`;
    const hasRulePair = (rule: AssociationRule) => Boolean(rule.antecedents[0] && (rule.consequents[0] || rule.antecedents[1]));

    const setDownloadPhase = (type: DownloadType, state: DownloadState, stage: DownloadStage, message: string, hint = '') => {
        setDownloadStatus({ type, state, stage, message, hint });
    };

    const getDownloadStageLabel = (stage: DownloadStage) => {
        switch (stage) {
            case 'prepare':
                return '准备中';
            case 'generate':
                return '生成中';
            case 'write':
                return '写入中';
            case 'complete':
                return '已完成';
            case 'failed':
                return '失败';
            default:
                return '通知';
        }
    };

    const getStatusNoticeMeta = () => {
        if (activeDownload || downloadStatus.state === 'processing') {
            const currentType = activeDownload || downloadStatus.type;
            return {
                icon: RefreshCw,
                stageLabel: getDownloadStageLabel(downloadStatus.stage || 'prepare'),
                title: `系统正在处理 ${getDownloadLabel(currentType)}`,
                detail: downloadStatus.message || '导出任务已进入处理队列，请稍候。',
                hint: '',
                tone: 'processing' as const,
            };
        }

        if (!downloadStatus.message || !chartUrl) {
            return null;
        }

        if (downloadStatus.state === 'success') {
            return {
                icon: CheckCircle2,
                stageLabel: getDownloadStageLabel(downloadStatus.stage || 'complete'),
                title: `${getDownloadLabel(downloadStatus.type)} 已完成`,
                detail: downloadStatus.message,
                hint: '',
                tone: 'success' as const,
            };
        }

        if (downloadStatus.state === 'error') {
            return {
                icon: AlertCircle,
                stageLabel: getDownloadStageLabel(downloadStatus.stage || 'failed'),
                title: `${getDownloadLabel(downloadStatus.type)} 导出失败`,
                detail: downloadStatus.message,
                hint: downloadStatus.hint,
                tone: 'error' as const,
            };
        }

        return {
            icon: BellRing,
            stageLabel: getDownloadStageLabel(downloadStatus.stage),
            title: '系统导出通知',
            detail: downloadStatus.message,
            hint: '',
            tone: 'processing' as const,
        };
    };

    const handleCopyChartConfigWithLink = async () => {
        try {
            const chartName = chartTypes.find(c => c.id === selectedType)?.name || selectedType;
            const keyHighlights = [
                `主字段：${config.x_col || '自动/无'}`,
                `副字段：${config.y_col || '自动/无'}`,
                selectedType === 'correlation_heatmap' ? `相关方法：${config.method || 'pearson'}` : '',
                selectedType === 'distribution' ? `分箱：${String(config.bins ?? 30)}` : '',
                selectedType === 'bar' ? `TopN：${String(config.top_n ?? 20)}` : '',
                selectedType === 'line' ? `趋势窗口：${String(config.trendline_window ?? 5)}` : '',
                selectedType === 'scatter' ? `趋势线：${config.add_trendline ? '开启' : '关闭'}` : '',
            ].filter(Boolean);

            // 构造分享链接：确保包含 taskId，这样其他人打开链接能加载到相同的数据基础
            const url = new URL(window.location.href);
            if (sourceTaskId && !url.searchParams.has('task_id')) {
                url.searchParams.set('task_id', sourceTaskId);
            }
            if (selectedType && !url.searchParams.has('preset')) {
                url.searchParams.set('preset', selectedType === 'correlation_heatmap' ? 'correlation_overview' : selectedType);
            }

            const shareText = [
                '分享一张当前图表：',
                `图表类型：${chartName}`,
                sourceRuleText ? `来源规则：${sourceRuleText}` : '',
                keyHighlights.join('｜'),
                `页面链接：${url.toString()}`,
            ].filter(Boolean).join('\n');

            await navigator.clipboard.writeText(shareText);
            toast.success('当前图表配置和分享链接已复制，协作伙伴可直接打开此链接查看图表。');
        } catch (e) {
            console.error('Sharing failed:', e);
            toast.error('图表配置和链接复制失败，请稍后重试');
        }
    };


    const resolveAutoRulePreset = (xCol: string, yCol: string) => {
        if (!profile) {
            return { type: 'scatter', label: '规则联动散点', config: { ...defaultChartConfig, x_col: xCol, y_col: yCol } };
        }

        const numericCols = profile.numeric_cols ?? [];
        const categoricalCols = profile.categorical_cols ?? [];
        const allCols = profile.columns ?? [];
        const fallbackNumeric = numericCols[0] ?? allCols[0] ?? '';
        const fallbackNumericPair = numericCols.find(col => col !== fallbackNumeric) ?? numericCols[1] ?? fallbackNumeric;
        const fallbackCategorical = categoricalCols[0] ?? allCols[0] ?? fallbackNumeric;
        const safeX = xCol && allCols.includes(xCol) ? xCol : (fallbackCategorical || fallbackNumeric);
        const safeY = yCol && allCols.includes(yCol) ? yCol : fallbackNumericPair;
        const xIsNumeric = numericCols.includes(safeX);
        const yIsNumeric = numericCols.includes(safeY);
        const xIsCategorical = categoricalCols.includes(safeX);

        if (safeX && safeY && xIsNumeric && yIsNumeric) {
            return {
                type: 'scatter',
                label: '规则联动散点',
                config: {
                    ...defaultChartConfig,
                    x_col: safeX,
                    y_col: safeY,
                    add_trendline: true,
                    show_regression_info: true,
                }
            };
        }
        if (safeX && safeY && xIsCategorical && yIsNumeric) {
            return {
                type: 'bar',
                label: '规则联动柱状图',
                config: {
                    ...defaultChartConfig,
                    x_col: safeX,
                    y_col: safeY,
                    top_n: 12,
                    xaxis_angle: -30,
                }
            };
        }
        if (safeX && xIsNumeric) {
            return {
                type: 'distribution',
                label: '规则联动分布图',
                config: {
                    ...defaultChartConfig,
                    x_col: safeX,
                    y_col: '',
                    bins: 30,
                }
            };
        }

        return {
            type: 'bar',
            label: '规则联动分类图',
            config: {
                ...defaultChartConfig,
                x_col: safeX,
                y_col: yIsNumeric ? safeY : (fallbackNumeric || ''),
                top_n: 12,
                xaxis_angle: -30,
            }
        };
    };

    const getPresetConfig = (presetId: string): { type: string; config: ChartGenerationConfig; label: string } | null => {
        const numeric = profile?.numeric_cols ?? [];
        const categorical = profile?.categorical_cols ?? [];
        const allColumns = profile?.columns ?? [];
        const firstNumeric = numeric[0] ?? allColumns[0] ?? '';
        const secondNumeric = numeric.find(col => col !== firstNumeric) ?? numeric[1] ?? firstNumeric;
        const firstCategorical = categorical[0] ?? allColumns[0] ?? '';

        switch (presetId) {
            case 'correlation_overview':
                return {
                    type: 'correlation_heatmap',
                    label: '相关性总览',
                    config: {
                        ...defaultChartConfig,
                        x_col: firstNumeric,
                        y_col: secondNumeric,
                        method: 'pearson',
                        colorscale: 'RdBu_r',
                    }
                };
            case 'numeric_scatter':
                return {
                    type: 'scatter',
                    label: '双变量散点',
                    config: {
                        ...defaultChartConfig,
                        x_col: firstNumeric,
                        y_col: secondNumeric,
                        add_trendline: true,
                        show_regression_info: true,
                    }
                };
            case 'single_distribution':
                return {
                    type: 'distribution',
                    label: '单变量分布',
                    config: {
                        ...defaultChartConfig,
                        x_col: firstNumeric,
                        y_col: '',
                        bins: 30,
                    }
                };
            case 'category_ranking':
                return {
                    type: 'bar',
                    label: '分类排行柱状图',
                    config: {
                        ...defaultChartConfig,
                        x_col: firstCategorical || firstNumeric,
                        y_col: firstCategorical ? firstNumeric : '',
                        top_n: 12,
                        xaxis_angle: -30,
                    }
                };
            case 'trend_line':
                return {
                    type: 'line',
                    label: '趋势分析',
                    config: {
                        ...defaultChartConfig,
                        x_col: firstNumeric,
                        y_col: secondNumeric,
                        show_markers: true,
                        add_trendline: true,
                        trendline_window: 5,
                    }
                };
            case 'rule_network':
                return {
                    type: 'network',
                    label: '规则网络',
                    config: {
                        ...defaultChartConfig,
                        x_col: '',
                        y_col: '',
                    }
                };
            default:
                return null;
        }
    };

    useAbortEffect((signal) => {
        dataService.getProfile(sourceTaskId, signal)
            .then(res => {
                if (res.success && res.profile) {
                    const prof = res.profile;
                    setProfile(prof);

                    if (prof.numeric_cols?.length > 0) {
                        setConfig(prev => ({
                            ...prev,
                            x_col: prof.numeric_cols[0],
                            y_col: prof.numeric_cols.length > 1 ? prof.numeric_cols[1] : prof.numeric_cols[0]
                        }));
                    }
                }
            })
            .catch(() => { });
    }, []);

    useAbortEffect((signal) => {
        const loadRules = async () => {
            try {
                if (sourceTaskId) {
                    const task = await algorithmService.getTaskStatus(sourceTaskId, signal);
                    setRulesData(task.result?.rules ?? []);
                    return;
                }
                const res = await algorithmService.getLastTask(signal);
                setRulesData(res.task?.result?.rules ?? []);
            } catch {
                setRulesData([]);
            }
        };
        void loadRules();
    }, [sourceTaskId]);

    const primaryColumnOptions = !profile
        ? []
        : ['scatter', 'distribution', 'box', 'correlation_heatmap'].includes(selectedType)
            ? profile.numeric_cols
            : selectedType === 'line'
                ? (profile.numeric_cols.length ? profile.numeric_cols : profile.columns)
                : selectedType === 'bar'
                    ? (profile.categorical_cols.length ? [...profile.categorical_cols, ...profile.numeric_cols] : profile.columns)
                    : profile.columns;

    const setRememberedConfig = (nextConfig: ChartGenerationConfig) => {
        configMemoryRef.current[selectedType] = nextConfig;
        setConfig(nextConfig);
    };

    const handleSelectType = (nextType: string) => {
        configMemoryRef.current[selectedType] = config;
        setSelectedType(nextType);
        setConfig(configMemoryRef.current[nextType] ?? { ...defaultChartConfig });
    };

    const secondaryColumnOptions = !profile
        ? []
        : ['scatter', 'line'].includes(selectedType)
            ? profile.numeric_cols
            : selectedType === 'box'
                ? (profile.categorical_cols.length ? profile.categorical_cols : profile.columns)
                : selectedType === 'bar'
                    ? (profile.numeric_cols.length ? profile.numeric_cols : profile.columns)
                    : profile.columns;

    useEffect(() => {
        if (!profile) return;
        if (selectedType === 'correlation_heatmap' || selectedType === 'network') return;

        setConfig(prev => {
            let nextX = prev.x_col;
            let nextY = prev.y_col;

            if (!primaryColumnOptions.includes(nextX)) {
                nextX = primaryColumnOptions[0] ?? '';
            }

            if (['scatter', 'line'].includes(selectedType)) {
                if (!secondaryColumnOptions.includes(nextY) || !nextY) {
                    nextY = secondaryColumnOptions.find(col => col !== nextX) ?? secondaryColumnOptions[0] ?? '';
                }
            } else if (nextY && !secondaryColumnOptions.includes(nextY)) {
                nextY = '';
            }

            if (nextX === prev.x_col && nextY === prev.y_col) {
                return prev;
            }

            return { ...prev, x_col: nextX, y_col: nextY };
        });
    }, [profile, selectedType, primaryColumnOptions, secondaryColumnOptions]);

    useEffect(() => {
        if (!chartHtml) {
            setChartUrl('');
            return;
        }
        const fullDocument = `<!DOCTYPE html><html><head><meta charset="utf-8" /><style>html,body{margin:0;padding:0;background:#fff;width:100%;height:100%;}body{overflow:auto;zoom:${zoomLevel};}.js-plotly-plot,.plotly,.plot-container{width:100%!important;height:100%!important;}.main-svg{width:100%!important;height:100%!important;}</style></head><body>${chartHtml}</body></html>`;
        const blob = new Blob([fullDocument], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        setChartUrl(url);

        return () => {
            URL.revokeObjectURL(url);
        };
    }, [chartHtml, zoomLevel]);

    useEffect(() => {
        if (!downloadStatus.message || downloadStatus.state === 'idle' || downloadStatus.state === 'processing' || activeDownload) return;
        const timer = window.setTimeout(() => {
            setDownloadStatus({ type: '', state: 'idle', stage: '', message: '', hint: '' });
        }, 3200);
        return () => window.clearTimeout(timer);
    }, [downloadStatus, activeDownload]);

    useEffect(() => {
        if (activeDownload) return;
        setDownloadStatus({ type: '', state: 'idle', stage: '', message: '', hint: '' });
    }, [selectedType, chartHtml]);

    const handleDownloadChart = async () => {
        if (!chartHtml) return;
        setActiveDownload('html');
        setLastDownloadType('html');
        setDownloadPhase('html', 'processing', 'prepare', `正在准备 ${getDownloadLabel('html')} 的导出内容…`);
        try {
            const chartName = chartTypes.find(c => c.id === selectedType)?.name || 'chart';
            const sourceHeader = sourceRuleText
                ? `<div style="padding:16px 20px;border-bottom:1px solid #e9e9e8;background:linear-gradient(90deg,#eff6ff,#eef2ff);font-family:Arial,'Microsoft YaHei',sans-serif;"><div style="font-size:12px;font-weight:700;letter-spacing:.08em;color:#2383e2;text-transform:uppercase;">来源规则</div><div style="margin-top:6px;font-size:14px;color:#37352f;font-weight:600;word-break:break-word;">${sourceRuleText}</div></div>`
                : '';
            const html = `<!DOCTYPE html><html><head><meta charset="utf-8" /><title>${sourceRuleText ? `${chartName} - ${sourceRuleText}` : chartName}</title><style>html,body{margin:0;padding:0;background:#fff;}body{overflow:auto;}</style></head><body>${sourceHeader}${chartHtml}</body></html>`;
            setDownloadPhase('html', 'processing', 'write', `正在写入 ${getDownloadLabel('html')} 下载文件…`);
            const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = buildChartFilename('html');
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
            setDownloadPhase('html', 'success', 'complete', `${getDownloadLabel('html')} 已写入浏览器下载队列`);
            toast.success(`${getDownloadLabel('html')} 已开始下载`);
        } catch (e) {
            const failureMessage = extractErrorMessage(e, `${getDownloadLabel('html')} 下载失败，请稍后重试`);
            setDownloadPhase('html', 'error', 'failed', `${getDownloadLabel('html')} 导出失败，请稍后重试`, getDownloadFailureHint(failureMessage));
            toast.error(failureMessage);
        } finally {
            window.setTimeout(() => setActiveDownload(''), 400);
        }
    };

    const handleOpenChartInNewTab = () => {
        if (!chartUrl) return;
        window.open(chartUrl, '_blank', 'noopener,noreferrer');
    };

    const handleToggleFullscreen = async () => {
        const element = viewerRef.current;
        if (!element) return;
        if (document.fullscreenElement) {
            await document.exitFullscreen();
            return;
        }
        await element.requestFullscreen();
    };

    const handleFitWidth = () => {
        setZoomLevel(0.9);
    };

    const handleResetCurrentChartConfig = () => {
        const resetConfig = {
            ...defaultChartConfig,
            x_col: primaryColumnOptions[0] ?? '',
            y_col: ['scatter', 'line'].includes(selectedType)
                ? (secondaryColumnOptions.find(col => col !== (primaryColumnOptions[0] ?? '')) ?? secondaryColumnOptions[0] ?? '')
                : '',
        };
        configMemoryRef.current[selectedType] = resetConfig;
        setConfig(resetConfig);
        toast.success('当前图表配置已重置');
    };

    const applyPreset = (presetId: string, options?: { silent?: boolean }) => {
        const preset = getPresetConfig(presetId);
        if (!preset) {
            if (!options?.silent) {
                toast.warning('未识别到对应的图表预设。');
            }
            return null;
        }
        if (preset.type === 'network' && rulesData.length === 0) {
            if (!options?.silent) {
                toast.warning('当前没有可用规则数据，暂时无法使用规则网络预设。');
            }
            return null;
        }
        if (preset.type !== 'network' && preset.type !== 'correlation_heatmap' && !preset.config.x_col) {
            if (!options?.silent) {
                toast.warning('当前数据字段不足，暂时无法应用该预设。');
            }
            return null;
        }

        configMemoryRef.current[selectedType] = config;
        configMemoryRef.current[preset.type] = preset.config;
        setSelectedType(preset.type);
        setConfig(preset.config);

        if (!options?.silent) {
            toast.success(`已应用预设：${preset.label}`);
        }

        return preset;
    };

    // PNG / SVG：纯前端导出，调用 iframe 内已渲染的 Plotly.toImage，不依赖 kaleido
    const handleClientExport = async (format: 'png' | 'svg') => {
        if (!chartUrl) return;
        setActiveDownload(format);
        setLastDownloadType(format);
        setDownloadPhase(format, 'processing', 'prepare', `正在准备 ${getDownloadLabel(format)} 的导出内容…`);
        try {
            const iframe = iframeRef.current;
            type PlotlyWin = Window & { Plotly?: { toImage: (el: Element, opts: object) => Promise<string> } };
            const iframeWin = iframe?.contentWindow as PlotlyWin | null;
            const plotlyDiv = iframe?.contentDocument?.querySelector('.js-plotly-plot');
            if (!iframeWin?.Plotly || !plotlyDiv) {
                throw new Error('图表视图未就绪，请先生成图表后再导出');
            }
            setDownloadPhase(format, 'processing', 'generate', `正在生成 ${getDownloadLabel(format)} 文件，请稍候…`);
            const dataUrl = await iframeWin.Plotly.toImage(plotlyDiv, { format, width: 1400, height: 900 });
            setDownloadPhase(format, 'processing', 'write', `正在写入 ${getDownloadLabel(format)} 下载文件…`);
            const link = document.createElement('a');
            link.href = dataUrl;
            link.download = buildChartFilename(format);
            document.body.appendChild(link);
            link.click();
            link.remove();
            setDownloadPhase(format, 'success', 'complete', `${getDownloadLabel(format)} 已写入浏览器下载队列`);
            toast.success(`${getDownloadLabel(format)} 已开始下载`);
        } catch (e) {
            const failureMessage = extractErrorMessage(e, `${format.toUpperCase()} 导出失败，请稍后重试`);
            setDownloadPhase(format, 'error', 'failed', failureMessage, getDownloadFailureHint(failureMessage));
            toast.error(failureMessage);
        } finally {
            window.setTimeout(() => setActiveDownload(''), 400);
        }
    };

    // PDF：仍走后端（需要 kaleido），但有超时保护
    const handleExportFile = async (format: 'pdf') => {
        if (!chartUrl) return;
        setActiveDownload(format);
        setLastDownloadType(format);
        setDownloadPhase(format, 'processing', 'prepare', `正在准备 ${getDownloadLabel(format)} 的导出参数…`);
        try {
            const downloadFilename = buildChartFilename(format);
            const payload = {
                chart_type: selectedType,
                use_current_data: !sourceTaskId,
                task_id: sourceTaskId || undefined,
                x_col: config.x_col,
                y_col: config.y_col || undefined,
                column: config.x_col,
                value_col: config.x_col,
                group_col: config.y_col || undefined,
                rules_data: selectedType === 'network' ? rulesData : undefined,
                format,
                filename: downloadFilename,
                config: {
                    add_trendline: config.add_trendline,
                    show_regression_info: config.show_regression_info,
                    method: config.method,
                    colorscale: config.colorscale,
                    bins: config.bins,
                    top_n: config.top_n,
                    xaxis_angle: config.xaxis_angle,
                    show_points: config.show_points,
                    show_markers: config.show_markers,
                    trendline_window: config.trendline_window,
                    width: 1400,
                    height: 900
                }
            };
            setDownloadPhase(format, 'processing', 'generate', `正在生成 ${getDownloadLabel(format)} 文件，请稍候…`);
            const blob = await visualizationService.exportChart(payload);
            setDownloadPhase(format, 'processing', 'write', `正在写入 ${getDownloadLabel(format)} 下载文件…`);
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = downloadFilename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
            setDownloadPhase(format, 'success', 'complete', `${getDownloadLabel(format)} 已写入浏览器下载队列`);
            toast.success(`${getDownloadLabel(format)} 已开始下载`);
        } catch (e) {
            const failureMessage = extractErrorMessage(e, `${format.toUpperCase()} 导出失败，请确认导出依赖已安装。`);
            setDownloadPhase(format, 'error', 'failed', `${getDownloadLabel(format)} 导出失败，请确认导出依赖已安装。`, getDownloadFailureHint(failureMessage));
            toast.error(failureMessage);
        } finally {
            window.setTimeout(() => setActiveDownload(''), 250);
        }
    };

    const handleExportPng = async () => { await handleClientExport('png'); };

    const handleRetryDownload = async () => {
        if (!downloadStatus.type || activeDownload) return;
        if (downloadStatus.type === 'html') { await handleDownloadChart(); return; }
        if (downloadStatus.type === 'png' || downloadStatus.type === 'svg') {
            await handleClientExport(downloadStatus.type);
            return;
        }
        await handleExportFile('pdf');
    };

    const handleRepeatLastDownload = async () => {
        if (!lastDownloadType || activeDownload) return;
        if (lastDownloadType === 'html') { await handleDownloadChart(); return; }
        if (lastDownloadType === 'png' || lastDownloadType === 'svg') {
            await handleClientExport(lastDownloadType);
            return;
        }
        await handleExportFile('pdf');
    };

    const handleCopyChartConfig = async () => {
        try {
            const chartName = chartTypes.find(c => c.id === selectedType)?.name || selectedType;
            const configLines = [
                `图表类型：${chartName}`,
                sourceRuleText ? `来源规则：${sourceRuleText}` : '',
                `主字段：${config.x_col || '自动/无'}`,
                `副字段：${config.y_col || '自动/无'}`,
                selectedType === 'correlation_heatmap' ? `相关方法：${config.method || 'pearson'}` : '',
                selectedType === 'correlation_heatmap' ? `色板：${config.colorscale || 'RdBu_r'}` : '',
                selectedType === 'distribution' ? `分箱：${String(config.bins ?? 30)}` : '',
                selectedType === 'bar' ? `TopN：${String(config.top_n ?? 20)}` : '',
                selectedType === 'bar' ? `X轴角度：${String(config.xaxis_angle ?? -45)}°` : '',
                selectedType === 'box' ? `异常点：${config.show_points ? '显示' : '隐藏'}` : '',
                selectedType === 'line' ? `标记点：${config.show_markers ? '显示' : '隐藏'}` : '',
                selectedType === 'line' ? `趋势窗口：${String(config.trendline_window ?? 5)}` : '',
                selectedType === 'scatter' ? `趋势线：${config.add_trendline ? '开启' : '关闭'}` : '',
                selectedType === 'scatter' ? `回归统计：${config.show_regression_info ? '开启' : '关闭'}` : '',
            ].filter(Boolean);
            await navigator.clipboard.writeText(configLines.join('\n'));
            toast.success('当前图表配置已复制');
        } catch {
            toast.error('图表配置复制失败，请稍后重试');
        }
    };

    const chartSummaryItems = [
        { label: '主字段', value: config.x_col || '自动/无' },
        ...(config.y_col ? [{ label: '副字段', value: config.y_col }] : []),
        ...(selectedType === 'correlation_heatmap' ? [
            { label: '相关方法', value: config.method || 'pearson' },
            { label: '色板', value: config.colorscale || 'RdBu_r' },
        ] : []),
        ...(selectedType === 'distribution' ? [{ label: '分箱', value: String(config.bins ?? 30) }] : []),
        ...(selectedType === 'bar' ? [
            { label: 'TopN', value: String(config.top_n ?? 20) },
            { label: '角度', value: `${config.xaxis_angle ?? -45}°` },
        ] : []),
        ...(selectedType === 'box' ? [{ label: '异常点', value: config.show_points ? '显示' : '隐藏' }] : []),
        ...(selectedType === 'line' ? [
            { label: '标记点', value: config.show_markers ? '显示' : '隐藏' },
            { label: '趋势窗口', value: String(config.trendline_window ?? 5) },
        ] : []),
        ...(selectedType === 'scatter' ? [
            { label: '趋势线', value: config.add_trendline ? '开启' : '关闭' },
            { label: '回归统计', value: config.show_regression_info ? '开启' : '关闭' },
        ] : []),
    ];

    const handleApplyExplorationView = async (type: string, nextConfig: ChartGenerationConfig, label: string) => {
        configMemoryRef.current[selectedType] = config;
        configMemoryRef.current[type] = nextConfig;
        setSelectedType(type);
        setConfig(nextConfig);
        await generateChart({ type, config: nextConfig });
        toast.success(`已切换到：${label}`);
    };

    const explorationOptions = (() => {
        if (!profile || (!sourceRuleFields.x && !sourceRuleFields.y)) return [];

        const numericCols = profile.numeric_cols ?? [];
        const categoricalCols = profile.categorical_cols ?? [];
        const allCols = profile.columns ?? [];
        const xField = sourceRuleFields.x && allCols.includes(sourceRuleFields.x) ? sourceRuleFields.x : '';
        const yField = sourceRuleFields.y && allCols.includes(sourceRuleFields.y) ? sourceRuleFields.y : '';
        const xIsNumeric = xField ? numericCols.includes(xField) : false;
        const yIsNumeric = yField ? numericCols.includes(yField) : false;
        const xIsCategorical = xField ? categoricalCols.includes(xField) : false;
        const fallbackNumeric = numericCols.find(col => col !== xField) ?? numericCols[0] ?? '';
        const options: Array<{ key: string; label: string; description: string; type: string; config: ChartGenerationConfig }> = [];

        if (xField && yField && xIsNumeric && yIsNumeric) {
            options.push({
                key: 'scatter-dual',
                label: '切到散点关系',
                description: '保留当前双数值字段，查看离散分布与趋势线。',
                type: 'scatter',
                config: {
                    ...defaultChartConfig,
                    x_col: xField,
                    y_col: yField,
                    add_trendline: true,
                    show_regression_info: true,
                }
            });
            options.push({
                key: 'line-dual',
                label: '切到趋势分析',
                description: '把同一对字段改成趋势视角，便于查看波动变化。',
                type: 'line',
                config: {
                    ...defaultChartConfig,
                    x_col: xField,
                    y_col: yField,
                    show_markers: true,
                    add_trendline: true,
                    trendline_window: 5,
                }
            });
        }

        if (xField && yField && xIsCategorical && yIsNumeric) {
            options.push({
                key: 'bar-pair',
                label: '切到分类排行',
                description: '按来源规则字段生成分类对数值汇总柱状图。',
                type: 'bar',
                config: {
                    ...defaultChartConfig,
                    x_col: xField,
                    y_col: yField,
                    top_n: 12,
                    xaxis_angle: -30,
                }
            });
            options.push({
                key: 'box-pair',
                label: '切到箱线分布',
                description: '查看各分类下的数值分布、离群点和四分位区间。',
                type: 'box',
                config: {
                    ...defaultChartConfig,
                    x_col: yField,
                    y_col: xField,
                    show_points: true,
                }
            });
        }

        if (xField && xIsNumeric) {
            options.push({
                key: 'dist-primary',
                label: `只看 ${xField} 分布`,
                description: '聚焦来源主字段本身，快速补看单变量分布形态。',
                type: 'distribution',
                config: {
                    ...defaultChartConfig,
                    x_col: xField,
                    y_col: '',
                    bins: 30,
                }
            });
        } else if (yField && yIsNumeric) {
            options.push({
                key: 'dist-secondary',
                label: `只看 ${yField} 分布`,
                description: '聚焦来源副字段本身，补看频数与偏态信息。',
                type: 'distribution',
                config: {
                    ...defaultChartConfig,
                    x_col: yField,
                    y_col: '',
                    bins: 30,
                }
            });
        }

        if (xField && !yField && xIsCategorical && fallbackNumeric) {
            options.push({
                key: 'bar-fallback',
                label: '补一个数值视角',
                description: `使用 ${fallbackNumeric} 作为值轴，为当前分类字段生成排行图。`,
                type: 'bar',
                config: {
                    ...defaultChartConfig,
                    x_col: xField,
                    y_col: fallbackNumeric,
                    top_n: 12,
                    xaxis_angle: -30,
                }
            });
        }

        return options
            .filter(option => option.type !== selectedType || option.config.x_col !== config.x_col || option.config.y_col !== config.y_col)
            .slice(0, 3);
    })();


    const generateChart = async (overrides?: { type?: string; config?: ChartGenerationConfig }) => {
        const activeType = overrides?.type ?? selectedType;
        const activeConfig = overrides?.config ?? config;
        const requiresPrimaryColumn = activeType !== 'correlation_heatmap' && activeType !== 'network';
        const requiresSecondaryColumn = ['scatter', 'line'].includes(activeType);

        if (requiresPrimaryColumn && !activeConfig.x_col) {
            toast.warning('请先选择图表的主维度字段。');
            return;
        }

        if (requiresSecondaryColumn && !activeConfig.y_col) {
            toast.warning('当前图表类型需要选择副维度字段。');
            return;
        }

        if (activeType === 'network' && rulesData.length === 0) {
            toast.warning('暂无可用规则网络数据，请先完成一次分析任务。');
            return;
        }
        setLoading(true);
        setChartHtml('');
        setChartMeta(null);
        try {
            const payload = {
                chart_type: activeType,
                use_current_data: !sourceTaskId,
                task_id: sourceTaskId || undefined,
                x_col: activeConfig.x_col,
                y_col: activeConfig.y_col || undefined,
                column: activeConfig.x_col,
                value_col: activeConfig.x_col,
                group_col: activeConfig.y_col || undefined,
                rules_data: activeType === 'network' ? rulesData : undefined,
                config: {
                    add_trendline: activeConfig.add_trendline,
                    show_regression_info: activeConfig.show_regression_info,
                    method: activeConfig.method,
                    colorscale: activeConfig.colorscale,
                    bins: activeConfig.bins,
                    top_n: activeConfig.top_n,
                    xaxis_angle: activeConfig.xaxis_angle,
                    show_points: activeConfig.show_points,
                    show_markers: activeConfig.show_markers,
                    trendline_window: activeConfig.trendline_window,
                    width: document.getElementById('chart-wrap')?.clientWidth || 800,
                    height: 600
                }
            };

            const res = await visualizationService.createChart(payload);
            if (res.success) {
                const responseData = (res.data ?? {}) as Record<string, unknown>;
                const nestedData = (responseData.data ?? {}) as Record<string, unknown>;
                const nextChartHtml = typeof responseData.chart_html === 'string'
                    ? responseData.chart_html
                    : (typeof nestedData.chart_html === 'string' ? nestedData.chart_html : '');
                const nextMetadata = (responseData.metadata ?? nestedData.metadata ?? null) as ChartMeta | null;

                if (!nextChartHtml) {
                    throw new Error('图表接口返回成功，但未生成可渲染的图表内容');
                }

                setChartHtml(nextChartHtml);
                setChartMeta(nextMetadata);
                if (
                    activeType === 'scatter'
                    && nextMetadata?.sampling_info?.sampled
                ) {
                    toast.info(
                        `散点图已自动抽样展示 ${nextMetadata.sampling_info.displayed_points.toLocaleString()} / ${nextMetadata.sampling_info.total_points.toLocaleString()} 个点，以提升浏览器渲染性能。`
                    );
                }
                if (
                    activeType === 'bar'
                    && nextMetadata?.category_limit_info?.truncated
                ) {
                    toast.info(
                        `柱状图已自动限制为前 ${nextMetadata.category_limit_info.displayed_categories} 个类别展示，原始类别数为 ${nextMetadata.category_limit_info.total_categories_before_limit}。`
                    );
                }
                if (
                    activeType === 'network'
                    && nextMetadata?.network_limit_info?.truncated
                ) {
                    toast.info(
                        `网络图已优先展示 ${nextMetadata.network_limit_info.displayed_rules} / ${nextMetadata.network_limit_info.total_rules_before_limit} 条高价值规则，以保证交互流畅。`
                    );
                }
                if (
                    activeType === 'dashboard'
                    && nextMetadata?.dashboard_limit_info?.row_sampled
                ) {
                    toast.info(
                        `仪表板已抽样展示 ${nextMetadata.dashboard_limit_info.displayed_rows.toLocaleString()} / ${nextMetadata.dashboard_limit_info.total_rows.toLocaleString()} 行数据，以提升整体响应速度。`
                    );
                }
            }
        } catch (e) {
            toast.error(extractErrorMessage(e, '绘制引擎出错，请检查列名指定或数据类型是否支持。'));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!profile) return;
        const querySignature = searchParams.toString();
        if (!querySignature || querySignature === lastAppliedQueryRef.current) return;

        const preset = searchParams.get('preset');
        const chart = searchParams.get('chart');
        const auto = searchParams.get('auto') === '1';
        const sourceRule = searchParams.get('source_rule');
        const sourceRuleKeyParam = searchParams.get('source_rule_key') ?? '';
        const sourceTaskIdParam = searchParams.get('task_id') ?? '';
        const xCol = searchParams.get('x') ?? '';
        const yCol = searchParams.get('y') ?? '';

        setSourceRuleText(sourceRule ?? '');
        setSourceRuleFields({ x: xCol, y: yCol });
        setSourceRuleKey(sourceRuleKeyParam);
        setSourceTaskId(sourceTaskIdParam);

        if (!preset && !chart) {
            lastAppliedQueryRef.current = querySignature;
            setSearchParams({}, { replace: true });
            return;
        }
        if ((preset === 'rule_network' || chart === 'network') && rulesData.length === 0) return;

        let nextType = chart || selectedType;
        let nextConfig = config;

        if (preset === 'rule_auto') {
            const applied = resolveAutoRulePreset(xCol, yCol);
            nextType = applied.type;
            nextConfig = applied.config;
            configMemoryRef.current[selectedType] = config;
            configMemoryRef.current[applied.type] = applied.config;
            setSelectedType(applied.type);
            setConfig(applied.config);
        } else if (preset) {
            const applied = applyPreset(preset, { silent: true });
            if (!applied) return;
            nextType = applied.type;
            nextConfig = applied.config;
        } else if (chart && chart !== selectedType) {
            const rememberedConfig = configMemoryRef.current[chart] ?? { ...defaultChartConfig };
            configMemoryRef.current[selectedType] = config;
            configMemoryRef.current[chart] = rememberedConfig;
            setSelectedType(chart);
            setConfig(rememberedConfig);
            nextType = chart;
            nextConfig = rememberedConfig;
        }

        if (xCol || yCol) {
            nextConfig = {
                ...nextConfig,
                x_col: xCol || nextConfig.x_col,
                y_col: yCol || nextConfig.y_col,
            };
            configMemoryRef.current[nextType] = nextConfig;
            setConfig(nextConfig);
        }
        lastAppliedQueryRef.current = querySignature;
        if (auto) {
            window.setTimeout(() => {
                void generateChart({ type: nextType, config: nextConfig });
            }, 0);
        }
        setSearchParams({}, { replace: true });
    }, [profile, rulesData, searchParams, setSearchParams, selectedType, config]);
    const buildSourceRuleVisualizationUrl = (rule: AssociationRule, mode: 'auto' | 'network' = 'auto') => {
        const params = new URLSearchParams();
        if (sourceTaskId) params.set('task_id', sourceTaskId);
        params.set('source_rule_key', getRuleKey(rule));
        params.set('source_rule', getRuleSummary(rule));

        if (mode === 'network' || !hasRulePair(rule)) {
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

    const featuredSourceRules = rulesData.slice(0, 5);
    const sourceNavigationInfo = (() => {
        if (!sourceRuleKey || featuredSourceRules.length === 0) return null;
        const currentIndex = featuredSourceRules.findIndex(rule => getRuleKey(rule) === sourceRuleKey);
        if (currentIndex < 0) return null;
        return {
            currentIndex,
            total: featuredSourceRules.length,
            previousRule: currentIndex > 0 ? featuredSourceRules[currentIndex - 1] : null,
            nextRule: currentIndex < featuredSourceRules.length - 1 ? featuredSourceRules[currentIndex + 1] : null,
        };
    })();

    const handleNavigateSourceRule = (rule: AssociationRule) => {
        const mode = selectedType === 'network' ? 'network' : 'auto';
        navigate(buildSourceRuleVisualizationUrl(rule, mode));
    };

    const getDownloadFailureAction = (): DownloadFailureAction | null => {
        if (downloadStatus.state !== 'error' || activeDownload) return null;

        if (downloadStatus.hint === '导出依赖未就绪' || downloadStatus.hint === '后端导出服务异常') {
            if (downloadStatus.type !== 'html' && chartHtml) {
                return {
                    label: '改用 HTML',
                    reason: '可先绕开图片导出链路，优先保留当前图表结果。',
                    onClick: () => { void handleDownloadChart(); },
                };
            }
            return {
                label: '新窗口查看',
                reason: '先直接打开当前图表，避免继续卡在导出服务。',
                onClick: handleOpenChartInNewTab,
            };
        }

        if (downloadStatus.hint === '导出服务响应超时') {
            return {
                label: '重新尝试',
                reason: '这类超时多为瞬时波动，重试一次通常即可恢复。',
                onClick: () => { void handleRetryDownload(); },
            };
        }

        if (downloadStatus.hint === '权限或浏览器拦截') {
            return {
                label: '新窗口查看',
                reason: '可绕过当前下载拦截，先确认图表内容本身可正常访问。',
                onClick: handleOpenChartInNewTab,
            };
        }

        return {
            label: '重新尝试',
            reason: '先做一次快速重试，能更快判断是否只是临时异常。',
            onClick: () => { void handleRetryDownload(); },
        };
    };


    return (
        <div className="max-w-[1400px] mx-auto py-8 px-4 h-full flex flex-col">
            <div className="mb-6 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-4">
                    <div className="bg-gradient-to-br from-[#2383e2] to-indigo-600 p-3 rounded-xl text-white shadow-lg shadow-blue-500/20">
                        <PieChart size={28} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-[#37352f]">可视化图表</h1>
                        <p className="text-[#787774] text-sm mt-1">自如排布各项字段刻面，依托底层海量算法探查空间统计学深层特征。</p>
                    </div>
                </div>
            </div>

            {sourceRuleText && (
                <div className="mb-5 rounded-xl border border-blue-100 bg-gradient-to-r from-blue-50 to-indigo-50 px-4 py-3 text-sm text-[#4f4e49] shadow-sm">
                    <div className="flex items-start gap-3">
                        <div className="mt-0.5 rounded-lg bg-white p-2 text-[#2383e2] border border-blue-100">
                            <BarChart3 size={16} />
                        </div>
                        <div className="min-w-0">
                            <div className="text-[11px] font-black uppercase tracking-widest text-[#2383e2]">来源规则联动</div>
                            <div className="mt-1 font-medium break-words">{sourceRuleText}</div>
                            <div className="mt-1 text-xs text-[#787774]">当前图表已根据来源规则的字段组合自动选择更合适的可视化预设，你也可以继续手动调整。</div>
                            <div className="mt-3 flex flex-wrap gap-2">
                                <button
                                    type="button"
                                    onClick={handleReapplySourceRecommendation}
                                    className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-indigo-600 hover:bg-indigo-50 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/40 active:scale-[0.97]"
                                >
                                    <Wand2 size={12} />
                                    按规则推荐
                                </button>
                                <button
                                    type="button"
                                    onClick={handleLockCurrentFields}
                                    className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-emerald-600 hover:bg-emerald-50 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/40 active:scale-[0.97]"
                                >
                                    <Type size={12} />
                                    锁定当前字段
                                </button>
                                <button
                                    type="button"
                                    onClick={() => navigate(sourceTaskId ? `/analysis_result?task_id=${encodeURIComponent(sourceTaskId)}${sourceRuleKey ? `&focus_rule=${encodeURIComponent(sourceRuleKey)}` : ''}` : '/analysis_result')}
                                    className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-white px-3 py-1.5 text-[12px] font-semibold text-[#2383e2] hover:bg-blue-50 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]"
                                >
                                    <RotateCcw size={12} />
                                    返回分析结果
                                </button>
                            </div>
                            {sourceNavigationInfo && (
                                <div className="mt-4 rounded-xl border border-[#dbe7ff] bg-white/75 p-3 shadow-sm">
                                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                                        <div className="min-w-0">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <span className="inline-flex items-center rounded-full bg-[#eef6ff] px-2.5 py-1 text-[10px] font-black text-[#2383e2]">
                                                    重点规则 {sourceNavigationInfo.currentIndex + 1} / {sourceNavigationInfo.total}
                                                </span>
                                                <span className="text-[12px] font-medium text-[#4f4e49]">
                                                    当前正在查看第 {sourceNavigationInfo.currentIndex + 1} 条重点规则，可直接切换相邻规则。
                                                </span>
                                            </div>
                                            <div className="mt-1 text-[11px] text-[#787774]">
                                                切换时会沿用当前浏览语境：{selectedType === 'network' ? '规则网络' : '规则推荐联动图'}。
                                            </div>
                                        </div>
                                        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                                            <button
                                                type="button"
                                                onClick={() => sourceNavigationInfo.previousRule && handleNavigateSourceRule(sourceNavigationInfo.previousRule)}
                                                disabled={!sourceNavigationInfo.previousRule}
                                                className="inline-flex items-center gap-1.5 rounded-lg border border-[#dbe7ff] bg-white px-3 py-1.5 text-[12px] font-semibold text-[#2383e2] transition-all hover:bg-[#f5f9ff] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]"
                                            >
                                                <ChevronLeft size={12} />
                                                上一条
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => sourceNavigationInfo.nextRule && handleNavigateSourceRule(sourceNavigationInfo.nextRule)}
                                                disabled={!sourceNavigationInfo.nextRule}
                                                className="inline-flex items-center gap-1.5 rounded-lg border border-[#dbe7ff] bg-white px-3 py-1.5 text-[12px] font-semibold text-[#2383e2] transition-all hover:bg-[#f5f9ff] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]"
                                            >
                                                下一条
                                                <ChevronRight size={12} />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
                            {explorationOptions.length > 0 && (
                                <div className="mt-4 rounded-xl border border-white/80 bg-white/70 p-3">
                                    <div className="flex items-center gap-2 text-[11px] font-black uppercase tracking-widest text-[#7c3aed]">
                                        <GitBranchPlus size={12} />
                                        连续探索建议
                                    </div>
                                    <div className="mt-2 grid gap-2 md:grid-cols-3">
                                        {explorationOptions.map((option) => (
                                            <button
                                                key={option.key}
                                                type="button"
                                                onClick={() => { void handleApplyExplorationView(option.type, option.config, option.label); }}
                                                className="rounded-xl border border-[#ebe7ff] bg-white px-3 py-2 text-left shadow-sm transition-all hover:bg-[#faf7ff] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7c3aed]/30 active:scale-[0.98]"
                                            >
                                                <div className="text-[12px] font-semibold text-[#4c1d95]">{option.label}</div>
                                                <div className="mt-1 text-[11px] leading-relaxed text-[#787774]">{option.description}</div>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 sm:gap-6 flex-1 min-h-0">
                {/* 左侧控制栏 */}
                <div className="lg:col-span-1 border border-[#e9e9e8] bg-[#fbfbfa] rounded-xl flex flex-col shrink-0 overflow-y-auto shadow-sm max-h-none lg:max-h-[calc(100vh-180px)]">
                    <div className="p-4 border-b border-[#e9e9e8] bg-white text-[#37352f] font-bold flex items-center gap-2">
                        <Filter size={18} /> 图表配置面板
                    </div>

                    <div className="p-4 space-y-6 flex-1">
                        <div>
                            <label className="text-xs font-semibold text-[#787774] mb-2 block uppercase tracking-wider">选择投影形态</label>
                            <div className="flex flex-col gap-2">
                                {chartTypes.map(c => (
                                    <button
                                        key={c.id}
                                        onClick={() => handleSelectType(c.id)}
                                        className={cn(
                                            "flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.98]",
                                            selectedType === c.id
                                                ? "bg-[#2383e2] text-white shadow-md border-transparent"
                                                : "border border-[#e9e9e8] bg-white text-[#37352f] hover:bg-[#f5f5f4]"
                                        )}
                                    >
                                        <c.icon size={16} className={cn(selectedType === c.id ? "text-white" : c.color)} /> {c.name}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="pt-4 border-t border-[#e9e9e8]">
                            <label className="text-xs font-semibold text-[#787774] mb-2 block uppercase tracking-wider">一键预设</label>
                            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-2 gap-2">
                                {[
                                    { id: 'correlation_overview', label: '相关总览' },
                                    { id: 'numeric_scatter', label: '散点关系' },
                                    { id: 'single_distribution', label: '单维分布' },
                                    { id: 'category_ranking', label: '分类排行' },
                                    { id: 'trend_line', label: '趋势分析' },
                                    { id: 'rule_network', label: '规则网络' },
                                ].map((preset) => (
                                    <button
                                        key={preset.id}
                                        type="button"
                                        onClick={() => applyPreset(preset.id)}
                                        className="flex items-center justify-center gap-1.5 rounded-lg border border-[#e9e9e8] bg-white px-2.5 py-2 text-[12px] font-medium text-[#4f4e49] transition-all hover:bg-[#f5f5f4] hover:text-[#2383e2] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]"
                                    >
                                        <Wand2 size={13} />
                                        {preset.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {selectedType !== 'correlation_heatmap' && profile && (
                            <div className="space-y-4 animate-in fade-in pt-4 border-t border-[#e9e9e8]">
                                <div>
                                    <label className="text-xs font-semibold text-[#787774] mb-2 block flex items-center gap-1"><Type size={12} /> 主维度 (X / 值)</label>
                                    <select
                                        className="w-full text-sm p-2 border border-[#e9e9e8] rounded outline-none focus:border-[#2383e2] focus:ring-2 focus:ring-[#2383e2]/20 transition-shadow"
                                        value={config.x_col}
                                        onChange={e => setRememberedConfig({ ...config, x_col: e.target.value })}
                                    >
                                        <option value="">-- 请选择 --</option>
                                        {primaryColumnOptions.map((col) => <option key={col} value={col}>{col}</option>)}
                                    </select>
                                </div>
                                {['scatter', 'line', 'box', 'bar'].includes(selectedType) && (
                                    <div>
                                        <label className="text-xs font-semibold text-[#787774] mb-2 block flex items-center gap-1"><Type size={12} /> {['scatter', 'line'].includes(selectedType) ? '副维度 (Y)' : '副维度 / 分组 (可选)'}</label>
                                        <select
                                            className="w-full text-sm p-2 border border-[#e9e9e8] rounded outline-none focus:border-[#2383e2] focus:ring-2 focus:ring-[#2383e2]/20 transition-shadow"
                                            value={config.y_col}
                                            onChange={e => setRememberedConfig({ ...config, y_col: e.target.value })}
                                        >
                                            <option value="">-- 请选择 --</option>
                                            {secondaryColumnOptions.map((col) => <option key={col} value={col}>{col}</option>)}
                                        </select>
                                    </div>
                                )}
                            </div>
                        )}

                        {selectedType === 'correlation_heatmap' && (
                            <div className="space-y-3 pt-4 border-t border-[#e9e9e8]">
                                <div>
                                    <label className="text-xs font-semibold text-[#787774] mb-2 block">相关系数方法</label>
                                    <select className="w-full text-sm p-2 border border-[#e9e9e8] rounded outline-none focus:border-[#2383e2] focus:ring-2 focus:ring-[#2383e2]/20 transition-shadow" value={config.method} onChange={e => setRememberedConfig({ ...config, method: e.target.value as ChartGenerationConfig['method'] })}>
                                        <option value="pearson">Pearson</option>
                                        <option value="spearman">Spearman</option>
                                        <option value="kendall">Kendall</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs font-semibold text-[#787774] mb-2 block">色板</label>
                                    <select className="w-full text-sm p-2 border border-[#e9e9e8] rounded outline-none focus:border-[#2383e2] focus:ring-2 focus:ring-[#2383e2]/20 transition-shadow" value={config.colorscale} onChange={e => setRememberedConfig({ ...config, colorscale: e.target.value as ChartGenerationConfig['colorscale'] })}>
                                        <option value="RdBu_r">RdBu_r</option>
                                        <option value="viridis">viridis</option>
                                        <option value="plasma">plasma</option>
                                    </select>
                                </div>
                            </div>
                        )}

                        {selectedType === 'distribution' && (
                            <div className="space-y-3 pt-4 border-t border-[#e9e9e8]">
                                <label className="text-xs font-semibold text-[#787774] mb-2 block">分箱数: {config.bins}</label>
                                <input type="range" min="10" max="80" step="1" className="w-full accent-[#2383e2]" value={config.bins} onChange={e => setRememberedConfig({ ...config, bins: Number(e.target.value) })} />
                            </div>
                        )}

                        {selectedType === 'bar' && (
                            <div className="space-y-3 pt-4 border-t border-[#e9e9e8]">
                                <label className="text-xs font-semibold text-[#787774] mb-2 block">Top N: {config.top_n}</label>
                                <input type="range" min="5" max="50" step="1" className="w-full accent-[#2383e2]" value={config.top_n} onChange={e => setRememberedConfig({ ...config, top_n: Number(e.target.value) })} />
                                <label className="text-xs font-semibold text-[#787774] mb-2 block">X 轴角度: {config.xaxis_angle}°</label>
                                <input type="range" min="-90" max="0" step="5" className="w-full accent-[#2383e2]" value={config.xaxis_angle} onChange={e => setRememberedConfig({ ...config, xaxis_angle: Number(e.target.value) })} />
                            </div>
                        )}

                        {selectedType === 'box' && (
                            <div className="space-y-3 pt-4 border-t border-[#e9e9e8]">
                                <label className="flex items-center gap-2 text-sm text-[#37352f] cursor-pointer">
                                    <input type="checkbox" className="accent-[#2383e2]" checked={config.show_points} onChange={e => setRememberedConfig({ ...config, show_points: e.target.checked })} />
                                    显示异常点
                                </label>
                            </div>
                        )}

                        {selectedType === 'line' && (
                            <div className="space-y-3 pt-4 border-t border-[#e9e9e8]">
                                <label className="flex items-center gap-2 text-sm text-[#37352f] cursor-pointer">
                                    <input type="checkbox" className="accent-[#2383e2]" checked={config.show_markers} onChange={e => setRememberedConfig({ ...config, show_markers: e.target.checked })} />
                                    显示标记点
                                </label>
                                <label className="flex items-center gap-2 text-sm text-[#37352f] cursor-pointer">
                                    <input type="checkbox" className="accent-[#2383e2]" checked={config.add_trendline} onChange={e => setRememberedConfig({ ...config, add_trendline: e.target.checked })} />
                                    显示移动平均趋势线
                                </label>
                                <label className="text-xs font-semibold text-[#787774] mb-2 block">趋势窗口: {config.trendline_window}</label>
                                <input type="range" min="2" max="20" step="1" className="w-full accent-[#2383e2]" value={config.trendline_window} onChange={e => setRememberedConfig({ ...config, trendline_window: Number(e.target.value) })} />
                            </div>
                        )}

                        {selectedType === 'scatter' && (
                            <div className="space-y-3 pt-4 border-t border-[#e9e9e8]">
                                <label className="flex items-center gap-2 text-sm text-[#37352f] cursor-pointer">
                                    <input type="checkbox" className="accent-[#2383e2]" checked={config.add_trendline} onChange={e => setRememberedConfig({ ...config, add_trendline: e.target.checked })} />
                                    显示趋势线
                                </label>
                                <label className="flex items-center gap-2 text-sm text-[#37352f] cursor-pointer">
                                    <input type="checkbox" className="accent-[#2383e2]" checked={config.show_regression_info} onChange={e => setRememberedConfig({ ...config, show_regression_info: e.target.checked })} />
                                    显示回归统计信息 (R², P 值)
                                </label>
                            </div>
                        )}

                        <div className="pt-4 mt-2">
                            <div className="flex gap-2">
                                <Button
                                    onClick={() => generateChart()}
                                    disabled={loading}
                                    className="flex-1"
                                >
                                    {loading ? <RefreshCw size={16} className="animate-spin" /> : <BarChart3 size={16} />}
                                    生成图表
                                </Button>
                                <button
                                    onClick={handleResetCurrentChartConfig}
                                    type="button"
                                    className="px-3 rounded-lg border border-[#e9e9e8] bg-white text-[#787774] hover:bg-[#f5f5f4] hover:text-[#37352f] transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]"
                                    title="重置当前图表配置"
                                >
                                    <RotateCcw size={15} />
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 右侧展示区 */}
                <div id="chart-wrap" ref={viewerRef} className="lg:col-span-3 bg-white border border-[#e9e9e8] rounded-xl relative flex flex-col overflow-hidden shadow-sm min-w-0">
                    {/* Header bar */}
                    <div className="min-h-11 border-b border-[#e9e9e8] bg-[#fbfbfa] flex flex-col px-3 sm:px-4 py-2 shrink-0 gap-2">
                        <div className="flex items-center gap-3 min-w-0">
                            <div className="flex gap-1.5 items-center shrink-0">
                                <div className="w-3 h-3 rounded-full bg-red-400"></div>
                                <div className="w-3 h-3 rounded-full bg-amber-400"></div>
                                <div className="w-3 h-3 rounded-full bg-green-400"></div>
                            </div>
                            <div className="min-w-0">
                                <div className="text-[11px] text-[#b4b4b3] font-mono tracking-wider truncate">
                                    {chartTypes.find(c => c.id === selectedType)?.name || '请选择图表类型'}
                                </div>
                                {sourceRuleText && (
                                    <div className="mt-0.5 flex items-center gap-2 min-w-0">
                                        <span className="inline-flex items-center rounded-full bg-[#eef6ff] px-2 py-0.5 text-[10px] font-black text-[#2383e2] shrink-0">
                                            来源规则
                                        </span>
                                        <span className="text-[11px] text-[#787774] truncate" title={sourceRuleText}>
                                            {sourceRuleText}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="flex w-full flex-col items-stretch gap-2">
                            {(() => {
                                const notice = getStatusNoticeMeta();
                                if (!notice) return null;
                                const StatusIcon = notice.icon;
                                const progressSteps = getDownloadProgressSteps(downloadStatus.stage || 'prepare', downloadStatus.state);
                                const suggestedFailureAction = getDownloadFailureAction();
                                const shouldShowSuggestedAction = downloadStatus.state === 'error' && !activeDownload && Boolean(suggestedFailureAction);
                                const shouldShowRetryAction = downloadStatus.state === 'error' && !activeDownload && suggestedFailureAction?.label !== '重新尝试';
                                return (
                                    <div className={cn(
                                        "w-full xl:min-w-[360px] xl:max-w-[520px] rounded-xl border shadow-sm backdrop-blur-sm",
                                        notice.tone === 'success'
                                            ? "border-emerald-200/80 bg-emerald-50/95 text-emerald-900"
                                            : notice.tone === 'error'
                                                ? "border-rose-200/80 bg-rose-50/95 text-rose-900"
                                                : "border-sky-200/80 bg-sky-50/95 text-sky-900"
                                    )}>
                                        <div className="flex flex-col gap-3 px-3.5 py-3 sm:flex-row sm:items-start">
                                            <div className="flex min-w-0 items-start gap-3 flex-1">
                                                <div className={cn(
                                                    "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-white/80 shadow-sm",
                                                    notice.tone === 'success'
                                                        ? "border-emerald-200 text-emerald-600"
                                                        : notice.tone === 'error'
                                                            ? "border-rose-200 text-rose-600"
                                                            : "border-sky-200 text-sky-600"
                                                )}>
                                                    <StatusIcon size={15} className={cn(activeDownload ? 'animate-spin' : '')} />
                                                </div>
                                                <div className="min-w-0 flex-1">
                                                    <div className="flex flex-wrap items-center gap-2">
                                                        <span className="inline-flex items-center rounded-full border border-current/10 bg-white/70 px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.2em]">
                                                            system notice
                                                        </span>
                                                        <span className="inline-flex items-center rounded-full border border-current/10 bg-white/70 px-2 py-0.5 text-[10px] font-black">
                                                            {notice.stageLabel}
                                                        </span>
                                                        <span className="text-[12px] font-bold leading-none">
                                                            {notice.title}
                                                        </span>
                                                    </div>
                                                    <p className="mt-1 text-[11px] leading-5 text-current/80 break-words">
                                                        {notice.detail}
                                                    </p>
                                                    {downloadStatus.state === 'error' && !activeDownload && suggestedFailureAction && (
                                                        <div className="mt-2 rounded-lg border border-current/10 bg-white/55 px-2.5 py-2">
                                                            <div className="flex flex-wrap items-center gap-2">
                                                                {notice.hint && (
                                                                    <span className="inline-flex items-center rounded-md border border-current/10 bg-white/80 px-2 py-0.5 text-[10px] font-black text-current/80">
                                                                        {notice.hint}
                                                                    </span>
                                                                )}
                                                                <span className="inline-flex items-center rounded-md border border-current/10 bg-white/80 px-2 py-0.5 text-[10px] font-black text-current/90">
                                                                    推荐动作 · {suggestedFailureAction.label}
                                                                </span>
                                                                <span className="text-[10px] leading-5 text-current/75">
                                                                    {suggestedFailureAction.reason}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    )}
                                                    <div className="mt-2.5 flex items-center gap-2 max-[420px]:gap-1.5">
                                                        {progressSteps.map((step, index) => (
                                                            <div key={step.key} className="flex min-w-0 flex-1 items-center gap-2 max-[420px]:gap-1">
                                                                <div className="flex min-w-0 items-center gap-2 max-[420px]:gap-1">
                                                                    <span className={cn(
                                                                        "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-black transition-all duration-200",
                                                                        notice.tone === 'error' && step.isCurrent
                                                                            ? "border-rose-300 bg-rose-100 text-rose-700"
                                                                            : step.isComplete
                                                                                ? "border-current/15 bg-white/85 text-current"
                                                                                : step.isCurrent
                                                                                    ? "border-current/15 bg-white/85 text-current shadow-sm"
                                                                                    : "border-current/10 bg-white/50 text-current/55"
                                                                    )}>
                                                                        {index + 1}
                                                                    </span>
                                                                    <span className={cn(
                                                                        "text-[10px] font-bold transition-colors duration-200",
                                                                        step.isComplete || step.isCurrent ? "text-current/90" : "text-current/55"
                                                                    )}>
                                                                        {step.label}
                                                                    </span>
                                                                </div>
                                                                {index < progressSteps.length - 1 && (
                                                                    <span className={cn(
                                                                        "h-px flex-1 rounded-full transition-all duration-200",
                                                                        progressSteps[index + 1].isComplete || progressSteps[index + 1].isCurrent
                                                                            ? "bg-current/35"
                                                                            : "bg-current/15"
                                                                    )} />
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                    {!activeDownload && (
                                                        <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-current/10 pt-2.5 sm:hidden">
                                                            {shouldShowSuggestedAction && suggestedFailureAction && (
                                                                <button
                                                                    type="button"
                                                                    onClick={suggestedFailureAction.onClick}
                                                                    className="rounded-lg border border-current/15 bg-white/90 px-2.5 py-1 text-[10px] font-bold transition-all hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current/30 active:scale-[0.97]"
                                                                >
                                                                    {suggestedFailureAction.label}
                                                                </button>
                                                            )}
                                                            {shouldShowRetryAction && (
                                                                <button
                                                                    type="button"
                                                                    onClick={() => { void handleRetryDownload(); }}
                                                                    className="rounded-lg border border-current/15 bg-white/80 px-2.5 py-1 text-[10px] font-bold transition-all hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current/30 active:scale-[0.97]"
                                                                >
                                                                    重试
                                                                </button>
                                                            )}
                                                            <button
                                                                type="button"
                                                                onClick={() => setDownloadStatus({ type: '', state: 'idle', stage: '', message: '', hint: '' })}
                                                                className="ml-auto rounded-lg p-1.5 text-current/70 transition-all hover:bg-white/80 hover:text-current focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current/30"
                                                                title="关闭提示"
                                                            >
                                                                <X size={13} />
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                            <div className="hidden shrink-0 items-center gap-1 sm:flex">
                                                {shouldShowSuggestedAction && suggestedFailureAction && (
                                                    <button
                                                        type="button"
                                                        onClick={suggestedFailureAction.onClick}
                                                        className="rounded-lg border border-current/15 bg-white/90 px-2.5 py-1 text-[10px] font-bold transition-all hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current/30 active:scale-[0.97]"
                                                    >
                                                        {suggestedFailureAction.label}
                                                    </button>
                                                )}
                                                {shouldShowRetryAction && (
                                                    <button
                                                        type="button"
                                                        onClick={() => { void handleRetryDownload(); }}
                                                        className="rounded-lg border border-current/15 bg-white/80 px-2.5 py-1 text-[10px] font-bold transition-all hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current/30 active:scale-[0.97]"
                                                    >
                                                        重试
                                                    </button>
                                                )}
                                                {!activeDownload && (
                                                    <button
                                                        type="button"
                                                        onClick={() => setDownloadStatus({ type: '', state: 'idle', stage: '', message: '', hint: '' })}
                                                        className="rounded-lg p-1.5 text-current/70 transition-all hover:bg-white/80 hover:text-current focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current/30"
                                                        title="关闭提示"
                                                    >
                                                        <X size={13} />
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })()}
                            <div className="flex w-full flex-wrap items-center gap-2">
                                <div className="flex items-center gap-1 rounded-xl border border-[#e9e9e8] bg-white px-1.5 py-1 shadow-sm max-[390px]:gap-0.5 max-[390px]:px-1">
                                    <span className="hidden sm:inline-flex px-1.5 text-[10px] font-black uppercase tracking-widest text-[#b4b4b3]">缩放</span>
                                    <div className="flex min-w-0 items-center gap-1 rounded-lg border border-[#e9e9e8] bg-[#fcfcfb] px-1 py-1 max-[390px]:gap-0.5 max-[390px]:px-0.5">
                                        <button className={cn("rounded-md px-2 py-1.5 text-[11px] font-bold transition-all disabled:opacity-50 max-[420px]:px-1.5 max-[360px]:text-[10px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]", Math.abs(zoomLevel - 0.9) < 0.001 ? "bg-[#2383e2] text-white" : "text-[#787774] hover:bg-[#f5f5f4] hover:text-[#37352f]")} title="适应宽度" onClick={handleFitWidth} disabled={!chartUrl}>
                                            <span className="max-[420px]:hidden">适应</span>
                                            <span className="hidden max-[420px]:inline">宽</span>
                                        </button>
                                        <button className={cn("rounded-md px-2 py-1.5 text-[11px] font-bold transition-all disabled:opacity-50 max-[420px]:px-1.5 max-[360px]:text-[10px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]", Math.abs(zoomLevel - 1) < 0.001 ? "bg-[#2383e2] text-white" : "text-[#787774] hover:bg-[#f5f5f4] hover:text-[#37352f]")} title="100%" onClick={() => setZoomLevel(1)} disabled={!chartUrl}>
                                            <span className="max-[420px]:hidden">100%</span>
                                            <span className="hidden max-[420px]:inline">1x</span>
                                        </button>
                                        <button className={cn("rounded-md px-2 py-1.5 text-[11px] font-bold transition-all disabled:opacity-50 max-[420px]:px-1.5 max-[360px]:text-[10px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]", Math.abs(zoomLevel - 1.5) < 0.001 ? "bg-[#2383e2] text-white" : "text-[#787774] hover:bg-[#f5f5f4] hover:text-[#37352f]")} title="150%" onClick={() => setZoomLevel(1.5)} disabled={!chartUrl}>
                                            <span className="max-[420px]:hidden">150%</span>
                                            <span className="hidden max-[420px]:inline">1.5x</span>
                                        </button>
                                    </div>
                                    <div className="flex items-center gap-1 rounded-lg border border-[#e9e9e8] bg-[#fcfcfb] px-1 py-1 max-[390px]:gap-0.5 max-[390px]:px-0.5">
                                        <button className="rounded-md p-1.5 text-[#787774] transition-all hover:bg-[#f5f5f4] hover:text-[#37352f] disabled:opacity-50 max-[390px]:p-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]" title="缩小" onClick={() => setZoomLevel(prev => Math.max(0.6, Number((prev - 0.1).toFixed(2))))} disabled={!chartUrl}>
                                            <ZoomOut size={14} />
                                        </button>
                                        <span className="min-w-[46px] px-1 text-center text-[11px] font-bold text-[#6b7280] max-[390px]:min-w-[34px] max-[390px]:text-[10px]">{Math.round(zoomLevel * 100)}%</span>
                                        <button className="rounded-md p-1.5 text-[#787774] transition-all hover:bg-[#f5f5f4] hover:text-[#37352f] disabled:opacity-50 max-[390px]:p-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]" title="放大" onClick={() => setZoomLevel(prev => Math.min(2, Number((prev + 0.1).toFixed(2))))} disabled={!chartUrl}>
                                            <ZoomIn size={14} />
                                        </button>
                                        <button className="rounded-md p-1.5 text-[#787774] transition-all hover:bg-[#f5f5f4] hover:text-[#37352f] disabled:opacity-50 max-[390px]:p-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]" title="重置比例" onClick={() => setZoomLevel(1)} disabled={!chartUrl}>
                                            <RotateCcw size={14} />
                                        </button>
                                    </div>
                                </div>
                                <div className="flex min-w-0 flex-1 items-center gap-1 rounded-xl border border-[#e9e9e8] bg-white px-1.5 py-1 shadow-sm max-[390px]:gap-0.5 max-[390px]:px-1">
                                    <span className="hidden sm:inline-flex px-1.5 text-[10px] font-black uppercase tracking-widest text-[#b4b4b3]">导出</span>
                                    <button className="rounded-lg border border-[#e9e9e8] bg-[#fcfcfb] p-2 text-[#787774] transition-all hover:bg-[#f5f5f4] hover:text-[#37352f] disabled:opacity-50 max-[390px]:p-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]" title="下载 HTML 图表" onClick={() => { void handleDownloadChart(); }} disabled={!chartUrl || !!activeDownload}>
                                        {activeDownload === 'html' ? <RefreshCw size={14} className="animate-spin" /> : <Download size={14} />}
                                    </button>
                                    <button className="rounded-lg border border-[#e9e9e8] bg-[#fcfcfb] px-2 py-2 text-[11px] font-bold text-[#787774] transition-all hover:bg-[#f5f5f4] hover:text-[#37352f] disabled:opacity-50 max-[390px]:px-1.5 max-[360px]:text-[10px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]" title="导出 PNG" onClick={() => { void handleExportPng(); }} disabled={!chartUrl || !!activeDownload}>
                                        {activeDownload === 'png' ? '下载中...' : 'PNG'}
                                    </button>
                                    <button className="hidden xl:inline-flex rounded-lg border border-[#e9e9e8] bg-[#fcfcfb] px-2 py-2 text-[11px] font-bold text-[#787774] transition-all hover:bg-[#f5f5f4] hover:text-[#37352f] disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]" title="导出 SVG" onClick={() => { void handleClientExport('svg'); }} disabled={!chartUrl || !!activeDownload}>
                                        {activeDownload === 'svg' ? '下载中...' : 'SVG'}
                                    </button>
                                    <button className="hidden xl:inline-flex rounded-lg border border-[#e9e9e8] bg-[#fcfcfb] px-2 py-2 text-[11px] font-bold text-[#787774] transition-all hover:bg-[#f5f5f4] hover:text-[#37352f] disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]" title="导出 PDF" onClick={() => { void handleExportFile('pdf'); }} disabled={!chartUrl || !!activeDownload}>
                                        {activeDownload === 'pdf' ? '下载中...' : 'PDF'}
                                    </button>
                                    {lastDownloadType && (
                                        <button
                                            className="hidden xl:inline-flex rounded-lg border border-[#dbe7ff] bg-[#f8fbff] px-2 py-2 text-[11px] font-bold text-[#2383e2] transition-all hover:bg-white disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]"
                                            title={`再次导出 ${getDownloadLabel(lastDownloadType)}`}
                                            onClick={() => { void handleRepeatLastDownload(); }}
                                            disabled={!chartUrl || !!activeDownload}
                                        >
                                            重导上次
                                        </button>
                                    )}
                                </div>
                                <div className="flex min-w-0 items-stretch justify-end gap-2 max-[390px]:gap-1">
                                    <div className="flex items-center gap-1 rounded-xl border border-[#e9e9e8] bg-white px-1.5 py-1 shadow-sm max-[390px]:gap-0.5 max-[390px]:px-1">
                                        <span className="hidden sm:inline-flex px-1.5 text-[10px] font-black uppercase tracking-widest text-[#b4b4b3]">查看</span>
                                        <button className="rounded-lg border border-[#e9e9e8] bg-[#fcfcfb] p-2 text-[#787774] transition-all hover:bg-[#f5f5f4] hover:text-[#37352f] disabled:opacity-50 max-[390px]:p-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]" title="复制当前图表配置" onClick={() => { void handleCopyChartConfig(); }} disabled={!chartUrl}>
                                            <Copy size={14} />
                                        </button>
                                        <button className="hidden xl:inline-flex rounded-lg border border-[#dbe7ff] bg-[#f8fbff] px-2 py-2 text-[11px] font-bold text-[#2383e2] transition-all hover:bg-white disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]" title="复制当前图表配置和页面链接" onClick={() => { void handleCopyChartConfigWithLink(); }} disabled={!chartUrl}>
                                            配置+链接
                                        </button>
                                        <button className="rounded-lg border border-[#e9e9e8] bg-[#fcfcfb] p-2 text-[#787774] transition-all hover:bg-[#f5f5f4] hover:text-[#37352f] disabled:opacity-50 max-[390px]:p-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]" title="新窗口打开" onClick={handleOpenChartInNewTab} disabled={!chartUrl}>
                                            <ExternalLink size={14} />
                                        </button>
                                        <button className="rounded-lg border border-[#e9e9e8] bg-[#fcfcfb] p-2 text-[#787774] transition-all hover:bg-[#f5f5f4] hover:text-[#37352f] disabled:opacity-50 max-[390px]:p-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]" title="全屏查看" onClick={handleToggleFullscreen} disabled={!chartUrl}>
                                            <Maximize2 size={14} />
                                        </button>
                                    </div>
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <button
                                                type="button"
                                                className="inline-flex items-center gap-1 rounded-xl border border-[#dbe7ff] bg-white px-3 py-2 text-[11px] font-bold text-[#2383e2] shadow-sm transition-all hover:bg-[#f8fbff] xl:hidden max-[390px]:min-w-[38px] max-[390px]:justify-center max-[390px]:gap-0 max-[390px]:px-2 max-[390px]:text-[10px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2383e2]/40 active:scale-[0.97]"
                                                disabled={!chartUrl}
                                            >
                                                <MoreHorizontal size={14} />
                                                <span className="max-[390px]:hidden">更多</span>
                                            </button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end" className="w-56">
                                            <DropdownMenuLabel>
                                                <span className="flex items-center gap-2 text-[#4f4e49]">
                                                    <span className="inline-flex h-5 w-5 items-center justify-center rounded-md bg-[#eef6ff] text-[#2383e2]">
                                                        <Download size={11} />
                                                    </span>
                                                    导出补充
                                                </span>
                                            </DropdownMenuLabel>
                                            <DropdownMenuItem onClick={() => { void handleClientExport('svg'); }} disabled={!chartUrl || !!activeDownload}>
                                                <Download size={14} />
                                                导出 SVG
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => { void handleExportFile('pdf'); }} disabled={!chartUrl || !!activeDownload}>
                                                <Download size={14} />
                                                导出 PDF
                                            </DropdownMenuItem>
                                            {lastDownloadType && (
                                                <DropdownMenuItem onClick={() => { void handleRepeatLastDownload(); }} disabled={!chartUrl || !!activeDownload}>
                                                    <RotateCcw size={14} />
                                                    重导上次
                                                </DropdownMenuItem>
                                            )}
                                            <DropdownMenuSeparator />
                                            <DropdownMenuLabel>
                                                <span className="flex items-center gap-2 text-[#4f4e49]">
                                                    <span className="inline-flex h-5 w-5 items-center justify-center rounded-md bg-[#f3f0ff] text-[#7c3aed]">
                                                        <Copy size={11} />
                                                    </span>
                                                    分享补充
                                                </span>
                                            </DropdownMenuLabel>
                                            <DropdownMenuItem onClick={() => { void handleCopyChartConfigWithLink(); }} disabled={!chartUrl}>
                                                <Copy size={14} />
                                                复制配置+链接
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="flex-1 overflow-auto flex items-center justify-center p-3 sm:p-6 bg-gradient-to-br from-white via-gray-50/40 to-blue-50/20 min-h-[360px] sm:min-h-[500px]">
                        <AnimatePresence mode="wait">
                            {loading ? (
                                <motion.div
                                    key="loading"
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.9 }}
                                    className="flex flex-col items-center gap-5 text-[#787774]"
                                >
                                    <div className="relative w-20 h-20">
                                        <div className="absolute inset-0 rounded-full border-4 border-[#e9e9e8]"></div>
                                        <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-[#2383e2] animate-spin"></div>
                                        <Activity size={24} className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[#2383e2]" />
                                    </div>
                                    <div className="text-center">
                                        <p className="text-sm font-bold text-[#37352f]">正在渲染图形引擎...</p>
                                        <p className="text-xs text-[#b4b4b3] mt-1">后端 Plotly 管线正在执行数据映射与 DOM 构建</p>
                                    </div>
                                </motion.div>
                            ) : chartUrl ? (
                                <motion.div
                                    key="chart"
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.4 }}
                                    className="w-full h-full flex justify-center items-center"
                                >
                                    <iframe
                                        ref={iframeRef}
                                        title={chartTypes.find(c => c.id === selectedType)?.name || 'chart'}
                                        src={chartUrl}
                                        className="w-full h-full min-h-[420px] sm:min-h-[620px] border-0 bg-white rounded-lg"
                                    />
                                </motion.div>
                            ) : (
                                <motion.div
                                    key="empty"
                                    initial={{ opacity: 0, y: 12 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.4 }}
                                    className="text-center py-16"
                                >
                                    <motion.div
                                        animate={{ y: [0, -6, 0] }}
                                        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                                        className="w-24 h-24 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-inner border border-blue-100/50"
                                    >
                                        <PieChart size={40} className="text-[#2383e2]/30" />
                                    </motion.div>
                                    <h3 className="text-lg font-bold text-[#37352f] mb-2">选择图表类型并渲染</h3>
                                    <p className="text-sm text-[#b4b4b3] max-w-sm mx-auto leading-relaxed">在左侧面板配置图表参数后，点击「生成图表」按钮以生成交互式可视化图表。</p>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {chartUrl && (
                        <div className="border-t border-[#e9e9e8] px-5 py-3 bg-[#fcfcfb] flex flex-wrap gap-2">
                            {chartSummaryItems.map((item) => (
                                <span key={`${item.label}-${item.value}`} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white border border-[#e9e9e8] text-[11px]">
                                    <span className="text-[#b4b4b3] font-bold">{item.label}</span>
                                    <span className="text-[#37352f] font-bold">{item.value}</span>
                                </span>
                            ))}
                            {chartMeta?.sampling_info?.sampled && (
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-[11px]">
                                    <span className="text-amber-600 font-bold">渲染优化</span>
                                    <span className="text-amber-900 font-bold">
                                        {chartMeta.sampling_info.displayed_points.toLocaleString()} / {chartMeta.sampling_info.total_points.toLocaleString()} 点
                                    </span>
                                </span>
                            )}
                            {chartMeta?.category_limit_info?.truncated && (
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-[11px]">
                                    <span className="text-amber-600 font-bold">类别裁剪</span>
                                    <span className="text-amber-900 font-bold">
                                        {chartMeta.category_limit_info.displayed_categories} / {chartMeta.category_limit_info.total_categories_before_limit} 类
                                    </span>
                                </span>
                            )}
                            {chartMeta?.network_limit_info?.truncated && (
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-[11px]">
                                    <span className="text-amber-600 font-bold">规则裁剪</span>
                                    <span className="text-amber-900 font-bold">
                                        {chartMeta.network_limit_info.displayed_rules} / {chartMeta.network_limit_info.total_rules_before_limit} 条
                                    </span>
                                </span>
                            )}
                            {chartMeta?.dashboard_limit_info?.row_sampled && (
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-[11px]">
                                    <span className="text-amber-600 font-bold">仪表板抽样</span>
                                    <span className="text-amber-900 font-bold">
                                        {chartMeta.dashboard_limit_info.displayed_rows.toLocaleString()} / {chartMeta.dashboard_limit_info.total_rows.toLocaleString()} 行
                                    </span>
                                </span>
                            )}
                        </div>
                    )}

                    {/* Enhanced Meta bar */}
                    {chartMeta?.regression_stats && (
                        <div className="border-t border-[#e9e9e8] px-5 py-4 bg-gradient-to-r from-blue-50/60 to-indigo-50/40">
                            <h4 className="text-[10px] font-black text-[#787774] uppercase tracking-widest mb-3 flex items-center gap-2">
                                <TrendingUp size={12} className="text-blue-500" />
                                回归统计数据
                            </h4>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                <div className="bg-white rounded-xl p-3 border border-blue-100/60 shadow-sm">
                                    <div className="flex items-center gap-2 mb-1">
                                        <div className="w-5 h-5 bg-blue-100 rounded-md flex items-center justify-center"><Hash size={10} className="text-blue-600" /></div>
                                        <span className="text-[9px] font-bold text-[#b4b4b3] uppercase">Pearson r</span>
                                    </div>
                                    <p className="text-lg font-black text-[#37352f] font-mono">{chartMeta.correlation?.toFixed(4)}</p>
                                </div>
                                <div className="bg-white rounded-xl p-3 border border-blue-100/60 shadow-sm">
                                    <div className="flex items-center gap-2 mb-1">
                                        <div className="w-5 h-5 bg-indigo-100 rounded-md flex items-center justify-center"><Sigma size={10} className="text-indigo-600" /></div>
                                        <span className="text-[9px] font-bold text-[#b4b4b3] uppercase">R²</span>
                                    </div>
                                    <p className="text-lg font-black text-[#37352f] font-mono">{chartMeta.regression_stats.r_squared?.toFixed(4)}</p>
                                </div>
                                <div className="bg-white rounded-xl p-3 border border-blue-100/60 shadow-sm">
                                    <div className="flex items-center gap-2 mb-1">
                                        <div className="w-5 h-5 bg-emerald-100 rounded-md flex items-center justify-center"><Activity size={10} className="text-emerald-600" /></div>
                                        <span className="text-[9px] font-bold text-[#b4b4b3] uppercase">P-value</span>
                                    </div>
                                    <p className={cn("text-lg font-black font-mono", (chartMeta.regression_stats.p_value ?? 1) < 0.05 ? "text-emerald-600" : "text-orange-500")}>
                                        {chartMeta.regression_stats.p_value?.toExponential(2)}
                                    </p>
                                </div>
                                <div className="bg-white rounded-xl p-3 border border-blue-100/60 shadow-sm">
                                    <div className="flex items-center gap-2 mb-1">
                                        <div className="w-5 h-5 bg-amber-100 rounded-md flex items-center justify-center"><ArrowDownUp size={10} className="text-amber-600" /></div>
                                        <span className="text-[9px] font-bold text-[#b4b4b3] uppercase">Slope</span>
                                    </div>
                                    <p className="text-lg font-black text-[#37352f] font-mono">{chartMeta.regression_stats.slope?.toFixed(4)}</p>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
