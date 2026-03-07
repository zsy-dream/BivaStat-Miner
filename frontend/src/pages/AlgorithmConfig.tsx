import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Settings2, BrainCircuit, RefreshCw, Calculator, Info, Sparkles, Database, Play, ChevronRight, AlertTriangle, ShieldCheck
} from 'lucide-react';
import { cn } from '../utils/cn';
import { algorithmService, dataService, extractErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import type { MiningParams, StatsParams, DataProfile, ProfileRecommendations, DataQualityAssessment, MiningDiagnostics } from '../types';

const DEFAULT_MINING_PARAMS: MiningParams = {
    min_support: 0.05,
    min_confidence: 0.4,
    min_lift: 1.0,
    max_len: 2,
    enable_pruning: true,
};

const DEFAULT_STATS_PARAMS: StatsParams = {
    test_method: 'auto',
    p_value_threshold: 0.05,
    confidence_level: 0.95,
    alternative: 'two-sided',
};

export default function AlgorithmConfig() {
    const navigate = useNavigate();
    const { toast, confirm } = useToast();
    const [runningTaskId, setRunningTaskId] = useState<string | null>(null);
    const [runningTaskProgress, setRunningTaskProgress] = useState(0);

    const [params, setParams] = useState<MiningParams>({ ...DEFAULT_MINING_PARAMS });
    const [statsParams, setStatsParams] = useState<StatsParams>({ ...DEFAULT_STATS_PARAMS });

    const [isAutoConfiguring, setIsAutoConfiguring] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [profileData, setProfileData] = useState<DataProfile | null>(null);
    const [profileAssessment, setProfileAssessment] = useState<DataQualityAssessment | null>(null);
    const [miningReadiness, setMiningReadiness] = useState<MiningDiagnostics | null>(null);
    const didAutoConfig = useRef(false);

    // 页面加载时检查是否已有运行中的任务
    useEffect(() => {
        algorithmService.getLastTask()
            .then(res => {
                if (res.success && res.task?.task_id && res.task.status === 'running') {
                    setRunningTaskId(res.task.task_id);
                    setRunningTaskProgress(res.task.progress ?? 0);
                } else {
                    setRunningTaskId(null);
                }
            })
            .catch(() => setRunningTaskId(null));
    }, []);

    // 获取并更新推荐建议
    const autoConfig = useCallback(async () => {
        setIsAutoConfiguring(true);
        setError('');
        try {
            const res = await dataService.getProfile();
            if (res.success) {
                const rec: ProfileRecommendations = res.recommendations ?? {};
                setProfileData(res.profile || null);
                setProfileAssessment(res.assessment || null);
                setMiningReadiness(res.miningReadiness || null);

                // 应用推荐参数
                setParams(prev => ({
                    ...prev,
                    min_support: rec.min_support ?? prev.min_support,
                    min_confidence: rec.min_confidence ?? prev.min_confidence,
                    min_lift: rec.min_lift ?? prev.min_lift
                }));

                setStatsParams(prev => ({
                    ...prev,
                    p_value_threshold: rec.p_value_threshold ?? prev.p_value_threshold,
                    test_method: rec.suggested_tests?.length ? 'auto' : prev.test_method
                }));

                toast.success(`智能适配完成：${rec.summary_text ?? '已根据数据集分布更新默认建议。'}`);
            }
        } catch (err) {
            console.error("Profile recommendation failed", err);
            setError(extractErrorMessage(err, "无法获取智能推荐。请确保数据集已加载。"));
        } finally {
            setIsAutoConfiguring(false);
        }
    }, [toast]);

    useEffect(() => {
        if (!didAutoConfig.current) {
            didAutoConfig.current = true;
            void autoConfig();
        }
    }, [autoConfig]);

    // P值变更时联动修改置信水平
    const handlePValueChange = (val: number) => {
        setStatsParams({
            ...statsParams,
            p_value_threshold: val,
            confidence_level: 1 - val
        });
    };

    const runAnalysis = async () => {
        // 提交前检查是否已有正在运行的任务，防止误操作导致历史里堆满重复记录
        if (runningTaskId) {
            const ok = await confirm(
                `当前已有任务正在运行（进度 ${runningTaskProgress.toFixed(0)}%）。直接前往查看，还是强行启动新任务？

• 取消 → 继续运行中的任务
• 确定 → 强行启动新任务（旧任务在后台继续运行，分别版入历史）`
            );
            if (!ok) {
                // 用户选择取消 —— 跳转到当前运行任务
                navigate(`/analysis_result?task_id=${runningTaskId}`);
                return;
            }
        }

        setLoading(true);
        setError('');
        try {
            const payload = {
                ...params,
                stats_config: statsParams
            };

            const resp = await algorithmService.startTask(payload);
            if (resp.success) {
                setRunningTaskId(resp.task_id);
                setRunningTaskProgress(0);
                navigate(`/analysis_result?task_id=${resp.task_id}`);
            }
        } catch (err) {
            setError(extractErrorMessage(err, '引擎启动失败'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-7xl mx-auto px-4 py-2 sm:px-6 pb-8 flex flex-col gap-4">
            {/* 顶部标题与快速操作 - 精简版 */}
            <div className="mb-4 flex flex-col md:flex-row md:items-center justify-between gap-3 shrink-0">
                <div className="flex items-center gap-3">
                    <div className="bg-[#2383e2] p-2 rounded-xl text-white shadow-lg">
                        <BrainCircuit size={22} />
                    </div>
                    <div>
                        <h1 className="text-xl font-black tracking-tighter text-[#37352f]">算法与检验配置</h1>
                    </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={autoConfig}
                        disabled={isAutoConfiguring}
                    >
                        <RefreshCw size={14} className={isAutoConfiguring ? 'animate-spin' : ''} />
                        智能推荐
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                            setParams({ ...DEFAULT_MINING_PARAMS });
                            setStatsParams({ ...DEFAULT_STATS_PARAMS });
                        }}
                    >
                        <RefreshCw size={14} />
                        重置参数
                    </Button>
                </div>
            </div>

            {/* 启发式规范 - 极致压缩 */}
            <div className="mb-4 p-3 bg-gradient-to-r from-blue-50/30 to-indigo-50/30 rounded-xl border border-blue-100/30 flex items-center gap-4 shrink-0 overflow-hidden">
                <div className="flex items-center gap-2 border-r border-blue-100/50 pr-4 shrink-0">
                    <Info size={16} className="text-blue-500" />
                    <span className="font-black text-[#37352f] text-[10px]">使用规范</span>
                </div>
                <div className="flex gap-6 flex-1 overflow-x-auto no-scrollbar">
                    <div className="flex items-center gap-2 whitespace-nowrap">
                        <div className="w-1 h-1 bg-blue-400 rounded-full" />
                        <span className="text-[10px] text-[#787774]"><strong>联动推导</strong>: 规则将无损传递至统计模块验证</span>
                    </div>
                    <div className="flex items-center gap-2 whitespace-nowrap">
                        <div className="w-1 h-1 bg-blue-400 rounded-full" />
                        <span className="text-[10px] text-[#787774]"><strong>并行加速</strong>: 独立线程处理非阻塞计算</span>
                    </div>
                    <div className="flex items-center gap-2 whitespace-nowrap">
                        <div className="w-1 h-1 bg-blue-400 rounded-full" />
                        <span className="text-[10px] text-[#787774]"><strong>显著性控制</strong>: 低 P 阈值可剔除随机噪声</span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 items-stretch mb-4">
                {/* 左侧：关联规则参数 */}
                <section className="bg-white notion-card p-4 border border-[#e9e9e8] rounded-xl shadow-sm hover:shadow-md transition-all h-full flex flex-col overflow-y-auto custom-scrollbar">
                    <div className="flex items-center justify-between mb-4 pb-2 border-b border-gray-50">
                        <h3 className="font-black flex items-center gap-2 text-[#37352f] text-sm">
                            <Settings2 size={16} className="text-[#2383e2]" />
                            关联规则挖掘参数
                        </h3>
                    </div>

                    <div className="space-y-6 flex-1">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-10">
                            <div className="space-y-4">
                                <label className="text-[11px] font-black text-[#37352f] uppercase tracking-wider flex justify-between">
                                    <span>最小支持度</span>
                                    <span className="text-[#2383e2] font-mono text-sm">{(params.min_support * 100).toFixed(1)}%</span>
                                </label>
                                <input
                                    type="range" min="0.001" max="0.5" step="0.001"
                                    className="w-full h-2 bg-[#efefee] rounded-full appearance-none cursor-pointer accent-[#2383e2] hover:accent-blue-400"
                                    value={params.min_support}
                                    onChange={e => setParams({ ...params, min_support: parseFloat(e.target.value) })}
                                />
                                <p className="text-[10px] text-[#b4b4b3] font-medium leading-relaxed">共现频率下限，滤除长尾或稀有项。</p>
                            </div>

                            <div className="space-y-4">
                                <label className="text-[11px] font-black text-[#37352f] uppercase tracking-wider flex justify-between">
                                    <span>最小置信度</span>
                                    <span className="text-[#2383e2] font-mono text-sm">{(params.min_confidence * 100).toFixed(0)}%</span>
                                </label>
                                <input
                                    type="range" min="0.1" max="1.0" step="0.05"
                                    className="w-full h-2 bg-[#efefee] rounded-full appearance-none cursor-pointer accent-[#2383e2] hover:accent-blue-400"
                                    value={params.min_confidence}
                                    onChange={e => setParams({ ...params, min_confidence: parseFloat(e.target.value) })}
                                />
                                <p className="text-[10px] text-[#b4b4b3] font-medium leading-relaxed">关联强度的可靠水位（推荐 {'>'} 50%）。</p>
                            </div>

                            <div className="space-y-3">
                                <label className="text-[11px] font-black text-[#37352f] uppercase tracking-wider block">最小提升度</label>
                    <Input
                            type="number" step="0.1" min="0" max="100"
                            className="font-bold"
                            value={params.min_lift}
                            onChange={e => setParams({ ...params, min_lift: parseFloat(e.target.value) })}
                        />
                                <p className="text-[10px] text-[#b4b4b3] font-medium leading-tight mt-1">独立性偏离强度（指标越大关联越强）。</p>
                            </div>

                            <div className="space-y-3">
                                <label className="text-[11px] font-black text-[#37352f] uppercase tracking-wider block">深度挖掘层级</label>
                                <select
                                    className="w-full border border-gray-100 rounded-xl px-4 py-2 text-sm bg-[#fbfbfa] focus:ring-2 focus:ring-blue-100 focus:border-[#2383e2] outline-none transition-all font-bold appearance-none"
                                    value={params.max_len}
                                    onChange={e => setParams({ ...params, max_len: parseInt(e.target.value) })}
                                >
                                    <option value={2}>2 级深度 (成对交互项)</option>
                                    <option value={3}>3 级深度 (三元交互项)</option>
                                </select>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-dashed border-gray-100">
                            <div className="space-y-3">
                                <label className="text-[11px] font-black text-[#37352f] uppercase tracking-wider block">相关性测算指标</label>
                                <select
                                    className="w-full border border-gray-100 rounded-xl px-4 py-2 text-sm bg-[#fbfbfa] focus:ring-2 focus:ring-blue-100 focus:border-[#2383e2] outline-none transition-all font-bold"
                                    defaultValue="lift"
                                >
                                    <option value="lift">提升度</option>
                                    <option value="leverage">杠杆率</option>
                                    <option value="conviction">确信度</option>
                                </select>
                            </div>
                            <div className="space-y-3">
                                <label className="text-[11px] font-black text-[#37352f] uppercase tracking-wider block">特征共线性过滤</label>
                                <div className="flex items-center gap-4 h-10">
                                    <label className="flex items-center gap-2 cursor-pointer group">
                                        <input type="radio" name="cf" defaultChecked className="hidden" />
                                        <div className="w-4 h-4 rounded-full border-2 border-[#2383e2] flex items-center justify-center p-0.5">
                                            <div className="w-full h-full bg-[#2383e2] rounded-full"></div>
                                        </div>
                                        <span className="text-sm font-bold text-[#37352f] group-hover:text-[#2383e2] transition-colors">开启过滤</span>
                                    </label>
                                    <label className="flex items-center gap-2 cursor-pointer group">
                                        <input type="radio" name="cf" className="hidden" />
                                        <div className="w-4 h-4 rounded-full border-2 border-gray-200 flex items-center justify-center p-0.5"></div>
                                        <span className="text-sm font-bold text-[#787774] group-hover:text-[#2383e2] transition-colors">全量保留</span>
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* 右侧：统计检验配置区 */}
                <section className="bg-white notion-card p-4 border border-[#e9e9e8] rounded-xl shadow-sm hover:shadow-md transition-all h-full flex flex-col overflow-y-auto custom-scrollbar">
                    <div className="flex items-center justify-between mb-4 pb-2 border-b border-gray-50">
                        <h3 className="font-black flex items-center gap-2 text-[#37352f] text-sm">
                            <Calculator size={16} className="text-[#10b981]" />
                            非参数统计检验参数
                        </h3>
                    </div>

                    <div className="space-y-6 flex-1">
                        <div className="space-y-3">
                            <label className="text-[11px] font-black text-[#37352f] uppercase tracking-wider block">目标检验算子选择</label>
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                                {[
                                    { id: 'auto', label: '智能推论', icon: BrainCircuit },
                                    { id: 'mannwhitney', label: 'U 检验', icon: Calculator },
                                    { id: 'chi2', label: '卡方独立项', icon: Calculator },
                                    { id: 'ks', label: 'KS 检验', icon: Calculator },
                                    { id: 'kruskal', label: 'H 检验', icon: Calculator }
                                ].map(method => (
                                    <button
                                        key={method.id}
                                        onClick={() => setStatsParams({ ...statsParams, test_method: method.id })}
                                        className={cn(
                                            "flex flex-col items-center justify-center p-3 rounded-xl border transition-all gap-1",
                                            statsParams.test_method === method.id
                                                ? "border-emerald-500 bg-emerald-50 text-emerald-700 font-bold shadow-sm ring-1 ring-emerald-500"
                                                : "border-gray-100 bg-[#fbfbfa] text-[#787774] hover:bg-white hover:border-emerald-200"
                                        )}
                                    >
                                        <method.icon size={16} className={statsParams.test_method === method.id ? 'text-emerald-600' : 'text-gray-300'} />
                                        <span className="text-[10px] text-center leading-none">{method.label}</span>
                                    </button>
                                ))}
                            </div>
                            {statsParams.test_method === 'auto' && (
                                <p className="text-[10px] text-emerald-600 mt-2 font-black tracking-wide flex items-center gap-1">
                                    <Sparkles size={12} /> 系统将根据变量对的数据形态实现自动最优拓扑路径。
                                </p>
                            )}
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-3">
                                <label className="text-[11px] font-black text-[#37352f] uppercase tracking-wider flex justify-between">
                                    <span>显著性水平</span>
                                    <span className="text-red-500 font-mono text-sm">{statsParams.p_value_threshold.toFixed(3)}</span>
                                </label>
                                <input
                                    type="range" min="0.001" max="0.100" step="0.001"
                                    className="w-full h-2 bg-[#efefee] rounded-full appearance-none cursor-pointer accent-red-500 hover:accent-red-400"
                                    value={statsParams.p_value_threshold}
                                    onChange={e => handlePValueChange(parseFloat(e.target.value))}
                                />
                                <div className="flex justify-between text-[9px] text-[#b4b4b3] font-black px-1">
                                    <span>极严苛 (0.01)</span>
                                    <span>标准 (0.05)</span>
                                    <span>基础 (0.10)</span>
                                </div>
                            </div>

                            <div className="space-y-3">
                                <label className="text-[11px] font-black text-[#37352f] uppercase tracking-wider block">置信区间可信度</label>
                                <div className="group relative">
                                    <div className="h-12 flex items-center bg-white px-5 rounded-2xl border border-gray-100 shadow-sm overflow-hidden ring-0 group-hover:ring-1 group-hover:ring-emerald-200 transition-all">
                                        <div className="flex-1">
                                            <div className="w-full bg-gray-50 h-2.5 rounded-full overflow-hidden">
                                                <div className="bg-gradient-to-r from-emerald-400 to-teal-500 h-full transition-all duration-700 ease-out" style={{ width: `${statsParams.confidence_level * 100}%` }} />
                                            </div>
                                        </div>
                                        <span className="ml-5 font-mono text-lg font-black text-emerald-600">{(statsParams.confidence_level * 100).toFixed(1)}%</span>
                                    </div>
                                    <p className="text-[10px] text-[#b4b4b3] font-medium mt-2 leading-relaxed italic pr-4">表示拒绝零假设时容错程度与确信概率。</p>
                                </div>
                            </div>
                        </div>

                        {profileData && (
                            <div className="mt-auto p-5 bg-gradient-to-br from-emerald-50/80 to-teal-50/80 rounded-[2rem] border border-emerald-100/50 shadow-inner">
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-8 h-8 bg-emerald-500 rounded-xl flex items-center justify-center text-white shadow-lg shadow-emerald-500/20">
                                        <Database size={16} />
                                    </div>
                                    <h4 className="font-black text-[13px] text-emerald-800 tracking-tight">本地数据流态快照</h4>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-white/80 backdrop-blur-sm p-3 rounded-2xl border border-emerald-100/50 flex flex-col items-center">
                                        <span className="text-[9px] font-black text-emerald-600/60 uppercase">样本总量</span>
                                        <span className="font-mono text-sm font-black text-emerald-900">{profileData.rows.toLocaleString()} 行</span>
                                    </div>
                                    <div className="bg-white/80 backdrop-blur-sm p-3 rounded-2xl border border-emerald-100/50 flex flex-col items-center">
                                        <span className="text-[9px] font-black text-emerald-600/60 uppercase">特征全集</span>
                                        <span className="font-mono text-sm font-black text-emerald-900">{profileData.cols.toLocaleString()} 列</span>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </section>
            </div>

            {(miningReadiness || profileAssessment) && (
                <section className="bg-white notion-card p-5 border border-[#e9e9e8] rounded-xl shadow-sm">
                    <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                        <div className="flex items-start gap-3">
                            <div className={cn(
                                "w-11 h-11 rounded-2xl flex items-center justify-center shrink-0",
                                miningReadiness?.readiness_level === 'good'
                                    ? "bg-emerald-50 text-emerald-600 border border-emerald-100"
                                    : miningReadiness?.readiness_level === 'limited'
                                        ? "bg-sky-50 text-sky-600 border border-sky-100"
                                        : "bg-amber-50 text-amber-600 border border-amber-100"
                            )}>
                                {miningReadiness?.readiness_level === 'good' ? <ShieldCheck size={18} /> : <AlertTriangle size={18} />}
                            </div>
                            <div>
                                <div className="flex flex-wrap items-center gap-2">
                                    <h3 className="text-sm font-black text-[#37352f]">挖掘适配诊断</h3>
                                    {miningReadiness && (
                                        <span className={cn(
                                            "inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-wider",
                                            miningReadiness.readiness_level === 'good'
                                                ? "bg-emerald-50 text-emerald-700"
                                                : miningReadiness.readiness_level === 'limited'
                                                    ? "bg-sky-50 text-sky-700"
                                                    : miningReadiness.readiness_level === 'weak'
                                                        ? "bg-amber-50 text-amber-700"
                                                        : "bg-red-50 text-red-700"
                                        )}>
                                            {miningReadiness.readiness_level}
                                        </span>
                                    )}
                                </div>
                                <p className="mt-1 text-sm text-[#5f5e58] leading-relaxed max-w-3xl">
                                    {miningReadiness?.summary ?? '已完成当前数据集的基础质量评估。'}
                                </p>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 min-w-0">
                            <ReadinessMetricCard
                                label="适配度"
                                value={miningReadiness ? `${Math.round(miningReadiness.readiness_score)} 分` : '--'}
                                hint="数据重复模式 + 可用字段"
                            />
                            <ReadinessMetricCard
                                label="候选字段"
                                value={`${miningReadiness?.candidate_overview?.selected_count ?? 0} 列`}
                                hint="预计参与挖掘"
                            />
                            <ReadinessMetricCard
                                label="排除字段"
                                value={`${miningReadiness?.candidate_overview?.excluded_count ?? 0} 列`}
                                hint="自动识别为弱信号"
                            />
                            <ReadinessMetricCard
                                label="质量评分"
                                value={profileAssessment?.overall_score !== undefined ? `${Math.round(profileAssessment.overall_score)} 分` : '--'}
                                hint="缺失 / 重复 / 一致性"
                            />
                        </div>
                    </div>

                    <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                        <div className="rounded-2xl border border-[#eef1f4] bg-[#fafbfc] px-4 py-4">
                            <div className="text-[11px] font-black uppercase tracking-widest text-[#787774]">风险提示</div>
                            {miningReadiness?.warnings?.length ? (
                                <div className="mt-3 flex flex-wrap gap-2">
                                    {miningReadiness.warnings.slice(0, 4).map((warning) => (
                                        <span
                                            key={warning}
                                            className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-[11px] font-medium text-amber-700"
                                        >
                                            {warning}
                                        </span>
                                    ))}
                                </div>
                            ) : (
                                <p className="mt-3 text-sm text-[#787774]">当前没有检测到明显的挖掘风险项。</p>
                            )}
                        </div>

                        <div className="rounded-2xl border border-[#eef1f4] bg-[#fafbfc] px-4 py-4">
                            <div className="text-[11px] font-black uppercase tracking-widest text-[#787774]">优先操作建议</div>
                            {miningReadiness?.suggestions?.length ? (
                                <div className="mt-3 space-y-2">
                                    {miningReadiness.suggestions.slice(0, 3).map((tip) => (
                                        <div key={tip} className="flex items-start gap-2 text-sm text-[#4f4e49]">
                                            <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[#2383e2] shrink-0" />
                                            <span>{tip}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="mt-3 text-sm text-[#787774]">当前建议已同步到默认参数，可直接启动挖掘任务。</p>
                            )}
                        </div>
                    </div>
                </section>
            )}

            {/* 底部悬浮操作栏 */}
            <div className="sticky bottom-0 pt-2 pb-1 bg-gradient-to-t from-[#fbfbfa] via-[#fbfbfa]/95 to-transparent">
                <div className="max-w-4xl mx-auto w-full">
                    {runningTaskId && (
                        <div className="mb-2 px-3 sm:px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-xl flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3 text-sm text-blue-800">
                            <RefreshCw size={14} className="animate-spin shrink-0 text-blue-500" />
                            <span className="flex-1">当前已有任务运行中（进度 {runningTaskProgress.toFixed(0)}%）</span>
                            <button
                                type="button"
                                onClick={() => navigate(`/analysis_result?task_id=${runningTaskId}`)}
                                className="shrink-0 text-blue-600 font-bold hover:underline text-xs"
                            >
                                查看任务 →
                            </button>
                        </div>
                    )}
                    <button
                        onClick={runAnalysis}
                        disabled={loading}
                        className="w-full h-12 sm:h-14 bg-[#37352f] text-white rounded-2xl font-bold text-sm sm:text-base flex items-center justify-center gap-2 sm:gap-3 hover:bg-black transition-all active:scale-[0.98] shadow-xl shadow-gray-400/30 group relative overflow-hidden disabled:bg-gray-400"
                    >
                        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-emerald-500/20 opacity-0 group-hover:opacity-100 transition-opacity" />
                        {loading ? <RefreshCw size={20} className="animate-spin" /> : <Play size={20} fill="currentColor" />}
                        {loading ? '分析任务启动中...' : '开始分析'}
                        <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
                    </button>
                    {error && (
                        <div className="mt-3 p-3.5 bg-red-50 text-red-600 rounded-xl border border-red-100 flex items-center gap-2 text-sm font-medium shadow-sm">
                            <Info size={16} /> {error}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function ReadinessMetricCard({ label, value, hint }: { label: string; value: string; hint: string }) {
    return (
        <div className="rounded-2xl border border-[#eef1f4] bg-[#fafbfc] px-4 py-3">
            <div className="text-[10px] font-black uppercase tracking-widest text-[#9b9a97]">{label}</div>
            <div className="mt-1 text-lg font-black text-[#37352f]">{value}</div>
            <div className="mt-1 text-[10px] leading-relaxed text-[#9b9a97]">{hint}</div>
        </div>
    );
}
