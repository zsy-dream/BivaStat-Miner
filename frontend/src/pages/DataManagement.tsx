import { useState, useEffect, useCallback } from 'react';
import {
    Upload, FileText, CheckCircle, AlertCircle,
    ShieldCheck, Play, Download,
    RefreshCw, Sliders, Layers, Server, LayoutTemplate,
    ChevronRight, ChevronDown, ChevronUp
} from 'lucide-react';
import { cn } from '../utils/cn';
import { dataService, extractErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import type { DataInfo, PreprocessingConfig, QualityReport, ProcessingResult } from '../types';

// 占位图表组件图标
const DatabaseIcon = ({ className }: { className?: string }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
        <path d="M3 5V19A9 3 0 0 0 21 19V5"></path>
        <path d="M3 12A9 3 0 0 0 21 12"></path>
    </svg>
);

export default function DataManagement() {
    const { toast, confirm } = useToast();
    const [loading, setLoading] = useState(false);
    const [dataInfo, setDataInfo] = useState<DataInfo | null>(null);
    const [qualityReport, setQualityReport] = useState<QualityReport | null>(null);
    const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
    const [statusMsg, setStatusMsg] = useState('');
    const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null);


    // UI状态：左侧选中的控制面板 Tab
    const [activeTab, setActiveTab] = useState<'missing' | 'outlier' | 'normalize' | 'encode' | null>(null);
    const [toolPanelExpanded, setToolPanelExpanded] = useState(true);

    // 中间的预处理配置状态
    const [config, setConfig] = useState<PreprocessingConfig>({
        missing_values: { strategy: 'none' },
        outliers: { method: 'none', threshold: 3.0, action: 'remove' },
        normalize: { method: 'none' },
        encode: { method: 'auto' }
    });

    const fetchQuality = useCallback(async (path: string) => {
        try {
            const res = await dataService.getQualityReport(path);
            if (res.success) {
                setQualityReport(res);
            }
        } catch {
            console.error('Failed to fetch quality report');
        }
    }, []);

    const fetchCurrent = useCallback(async () => {
        try {
            const res = await dataService.getCurrent();
            if (res.success && res.data) {
                setDataInfo(res.data);
                await fetchQuality(res.data.path);
            }
        } catch {
            // 暂无已加载数据集
        }
    }, [fetchQuality]);

    useEffect(() => {
        void fetchCurrent();
    }, [fetchCurrent]);

    const handleLoadSampleDataset = async (type: string) => {
        setLoading(true);
        setStatusMsg(`正在生成并加载 ${type} 示例数据集...`);
        try {
            const res = await dataService.loadSampleDataset(type);
            if (res.success) {
                const nextDataInfo: DataInfo | null = res.data ?? (res.path ? {
                    filename: `sample_${type}.csv`,
                    path: res.path,
                    shape: Array.isArray(res.shape)
                        ? [Number(res.shape[0] ?? 0), Number(res.shape[1] ?? 0)]
                        : [0, 0],
                    columns: Array.isArray(res.columns) ? res.columns.map((column) => String(column)) : [],
                    preview: Array.isArray(res.preview) ? res.preview as Record<string, unknown>[] : []
                } : null);

                if (!nextDataInfo) {
                    throw new Error('示例数据集加载结果缺少数据内容');
                }
                setDataInfo(nextDataInfo);
                setUploadStatus('success');
                if (nextDataInfo.path) {
                    await fetchQuality(nextDataInfo.path);
                }
            }
        } catch (e) {
            setUploadStatus('error');
            setStatusMsg(extractErrorMessage(e, '加载示例数据失败'));
        } finally {
            setLoading(false);
        }
    };

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        const selectedFile = files[0];

        setLoading(true);
        setUploadStatus('uploading');
        setStatusMsg('正在上传并解析文件...');

        try {
            const res = await dataService.uploadData(selectedFile);

            if (res.success && res.data) {
                setUploadStatus('success');
                setStatusMsg('文件解析成功！');
                setDataInfo(res.data);
                await fetchQuality(res.data.path);
            }
        } catch (error) {
            setUploadStatus('error');
            setStatusMsg(extractErrorMessage(error, '解析失败，请检查文件格式是否规范'));
        } finally {
            setLoading(false);
            e.target.value = '';
        }
    };

    const handleApplyAllConfig = async () => {
        if (!dataInfo || !dataInfo.path) return;
        setLoading(true);
        setStatusMsg('正在后台执行增强预处理管道...');

        const payloadConfig: Record<string, unknown> = {};
        if (config.missing_values.strategy !== 'none') {
            payloadConfig.missing_values = config.missing_values;
        }
        if (config.outliers.method !== 'none') {
            payloadConfig.outliers = config.outliers;
        }
        if (config.normalize.method !== 'none') {
            payloadConfig.normalize = config.normalize;
        }
        if (config.encode?.method && config.encode.method !== 'none') {
            payloadConfig.encode = config.encode;
        }
        if (Object.keys(payloadConfig).length === 0) {
            toast.warning('未选择任何预处理操作，直接跳过。');
            setLoading(false);
            setStatusMsg('');
            return;
        }

        try {
            const res = await dataService.enhancedPreprocessing(dataInfo.path, payloadConfig);
            if (res.success) {
                setProcessingResult(res.data?.preprocessing_result ?? null);
                const currentDataRes = await dataService.getCurrent();
                if (currentDataRes.success && currentDataRes.data) {
                    setDataInfo(currentDataRes.data);
                    await fetchQuality(currentDataRes.data.path);
                }
                toast.success('预处理管道执行完毕');
                setStatusMsg('预处理管道执行完毕');
            } else {
                toast.error(res.error || '执行失败');
            }
        } catch (e) {
            toast.error(extractErrorMessage(e, '请求预处理失败'));
        } finally {
            setLoading(false);
        }
    };

    const handleExport = () => {
        window.open(dataService.getExportUrl('csv'), '_blank');
    };

    const handleExportQuality = () => {
        window.open(dataService.getQualityReportDownloadUrl('html'), '_blank');
    };

    const handleClearSession = async () => {
        const ok = await confirm('确定要清除当前会话，返回导入页面吗？这也会清除服务器上的当前数据集记录。');
        if (ok) {
            try {
                await dataService.clearCurrent();
                setDataInfo(null);
                setQualityReport(null);
                setProcessingResult(null);
                setUploadStatus('idle');
                setStatusMsg('');
                toast.success('会话已清除');
            } catch {
                setDataInfo(null);
                setQualityReport(null);
                setProcessingResult(null);
                setUploadStatus('idle');
                setStatusMsg('');
            }
        }
    };

    // 重置预处理配置为默认值
    const handleResetConfig = () => {
        setConfig({
            missing_values: { strategy: 'none' },
            outliers: { method: 'none', threshold: 3.0, action: 'remove' },
            normalize: { method: 'none' },
            encode: { method: 'auto' }
        });
        setStatusMsg('配置已重置');
        setTimeout(() => setStatusMsg(''), 2000);
    };
    if (!dataInfo) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[70vh] w-full max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
                <div className="text-center mb-10">
                    <div className="inline-block px-4 py-1.5 bg-blue-50 text-[#2383e2] rounded-full text-[10px] font-black uppercase tracking-[0.2em] mb-4 border border-blue-100">
                        Data Pipeline Entry
                    </div>
                    <h1 className="text-4xl font-black mb-3 text-[#31302c] tracking-tight">导入分析数据集</h1>
                    <p className="text-sm text-[#b4b4b3] max-w-md mx-auto leading-relaxed">支持 CSV, Excel 格式，一键开启基于启发式算法的深度双变量数据洞察与非参数统计分析。</p>
                </div>

                <div className="w-full max-w-2xl bg-white rounded-[32px] p-2 border border-[#f1f1f0] shadow-2xl shadow-blue-500/5 group relative transition-all hover:border-[#2383e2]/30">
                    <div className="flex flex-col items-center justify-center border-2 border-dashed border-[#e9e9e8] rounded-[26px] p-12 bg-[#fcfcfb] group-hover:bg-white transition-all group-hover:border-[#2383e2]/50">
                        <input type="file" className="absolute inset-0 opacity-0 cursor-pointer z-20" accept=".csv,.xlsx,.xls" onChange={handleUpload} disabled={loading} />

                        {loading ? (
                            <div className="flex flex-col items-center py-10">
                                <div className="relative mb-6">
                                    <RefreshCw className="w-16 h-16 text-[#2383e2]/10 animate-spin" />
                                    <DatabaseIcon className="w-6 h-6 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[#2383e2]" />
                                </div>
                                <p className="text-sm text-[#31302c] font-bold tracking-tight">{statusMsg}</p>
                                <div className="mt-4 flex gap-1">
                                    <div className="w-1.5 h-1.5 bg-[#2383e2] rounded-full animate-bounce [animation-delay:-0.3s]" />
                                    <div className="w-1.5 h-1.5 bg-[#2383e2] rounded-full animate-bounce [animation-delay:-0.15s]" />
                                    <div className="w-1.5 h-1.5 bg-[#2383e2] rounded-full animate-bounce" />
                                </div>
                            </div>
                        ) : (
                            <>
                                <div className="w-20 h-20 rounded-3xl bg-white shadow-xl shadow-blue-500/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-all duration-500 border border-[#f1f1f0]">
                                    <Upload className="w-8 h-8 text-[#2383e2]" />
                                </div>
                                <h3 className="text-xl font-black text-[#31302c] mb-2 tracking-tight">选择或拖拽数据集</h3>
                                <p className="text-xs text-[#b4b4b3] mb-8 font-medium">支持 .csv, .xlsx, .xls | 单个文件最大支持 100MB</p>

                                <div className="flex items-center gap-4 flex-wrap justify-center">
                                    <div className="relative group/upload">
                                        <button className="px-8 py-3 bg-[#31302c] text-white rounded-xl text-xs font-black shadow-lg shadow-black/10 flex items-center gap-2 group-hover:bg-blue-600 transition-colors">
                                            <FileText className="w-4 h-4" /> 浏览本地文件
                                        </button>
                                        <input type="file" className="absolute inset-0 opacity-0 cursor-pointer z-20" accept=".csv,.xlsx,.xls" onChange={handleUpload} disabled={loading} />
                                    </div>

                                    <div className="relative z-30 group/sample">
                                        <div className="px-6 py-3 bg-white text-[#787774] border border-[#e9e9e8] rounded-xl text-xs font-black hover:border-blue-200 transition-all cursor-pointer flex items-center gap-2">
                                            <Layers className="w-4 h-4" /> 加载演示数据
                                        </div>
                        <div className="absolute bottom-full right-0 sm:left-full sm:right-auto ml-0 sm:ml-2 mb-0 w-56 bg-white/80 backdrop-blur-xl border border-white/20 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.1)] opacity-0 invisible group-hover/sample:opacity-100 group-hover/sample:visible transition-all z-50 p-2.5 space-y-1.5 border-[#f1f1f0]">
                                            <div className="px-3 py-2 text-[10px] font-black text-[#b4b4b3] uppercase tracking-widest border-b border-[#f1f1f0] mb-1">行业预设数据集</div>
                                            {[
                                                { id: 'retail', name: '零售交易流水' },
                                                { id: 'medical', name: '患者诊断数据' },
                                                { id: 'financial', name: '金融风控样本' },
                                                { id: 'education', name: '学生成绩分布' },
                                                { id: 'marketing', name: '推广转化反馈' },
                                                { id: 'iris_extended', name: '多维鸢尾花(扩展)' }
                                            ].map(d => (
                                                <button
                                                    key={d.id}
                                                    onClick={() => handleLoadSampleDataset(d.id)}
                                                    className="w-full text-left px-4 py-2.5 text-[11px] font-bold text-[#787774] hover:bg-blue-500 hover:text-white rounded-xl transition-all flex items-center justify-between group"
                                                >
                                                    {d.name}
                                                    <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                {uploadStatus === 'error' && (
                                    <div className="mt-8 flex items-center gap-3 text-red-500 bg-red-50 px-5 py-2.5 rounded-xl text-xs font-bold border border-red-100 animate-shake">
                                        <AlertCircle className="w-4 h-4" /> {statusMsg}
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>

                <div className="mt-8 sm:mt-12 grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-8 w-full max-w-3xl">
                    {[
                        { title: '多维特征解析', desc: '智能识别变量类型与分布' },
                        { title: '强化预处理', desc: '内置多种缺失值与异常值策略' },
                        { title: '秒级洞察', desc: '启发式算法快速定位关键因子' }
                    ].map((feature, i) => (
                        <div key={i} className="text-center group">
                            <h4 className="text-[11px] font-black text-[#31302c] uppercase tracking-widest mb-1 shadow-sm inline-block px-2 group-hover:text-blue-500 transition-colors tracking-tighter">{feature.title}</h4>
                            <p className="text-[10px] text-[#b4b4b3] font-medium leading-relaxed">{feature.desc}</p>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    // 主视图：三栏式增强数据预处理工作台
    return (
        <div className="flex flex-col h-full bg-white rounded-2xl shadow-sm border border-[#e9e9e8] overflow-hidden -m-3 sm:-m-5 md:-m-8 lg:-m-10">
            {/* 顶栏控制 */}
            <div className="py-4 px-6 md:px-8 border-b border-[#f1f1f0] bg-white flex flex-wrap justify-between items-center shrink-0 z-10 gap-3">
                <div className="flex items-center gap-4">
                    <div className="bg-gradient-to-br from-[#2383e2] to-[#0056b3] p-2 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
                        <DatabaseIcon className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-lg font-black text-[#31302c] tracking-tight leading-none">数据管道预处理</h1>
                        <p className="text-[10px] text-[#b4b4b3] mt-2 font-mono uppercase tracking-widest flex items-center gap-2">
                            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                            当前激活数据集: <span className="text-[#787774] font-bold">{dataInfo.filename}</span>
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                    <div className="flex bg-[#fcfcfb] border border-[#f1f1f0] p-1 rounded-xl gap-1">
                        <label className="cursor-pointer text-[11px] font-bold text-[#787774] hover:text-[#2383e2] hover:bg-white flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all">
                            <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} /> 重新载入
                            <input type="file" className="hidden" accept=".csv,.xlsx,.xls" onChange={handleUpload} />
                        </label>
                        <div className="w-[1px] h-5 bg-[#f1f1f0] self-center" />
                        <button
                            className="bg-transparent text-[#787774] hover:text-red-500 hover:bg-red-50 px-3.5 py-2 rounded-lg text-[11px] font-bold flex items-center gap-2 transition-all"
                            onClick={handleClearSession}
                        >
                            <RefreshCw className="w-3.5 h-3.5" /> 清除会话
                        </button>
                    </div>

                    <div className="flex bg-[#fcfcfb] border border-[#f1f1f0] p-1 rounded-xl gap-1">
                        <button
                            className="text-[#787774] hover:text-[#2383e2] hover:bg-white px-3.5 py-2 rounded-lg text-[11px] font-bold flex items-center gap-2 transition-all"
                            onClick={handleExport}
                        >
                            <Download className="w-3.5 h-3.5" /> 导出数据集
                        </button>
                        <div className="w-[1px] h-5 bg-[#f1f1f0] self-center" />
                        <button
                            className="text-[#787774] hover:text-[#2383e2] hover:bg-white px-3.5 py-2 rounded-lg text-[11px] font-bold flex items-center gap-2 transition-all"
                            onClick={handleExportQuality}
                        >
                            <FileText className="w-3.5 h-3.5" /> 诊断报告
                        </button>
                    </div>

                    <button
                        className="bg-[#2383e2] text-white shadow-lg shadow-blue-500/20 px-6 py-2.5 rounded-xl text-xs font-black flex items-center gap-2 hover:bg-blue-600 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60"
                        onClick={handleApplyAllConfig}
                        disabled={loading}
                    >
                        {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                        执行预处理管道
                    </button>
                </div>
            </div>

            {/* 主内容工作区：上方配置 + 下方全宽预览 */}
            <div className="flex flex-col flex-1 overflow-hidden">

                {/* === 左侧栏: 导航 === */}
                <div className="w-full border-b border-[#f1f1f0] bg-[#fcfcfb] px-4 md:px-6 py-3 shrink-0">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-[11px] font-black text-[#6f6f6f] uppercase tracking-[0.2em]">操作项折叠面板</h3>
                        <button
                            onClick={() => setToolPanelExpanded(v => !v)}
                            className="text-[11px] font-black text-[#787774] hover:text-[#2383e2] flex items-center gap-1.5 px-2 py-1 rounded-lg hover:bg-white transition-all"
                        >
                            {toolPanelExpanded ? '收起' : '展开'}
                            {toolPanelExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>
                    </div>
                    {toolPanelExpanded && (
                        <>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                            {[
                                { key: 'missing' as const, icon: ShieldCheck, label: '缺失值处理', desc: config.missing_values.strategy === 'none' ? '未配置' : config.missing_values.strategy },
                                { key: 'outlier' as const, icon: AlertCircle, label: '异常值检测', desc: config.outliers.method === 'none' ? '未配置' : config.outliers.method },
                                { key: 'normalize' as const, icon: Sliders, label: '数据标准化', desc: config.normalize.method === 'none' ? '未配置' : config.normalize.method },
                                { key: 'encode' as const, icon: Layers, label: '特征编码', desc: config.encode?.method === 'auto' ? '自动' : (config.encode?.method || '未配置') },
                            ].map(item => (
                                <button
                                    key={item.key}
                                    onClick={() => setActiveTab(prev => prev === item.key ? null : item.key)}
                                    className={cn(
                                        "group flex items-center justify-between w-full text-left px-3 py-2.5 rounded-xl transition-all duration-200 text-sm",
                                        activeTab === item.key
                                            ? "bg-white shadow-[0_4px_12px_rgba(0,0,0,0.05)] border border-[#2383e2]/30 font-bold text-[#2383e2]"
                                            : "text-[#787774] hover:bg-white hover:text-[#37352f] border border-transparent"
                                    )}
                                >
                                    <div className="flex items-center gap-3">
                                        <item.icon className={cn("w-4.5 h-4.5 transition-transform group-hover:scale-110", activeTab === item.key ? "text-[#2383e2]" : "text-[#b4b4b3]")} />
                                        <div className="flex flex-col">
                                            <span>{item.label}</span>
                                            <span className={cn("text-[9px] font-medium", activeTab === item.key ? "text-[#2383e2]/60" : "text-[#b4b4b3]")}>{item.desc}</span>
                                        </div>
                                    </div>
                                    {activeTab === item.key
                                        ? <ChevronUp className="w-3.5 h-3.5 text-[#2383e2]" />
                                        : <ChevronDown className="w-3.5 h-3.5 text-[#b4b4b3] opacity-0 group-hover:opacity-100 transition-opacity" />}
                                </button>
                            ))}
                        </div>

                        {/* 展开的配置面板 */}
                        {activeTab === 'missing' && (
                            <div className="mt-3 p-5 bg-white border border-[#f1f1f0] rounded-2xl shadow-sm animate-in slide-in-from-top-2 duration-200">
                                <label className="text-xs font-black text-[#31302c] mb-3 block">选择处理策略</label>
                                <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                                    {[
                                        { v: 'none', l: '不处理', d: '跳过' },
                                        { v: 'drop', l: '直接删除', d: '移除空行' },
                                        { v: 'mean', l: '平均值', d: '均值填充' },
                                        { v: 'median', l: '中位数', d: '鲁棒填充' },
                                        { v: 'constant', l: '常数', d: '固定值' },
                                        { v: 'knn', l: 'KNN 插补', d: 'AI填充' }
                                    ].map(opt => (
                                        <label
                                            key={opt.v}
                                            className={cn(
                                                "flex flex-col gap-1 p-2.5 border rounded-xl cursor-pointer transition-all text-center",
                                                config.missing_values.strategy === opt.v
                                                    ? "border-[#2383e2] bg-blue-50/50 ring-1 ring-[#2383e2]/20"
                                                    : "border-[#f1f1f0] hover:border-[#b4b4b3] bg-white"
                                            )}
                                        >
                                            <input type="radio" className="hidden" checked={config.missing_values.strategy === opt.v} onChange={() => setConfig({ ...config, missing_values: { ...config.missing_values, strategy: opt.v } })} />
                                            <span className={cn("text-[11px] font-bold", config.missing_values.strategy === opt.v ? "text-[#2383e2]" : "text-[#31302c]")}>{opt.l}</span>
                                            <span className="text-[9px] text-[#b4b4b3]">{opt.d}</span>
                                        </label>
                                    ))}
                                </div>
                                {config.missing_values.strategy === 'constant' && (
                                    <div className="mt-3">
                                        <input type="text" className="w-full p-2.5 border border-[#f1f1f0] rounded-xl outline-none focus:border-[#2383e2] bg-[#fcfcfb] text-sm" placeholder="填充常数，例如: 0 或 Unknown" onChange={e => setConfig({ ...config, missing_values: { ...config.missing_values, fill_value: e.target.value } })} />
                                    </div>
                                )}
                            </div>
                        )}

                        {activeTab === 'outlier' && (
                            <div className="mt-3 p-5 bg-white border border-[#f1f1f0] rounded-2xl shadow-sm animate-in slide-in-from-top-2 duration-200 space-y-4">
                                <div>
                                    <label className="text-xs font-black text-[#31302c] mb-3 block">1. 检测算法</label>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                                        {[
                                            { v: 'none', l: '不处理' },
                                            { v: 'zscore', l: 'Z-Score' },
                                            { v: 'iqr', l: 'IQR 箱线图' },
                                            { v: 'dbscan', l: 'DBSCAN 密度' }
                                        ].map(m => (
                                            <button
                                                key={m.v}
                                                onClick={() => setConfig({ ...config, outliers: { ...config.outliers, method: m.v } })}
                                                className={cn(
                                                    "px-3 py-2 rounded-xl border text-xs font-bold transition-all",
                                                    config.outliers.method === m.v ? "bg-[#31302c] text-white border-[#31302c]" : "bg-white text-[#787774] border-[#f1f1f0] hover:border-[#b4b4b3]"
                                                )}
                                            >
                                                {m.l}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                {(config.outliers.method === 'zscore' || config.outliers.method === 'iqr') && (
                                    <div className="flex items-center gap-4">
                                        <label className="text-xs font-bold text-[#31302c] shrink-0">2. 阈值</label>
                                        <input type="range" min="1.0" max="5.0" step="0.1" className="flex-1 cursor-pointer accent-[#2383e2]" value={config.outliers.threshold} onChange={e => setConfig({ ...config, outliers: { ...config.outliers, threshold: parseFloat(e.target.value) } })} />
                                        <span className="text-sm font-black text-[#2383e2] font-mono w-10 text-right">{config.outliers.threshold.toFixed(1)}x</span>
                                    </div>
                                )}
                                <div>
                                    <label className="text-xs font-black text-[#31302c] mb-2 block">3. 处置方式</label>
                                    <div className="grid grid-cols-2 gap-2">
                                        {[
                                            { v: 'remove', l: '整行剔除' },
                                            { v: 'clip', l: '边缘截断 (Clip)' }
                                        ].map(opt => (
                                            <label
                                                key={opt.v}
                                                className={cn(
                                                    "flex items-center gap-2 p-2.5 border rounded-xl cursor-pointer transition-all text-xs font-bold",
                                                    config.outliers.action === opt.v
                                                        ? "border-[#2383e2] bg-blue-50/50 text-[#2383e2]"
                                                        : "border-[#f1f1f0] text-[#787774] hover:border-[#b4b4b3]"
                                                )}
                                            >
                                                <input type="radio" className="accent-[#2383e2] w-3.5 h-3.5" checked={config.outliers.action === opt.v} onChange={() => setConfig({ ...config, outliers: { ...config.outliers, action: opt.v } })} />
                                                {opt.l}
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {activeTab === 'normalize' && (
                            <div className="mt-3 p-5 bg-white border border-[#f1f1f0] rounded-2xl shadow-sm animate-in slide-in-from-top-2 duration-200">
                                <label className="text-xs font-black text-[#31302c] mb-3 block">标准化算法</label>
                                <select
                                    className="w-full p-3 border border-[#f1f1f0] rounded-xl outline-none focus:border-[#2383e2] bg-[#fcfcfb] font-bold text-sm text-[#31302c]"
                                    value={config.normalize.method}
                                    onChange={e => setConfig({ ...config, normalize: { ...config.normalize, method: e.target.value } })}
                                >
                                    <option value="none">不处理 (跳过)</option>
                                    <option value="standard">StandardScaler (Z-Score)</option>
                                    <option value="minmax">MinMaxScaler (0-1 归一化)</option>
                                    <option value="robust">RobustScaler (抗异常值)</option>
                                </select>
                                <p className="mt-2 text-[10px] text-[#b4b4b3] flex items-center gap-1.5">
                                    <CheckCircle className="w-3 h-3 text-blue-400" />
                                    系统自动识别数值型变量，分类标签将保持原始形态。
                                </p>
                            </div>
                        )}

                        {activeTab === 'encode' && (
                            <div className="mt-3 p-5 bg-white border border-[#f1f1f0] rounded-2xl shadow-sm animate-in slide-in-from-top-2 duration-200">
                                <div className="flex items-center gap-3 mb-3">
                                    <LayoutTemplate className="w-5 h-5 text-[#2383e2]" />
                                    <h3 className="font-black text-sm text-[#31302c]">特征编码策略</h3>
                                </div>
                                <select
                                    className="w-full p-3 border border-[#f1f1f0] rounded-xl outline-none focus:border-[#2383e2] bg-[#fcfcfb] font-bold text-sm text-[#31302c]"
                                    value={config.encode?.method || 'auto'}
                                    onChange={e => setConfig({ ...config, encode: { method: e.target.value } })}
                                >
                                    <option value="auto">自动（低基数 One-Hot / 高基数 Label）</option>
                                    <option value="onehot">强制 One-Hot 编码</option>
                                    <option value="label">强制 Label 编码</option>
                                    <option value="none">不编码</option>
                                </select>
                                <p className="text-[10px] text-[#b4b4b3] mt-2 leading-relaxed">
                                    执行预处理后，编码结果会真实写回当前数据集，并直接体现在下方表头与预览列中。
                                </p>
                            </div>
                        )}
                        </>
                    )}

                    <button
                        onClick={handleResetConfig}
                        className="mt-3 group inline-flex items-center gap-2 text-left px-3 py-2 text-[#b4b4b3] hover:text-[#ea5b5c] transition-all duration-200 text-[11px] font-black uppercase tracking-widest rounded-lg hover:bg-white"
                    >
                        <RefreshCw className="w-3.5 h-3.5 transition-transform group-hover:rotate-180" />
                        <span>重置所有配置</span>
                    </button>
                </div>

                {/* === 数据预览表格 === */}
                <div className="flex-1 flex flex-col overflow-hidden bg-[#fbfbfa] min-w-0">
                    <div className="bg-white border-t border-[#f1f1f0] flex flex-col flex-1 min-h-0">
                        {/* 表头栏：紧凑统计摘要 */}
                        <div className="px-6 md:px-8 py-3 border-b border-[#f1f1f0] bg-[#fbfbfa] flex items-center justify-between shrink-0 gap-3 flex-wrap">
                            <div className="flex items-center gap-4">
                                <div className="flex items-center gap-2">
                                    <div className="w-6 h-6 bg-[#2383e2]/10 rounded-lg flex items-center justify-center">
                                        <Server className="w-3.5 h-3.5 text-[#2383e2]" />
                                    </div>
                                    <h3 className="text-[11px] font-black text-[#31302c] uppercase tracking-wider">
                                        原始采样数据预览
                                    </h3>
                                </div>
                                <div className="h-3 w-[1px] bg-[#f1f1f0]" />
                                <span className="text-[10px] font-bold text-[#b4b4b3]">当前预览 {dataInfo?.preview?.length ?? 0} 条样本，可直接连续滚动浏览</span>
                            </div>
                            <div className="flex items-center gap-3">
                                {/* 紧凑质量指标 */}
                                <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-[#f1f1f0] text-[10px]">
                                    <span className="text-[#b4b4b3] font-bold">样本</span>
                                    <span className="text-[#31302c] font-black">{dataInfo?.shape[0]?.toLocaleString()}</span>
                                    <div className="w-[1px] h-3 bg-[#f1f1f0]" />
                                    <span className="text-[#b4b4b3] font-bold">特征</span>
                                    <span className="text-[#31302c] font-black">{dataInfo?.shape[1]}</span>
                                    <div className="w-[1px] h-3 bg-[#f1f1f0]" />
                                    <span className="text-[#b4b4b3] font-bold">质量</span>
                                    <span className="text-[#2383e2] font-black">{(qualityReport?.summary?.overall_score || 100).toFixed(0)}</span>
                                </div>
                                <div className="flex items-center gap-1.5 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">
                                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                                    <span className="text-[10px] font-black text-emerald-600">已连接</span>
                                </div>
                            </div>
                        </div>

                        {/* 警告条 */}
                        {(qualityReport?.summary?.warnings?.length ?? 0) > 0 && (
                            <div className="px-6 py-2 bg-orange-50/80 border-b border-orange-100 flex items-center gap-3 shrink-0">
                                <AlertCircle className="w-3.5 h-3.5 text-orange-500 shrink-0" />
                                <p className="text-[10px] text-orange-700 font-bold truncate">
                                    {qualityReport!.summary!.warnings[0]}
                                    {(qualityReport!.summary!.warnings.length > 1) && ` (+${qualityReport!.summary!.warnings.length - 1} 项)`}
                                </p>
                            </div>
                        )}

                        {/* 预处理结果条 */}
                        {processingResult && (
                            <div className="px-6 py-2 bg-[#f0fdf4] border-b border-emerald-100 flex items-center gap-3 shrink-0">
                                <CheckCircle className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                                <p className="text-[10px] text-emerald-700 font-bold">
                                    预处理完成 · {processingResult.final_shape.join('×')} · {processingResult.processing_log.length} 步操作
                                </p>
                            </div>
                        )}

                        <div className="px-6 py-2 border-b border-[#f1f1f0] bg-[#f8fafc] text-[10px] text-[#787774] font-bold shrink-0">
                            支持横向滚动查看全部特征列，支持纵向连续滚动浏览全部预览样本。
                        </div>
                        <div className="flex-1 overflow-auto custom-scrollbar">
                            <table className="w-max min-w-full text-left border-collapse">
                                <thead className="bg-[#fbfbfa] border-b border-[#f1f1f0] sticky top-0 z-20 shadow-sm">
                                    <tr>
                                        {dataInfo?.columns?.map((col: string, i: number) => (
                                            <th key={i} className="px-4 py-3 text-[10px] font-black uppercase tracking-[0.12em] text-[#6f6f6f] bg-[#fbfbfa]/90 backdrop-blur-md border-r border-[#f1f1f0]/40 last:border-r-0 whitespace-nowrap">
                                                {col}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[#f1f1f0]">
                                    {dataInfo?.preview?.map((row, rIndex: number) => (
                                        <tr key={rIndex} className="hover:bg-[#f9f9f8] transition-colors group">
                                            {dataInfo?.columns?.map((col: string, cIndex: number) => (
                                                <td key={cIndex} className="px-4 py-2.5 text-[11px] font-medium text-[#31302c] border-r border-[#f1f1f0]/20 last:border-r-0 whitespace-nowrap min-w-[140px] max-w-[280px]">
                                                    {String(row[col]) === 'NaN' || row[col] === null || row[col] === '' ?
                                                        <span className="text-red-400 bg-red-50 px-1 rounded">NULL</span> :
                                                        <span className="opacity-80 group-hover:opacity-100 transition-opacity font-mono text-[10px]">{String(row[col])}</span>
                                                    }
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
