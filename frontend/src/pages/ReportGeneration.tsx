import { useState } from 'react';
import {
    FileText, Download, CheckCircle, Briefcase, RefreshCw, Presentation, MonitorCheck, LayoutTemplate, Brain
} from 'lucide-react';
import { cn } from '../utils/cn';
import { reportService, aiService, extractErrorMessage } from '../services/api';
import { useToast } from '../components/Toast';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { useAbortEffect } from '../hooks/useAbortEffect';
import type { ReportForm } from '../types';

const TEMPLATE_OPTIONS = [
    { v: 'basic', l: '综合分析模板', d: '通用场景，包含数据概况、规则挖掘、统计检验与 AI 解读' },
    { v: 'financial_risk', l: '金融风控模板', d: '红色风控主题，突出风险因子关联与显著性检验' },
    { v: 'medical_research', l: '医学研究模板', d: '等同综合分析，适用于临床数据与症状关联分析' },
    { v: 'market_analysis', l: '市场分析模板', d: '绿色营销主题，侧重购物篮关联与市场趋势可视化' },
] as const;

export default function ReportGeneration() {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [statusText, setStatusText] = useState('');
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');

    const [form, setForm] = useState<ReportForm>({
        title: '',
        templateType: 'financial_risk',
        author: '系统自动生成',
        date: new Date().toLocaleDateString('zh-CN'),
        include_visuals: true
    });

    const [useAiSummary, setUseAiSummary] = useState(false);
    const [aiAvailable, setAiAvailable] = useState(false);
    const [aiStatus, setAiStatus] = useState<'checking' | 'available' | 'unavailable'>('checking');

    useAbortEffect((signal) => {
        setAiStatus('checking');
        aiService.checkStatus(signal)
            .then(res => {
                setAiAvailable(res.available);
                setAiStatus(res.available ? 'available' : 'unavailable');
                if (!res.available) {
                    setUseAiSummary(false);
                }
            })
            .catch(() => {
                setAiAvailable(false);
                setAiStatus('unavailable');
                setUseAiSummary(false);
            });
    }, []);

    const retryAiStatus = async () => {
        setAiStatus('checking');
        try {
            const res = await aiService.checkStatus();
            setAiAvailable(res.available);
            setAiStatus(res.available ? 'available' : 'unavailable');
            if (!res.available) {
                setUseAiSummary(false);
            }
        } catch {
            setAiAvailable(false);
            setAiStatus('unavailable');
            setUseAiSummary(false);
        }
    };

    const handleGenerate = async () => {
        setLoading(true);
        setError('');
        setSuccess(false);
        setStatusText(useAiSummary
            ? '正在汇总规则证据、统计检验与图表摘要，并请求 AI 生成执行摘要...'
            : '正在搜集后台算法流水数据并整合图表快照...');

        try {
            const payload = { ...form, title: form.title.trim(), use_ai_summary: useAiSummary };
            const res = await reportService.generateReport(payload);

            if (res.success && res.report_id) {
                setStatusText('文档编排成功！正在拉取文件...');

                const blob = await reportService.downloadReport(res.report_id);
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', `${res.title || payload.title || '分析报告'}.html`);
                document.body.appendChild(link);
                link.click();
                link.parentNode?.removeChild(link);
                window.URL.revokeObjectURL(url);

                setSuccess(true);
                toast.success('报告文件已成功下载');
            }
        } catch (e) {
            setError(extractErrorMessage(e, '由于近期未有运算分析存档数据，导致无法编排出正式报告。请先回到算力配置台运行程序。'));
        } finally {
            setLoading(false);
            setStatusText('');
        }
    };

    return (
        <div className="max-w-4xl mx-auto py-8 px-4 h-full overflow-y-auto font-sans">
            <div className="mb-8 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="bg-[#2383e2]/10 p-3 rounded-xl text-[#2383e2]">
                        <Presentation size={28} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-[#37352f]">报告生成</h1>
                        <p className="text-[#787774] text-sm mt-1">组合预处理器、算法结论与显著性规则网，装订为业务汇报型交互文档。</p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                {/* 封面表单配置 */}
                <div className="notion-card p-6 bg-white border-[#e9e9e8] shadow-sm animate-in fade-in slide-in-from-bottom-2">
                    <h3 className="font-bold flex items-center gap-2 mb-6 text-[#37352f] border-b border-[#e9e9e8] pb-3 text-[15px]">
                        <LayoutTemplate size={18} className="text-[#2383e2]" />
                        公文规范与元数据配置
                    </h3>

                    <div className="space-y-5">
                        <div>
                            <label className="text-xs font-semibold text-[#787774] block uppercase tracking-wider mb-2">报告全宗标题</label>
                            <Input
                                type="text"
                                value={form.title}
                                onChange={(e) => setForm({ ...form, title: e.target.value })}
                                placeholder="留空时自动按当前数据集、模板类型与规则结果生成标题"
                            />
                            <p className="mt-2 text-[11px] leading-relaxed text-[#787774]">
                                如果你不手动填写，系统会自动生成类似“数据集名 · 模板类型 · 规则数”的报告标题；只有你主动输入时才会覆盖自动命名。
                            </p>
                        </div>

                        <div>
                            <label className="text-xs font-semibold text-[#787774] block uppercase tracking-wider mb-2">生成版式 / 细分行业模板</label>
                            <div className="flex flex-col gap-2">
                                {TEMPLATE_OPTIONS.map(t => (
                                    <label key={t.v} className={cn("flex flex-1 items-center gap-2 p-2.5 border rounded-lg cursor-pointer transition-all text-sm", form.templateType === t.v ? "border-[#2383e2] bg-[#ebf3fb] text-[#2383e2] shadow-sm" : "border-[#e9e9e8] text-[#787774] hover:bg-[#f9f9f8]")}>
                                        <Briefcase size={16} className={cn("shrink-0", form.templateType === t.v ? "text-[#2383e2]" : "text-[#d3d3d3]")} />
                                        <div className="flex flex-col">
                                            <span className="font-medium">{t.l}</span>
                                            <span className={cn("text-[10px] leading-tight", form.templateType === t.v ? "text-[#2383e2]/70" : "text-[#a5a5a3]")}>{t.d}</span>
                                        </div>
                                        <input type="radio" className="hidden" name="tpl" checked={form.templateType === t.v} onChange={() => setForm({ ...form, templateType: t.v as ReportForm['templateType'] })} />
                                    </label>
                                ))}
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 pt-2 border-t border-[#e9e9e8]">
                            <div>
                                <label className="text-xs font-semibold text-[#787774] block mb-2">署名编者</label>
                                <input type="text" value={form.author} onChange={e => setForm({ ...form, author: e.target.value })} className="w-full text-sm p-2 border border-[#e9e9e8] rounded outline-none" />
                            </div>
                            <div>
                                <label className="text-xs font-semibold text-[#787774] block mb-2">归档日期</label>
                                <input type="text" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} className="w-full text-sm p-2 border border-[#e9e9e8] rounded outline-none" readOnly />
                            </div>
                        </div>

                        <label className="flex items-start gap-2 pt-2 cursor-pointer text-[#787774] text-xs">
                            <input type="checkbox" className="accent-[#2383e2] mt-0.5" checked={form.include_visuals} onChange={e => setForm({ ...form, include_visuals: e.target.checked })} />
                            包含预构建的静态雷达与关系图斑序列 (这将微增文档体积)
                        </label>

                        {/* AI 智能摘要开关 */}
                        <div className={cn(
                            "mt-3 rounded-xl border p-4 transition-all",
                            aiStatus === 'checking'
                                ? "bg-slate-50 border-slate-200 text-slate-900"
                                : useAiSummary && aiAvailable
                                ? "bg-gradient-to-r from-[#37352f] to-[#25242a] border-transparent text-white shadow-lg shadow-black/10"
                                : aiAvailable
                                    ? "bg-[#f8fafc] border-[#e9eef5] text-[#37352f]"
                                    : "bg-amber-50 border-amber-200 text-amber-900"
                        )}>
                            <div className="flex items-start justify-between gap-4">
                                <div className="flex items-start gap-3">
                                    <div className={cn(
                                        "p-2 rounded-lg border",
                                        aiStatus === 'checking'
                                            ? "bg-white border-slate-200"
                                            : useAiSummary && aiAvailable
                                            ? "bg-emerald-400/20 border-emerald-400/30"
                                            : aiAvailable
                                                ? "bg-white border-[#dfe7f1]"
                                                : "bg-white/80 border-amber-200"
                                    )}>
                                        <Brain size={18} className={aiStatus === 'checking' ? "text-slate-500" : useAiSummary && aiAvailable ? "text-emerald-400" : aiAvailable ? "text-[#2383e2]" : "text-amber-600"} />
                                    </div>
                                    <div>
                                        <div className="text-sm font-black flex items-center gap-2 flex-wrap">
                                            AI 智能执行摘要
                                            <span className={cn(
                                                "text-[8px] px-1.5 py-0.5 rounded-full uppercase tracking-tighter",
                                                aiStatus === 'checking'
                                                    ? "bg-slate-200 text-slate-700"
                                                    : useAiSummary && aiAvailable
                                                    ? "bg-emerald-500 text-white"
                                                    : aiAvailable
                                                        ? "bg-[#e9eef5] text-[#57738e]"
                                                        : "bg-amber-100 text-amber-700"
                                            )}>
                                                {aiStatus === 'checking' ? '检测中' : aiAvailable ? 'DeepSeek' : '暂不可用'}
                                            </span>
                                        </div>
                                        <div className={cn(
                                            "text-[10px] mt-0.5 leading-relaxed",
                                            aiStatus === 'checking'
                                                ? "text-slate-600"
                                                : useAiSummary && aiAvailable
                                                ? "text-gray-400"
                                                : aiAvailable
                                                    ? "text-[#787774]"
                                                    : "text-amber-700/90"
                                        )}>
                                            {aiStatus === 'checking'
                                                ? '正在检测 AI 摘要服务状态，请稍等片刻；检测完成后会自动更新是否可开启。'
                                                : aiAvailable
                                                ? '控制本次导出报告是否附带 AI 执行摘要；不代表该任务之前是否已经生成过 AI 解读记录。'
                                                : '这不是“功能消失”，只是当前前端暂时没拿到可用状态；你可以重新检测，恢复后即可直接开启。'}
                                        </div>
                                    </div>
                                </div>
                                <label className={cn("relative inline-flex items-center shrink-0 mt-0.5", aiStatus === 'available' ? "cursor-pointer" : "cursor-not-allowed opacity-70")}>
                                    <input
                                        type="checkbox"
                                        className="sr-only peer"
                                        checked={useAiSummary && aiStatus === 'available'}
                                        disabled={aiStatus !== 'available'}
                                        onChange={e => setUseAiSummary(e.target.checked)}
                                    />
                                    <div className={cn(
                                        "w-10 h-5 rounded-full peer-focus:outline-none after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all",
                                        aiStatus === 'available'
                                            ? "bg-gray-600 peer-checked:bg-emerald-500 peer-checked:after:translate-x-full"
                                            : aiStatus === 'checking'
                                                ? "bg-slate-300"
                                                : "bg-amber-200"
                                    )}></div>
                                </label>
                            </div>

                            <div className="mt-4 grid grid-cols-2 gap-2">
                                {['执行结论', '关键发现', '管理建议', '风险提示'].map((item) => (
                                    <div
                                        key={item}
                                        className={cn(
                                            "rounded-lg border px-3 py-2 text-[11px] font-bold",
                                            aiStatus === 'checking'
                                                ? "border-slate-200 bg-white/80 text-slate-500"
                                                : useAiSummary && aiAvailable
                                                ? "border-white/10 bg-white/5 text-gray-100"
                                                : aiAvailable
                                                    ? "border-[#e9eef5] bg-white text-[#556274]"
                                                    : "border-amber-200 bg-white/70 text-amber-800"
                                        )}
                                    >
                                        {item}
                                    </div>
                                ))}
                            </div>

                            <div className={cn(
                                "mt-3 text-[10px] leading-relaxed",
                                aiStatus === 'checking'
                                    ? "text-slate-600"
                                    : useAiSummary && aiAvailable
                                    ? "text-gray-400"
                                    : aiAvailable
                                        ? "text-[#8a94a3]"
                                        : "text-amber-700/80"
                            )}>
                                {aiStatus === 'checking'
                                    ? '如果检测成功，你可以在这里自主选择是否把 AI 执行摘要加入最终报告。'
                                    : aiAvailable
                                    ? '开启后仅影响这一次导出的最终报告；分析结果页或历史记录里已有的 AI 解读是否存在，和这里不是一回事。'
                                    : '当前仍可生成常规报告；待 AI 服务可用后，你可以在这里自主选择是否把 AI 执行摘要加入最终报告。'}
                            </div>

                            {aiStatus !== 'available' && (
                                <div className="mt-3">
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        onClick={retryAiStatus}
                                        disabled={aiStatus === 'checking'}
                                        className={cn(
                                            "text-xs",
                                            aiStatus === 'checking'
                                                ? "border-slate-200 text-slate-500 bg-white"
                                                : "border-amber-200 text-amber-700 bg-white hover:bg-amber-50"
                                        )}
                                    >
                                        <RefreshCw size={14} className={cn(aiStatus === 'checking' && 'animate-spin')} />
                                        {aiStatus === 'checking' ? '正在检测 AI 状态...' : '重新检测 AI 状态'}
                                    </Button>
                                </div>
                            )}
                        </div>

                        <Button
                            disabled={loading}
                            onClick={handleGenerate}
                            className={cn(
                                "w-full mt-4 transition-all",
                                loading && "bg-[#2f7fd8] hover:bg-[#2f7fd8] text-white shadow-sm"
                            )}
                            size="lg"
                        >
                            {loading ? <RefreshCw size={18} className="animate-spin" /> : <Download size={18} />}
                            {loading ? '正在生成报告...' : '生成并下载报告'}
                        </Button>

                        {loading && statusText && (
                            <div className="mt-3 rounded-xl border border-[#dbe7f3] bg-gradient-to-r from-[#f7fbff] to-[#f3f8fd] px-4 py-3 text-xs text-[#5f6b7a] shadow-sm">
                                <div className="flex items-center gap-2 text-[11px] font-semibold text-[#2f6da8]">
                                    <span className="inline-flex h-2 w-2 rounded-full bg-[#2383e2] animate-pulse" />
                                    生成进行中
                                </div>
                                <p className="mt-1 leading-relaxed text-[#6b7280]">
                                    {statusText}
                                </p>
                            </div>
                        )}

                        {error && (
                            <div className="p-3 bg-red-50 text-red-600 rounded-md border border-red-100 flex items-start gap-2 text-xs leading-relaxed">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 mt-0.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                                {error}
                            </div>
                        )}

                        {success && !loading && (
                            <div className="p-3 bg-emerald-50 text-emerald-700 font-medium rounded-md border border-emerald-100 flex items-center justify-between text-sm shadow-sm animate-in fade-in">
                                <span className="flex items-center gap-2"><CheckCircle size={16} /> 文件流已装卸到您的本地磁盘！</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* 右侧展示或预览 */}
                <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-right-4">
                    {/* 样式模拟卡 */}
                    <div className="notion-card bg-gradient-to-br from-gray-800 to-gray-900 border-[#30363d] p-6 text-white shadow-2xl relative overflow-hidden group">
                        <div className="absolute -right-16 -top-16 opacity-10 pointer-events-none transition-transform group-hover:rotate-12 duration-500">
                            <Briefcase size={200} />
                        </div>
                        <h4 className="flex items-center gap-2 font-bold mb-6 text-gray-300 pb-2 border-b border-gray-700 text-sm">
                            <MonitorCheck size={16} className="text-blue-400" />
                            沉浸式 HTML 载体优点
                        </h4>
                        <ul className="space-y-4 text-xs text-gray-400 font-serif tracking-wide leading-relaxed">
                            <li className="flex items-start gap-3">
                                <span className="text-blue-400 font-bold opacity-80">1</span>
                                无需借助任何外部后端或互联网解析服务即可阅览报告全集图文数据。
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="text-blue-400 font-bold opacity-80">2</span>
                                自包含 (Self-contained) 支持。内部数据表可以直接执行检索、分页与再过滤。
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="text-blue-400 font-bold opacity-80">3</span>
                                完全符合 W3C 以及企业合规标准，可轻易被 PDF 打印机或者第三方截图工具归档。
                            </li>
                        </ul>
                    </div>

                    <div className="notion-card p-5 bg-[#fbfbfa] border-[#e9e9e8] border-dashed flex flex-col items-center justify-center min-h-[160px] text-center">
                        <FileText size={40} className="text-[#e9e9e8] mb-3" />
                        <h4 className="text-[#37352f] font-bold text-sm mb-1">跨平台共享支持</h4>
                        <p className="text-[#787774] text-xs max-w-xs leading-relaxed">请直接将生成的 .html 通过办公沟通工具（如飞书、企业微信）发送给协作成员或业务分析岗同仁。</p>
                    </div>
                </div>
            </div>
        </div>
    );
}

