import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Layers, Download, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { API_ENDPOINTS } from '../utils/api';

const API_ALGO = API_ENDPOINTS.ALGORITHM;

const AnalysisResult: React.FC = () => {
    const [searchParams] = useSearchParams();
    const taskId = searchParams.get('task_id');
    const [task, setTask] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const fetchStatus = async () => {
        if (!taskId) return;
        try {
            const resp = await axios.get(`${API_ALGO}/task_status/${taskId}`);
            setTask(resp.data);
            if (resp.data.status === 'running' || resp.data.status === 'pending') {
                setTimeout(fetchStatus, 1500);
            }
        } catch (e) { }
    };

    useEffect(() => {
        if (taskId) {
            setLoading(true);
            fetchStatus();
        }
    }, [taskId]);

    const handleDownload = () => {
        if (!task || !task.result || !task.result.rules) return;
        const rules = task.result.rules;

        let csvContent = "data:text/csv;charset=utf-8,\uFEFF";
        csvContent += "前项 (Antecedents),后项 (Consequents),支持度,置信度,提升度,P-Value,是否显著\n";

        rules.forEach((r: any) => {
            const ant = r.antecedents.join(" & ").replace(/,/g, "，");
            const con = r.consequents.join(" & ").replace(/,/g, "，");
            csvContent += `"${ant}","${con}",${r.support},${r.confidence},${r.lift},${r.p_value},${r.significant ? '是' : '否'}\n`;
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `association_rules_${taskId.split('-')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    if (!taskId) return <div className="text-center py-20 font-bold text-[#8e8e8e]">无分析任务 ID</div>;

    if (!task) return <div className="text-center py-20 italic text-[#8e8e8e]">初始化引擎状态...</div>;

    const rules = task.result?.rules || [];

    return (
        <div className="max-w-6xl mx-auto py-2">
            <div className="flex items-center justify-between mb-8 bg-white p-5 rounded-2xl border border-[#e9e9e8] shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight mb-2 flex items-center gap-3">
                        智能关联分析报告
                        {task.status === 'completed' && <CheckCircle2 className="text-emerald-500" size={24} />}
                    </h1>
                    <div className="flex items-center gap-4 text-xs font-bold tracking-widest text-[#8e8e8e] uppercase">
                        <span className="bg-[#f0f0f0] px-2 py-0.5 rounded text-[#555]">ID: {taskId.split('-')[0]}</span>
                        <span>•</span>
                        <span>开始时间: {task.start_time}</span>
                    </div>
                </div>
                {task.status === 'completed' && (
                    <button
                        onClick={handleDownload}
                        className="notion-btn-primary flex items-center gap-2 px-6 shadow-sm hover:shadow-md transition-all active:scale-95"
                    >
                        <Download size={18} />
                        导出 CSV 报告
                    </button>
                )}
            </div>

            {task.status !== 'completed' && task.status !== 'failed' && (
                <div className="notion-card p-12 text-center bg-white/50 border-dashed animate-pulse my-8">
                    <RefreshCw className="animate-spin mx-auto mb-6 text-primary-500" size={48} />
                    <h3 className="text-xl font-bold mb-3 text-[#37352f]">{task.message || '正在分析中...'}</h3>
                    <div className="max-w-md mx-auto h-3 bg-gray-100 rounded-full mt-8 overflow-hidden">
                        <div className="h-full bg-primary-500 transition-all duration-500" style={{ width: `${task.progress}%` }} />
                    </div>
                    <p className="text-xs text-[#8e8e8e] mt-4 font-black">{task.progress}% COMPLETED</p>
                </div>
            )}

            {task.status === 'completed' && (
                <div className="space-y-8 animate-fade-in-up">
                    <div className="grid grid-cols-4 gap-6">
                        {[
                            { label: '生成的关联规则总数', val: rules.length, color: 'text-primary-600', sub: 'RULESET_TOTAL', bg: 'bg-primary-50' },
                            { label: '统计显著性规则 (P<0.05)', val: rules.filter((r: any) => r.significant).length, color: 'text-emerald-600', sub: 'SIG_RATIO', bg: 'bg-emerald-50' },
                            { label: '整体平均置信度', val: `${(rules.reduce((a: any, r: any) => a + r.confidence, 0) / Math.max(1, rules.length) * 100).toFixed(1)}%`, color: 'text-amber-600', sub: 'AVG_CONF', bg: 'bg-amber-50' },
                            { label: '挖掘出的最高提升度', val: Math.max(0, ...rules.map((r: any) => r.lift)).toFixed(2), color: 'text-indigo-600', sub: 'PEAK_LIFT', bg: 'bg-indigo-50' },
                        ].map((s, i) => (
                            <div key={i} className="notion-card p-6 flex flex-col relative overflow-hidden group">
                                <div className={`absolute -right-6 -top-6 w-24 h-24 rounded-full opacity-50 transition-transform group-hover:scale-110 ${s.bg}`}></div>
                                <span className="text-[10px] font-black text-[#8e8e8e] uppercase tracking-widest mb-2 z-10">{s.sub}</span>
                                <span className={`text-4xl font-black mb-2 z-10 ${s.color}`}>{s.val}</span>
                                <span className="text-xs font-bold text-[#37352f] z-10">{s.label}</span>
                            </div>
                        ))}
                    </div>

                    <div className="notion-card">
                        <div className="p-6 flex items-center justify-between border-b border-[#e9e9e8]">
                            <h3 className="text-lg font-bold flex items-center gap-2">
                                <Layers size={20} className="text-[#37352f]" />
                                挖掘规则明细大纲
                            </h3>
                            <div className="flex gap-4">
                                <span className="flex items-center gap-1.5 text-xs text-[#8e8e8e] font-bold">
                                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-sm" />
                                    表示该规则具有统计显著性
                                </span>
                            </div>
                        </div>

                        <div className="overflow-x-auto bg-white rounded-b-lg">
                            <table className="w-full text-sm text-left border-collapse">
                                <thead className="bg-[#f7f6f3] text-[11px] font-black uppercase text-[#8e8e8e] tracking-wider">
                                    <tr>
                                        <th className="px-6 py-4">条件前项 (Antecedents)</th>
                                        <th className="px-6 py-4">结论后项 (Consequents)</th>
                                        <th className="px-6 py-4 text-center">支持度</th>
                                        <th className="px-6 py-4 text-center">置信度</th>
                                        <th className="px-6 py-4 text-center">提升度</th>
                                        <th className="px-6 py-4 text-center">P-Value</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[#e9e9e8]">
                                    {rules.map((rule: any, i: number) => (
                                        <tr key={i} className={`hover:bg-[#fbfbfa] transition-colors ${rule.significant ? '' : 'opacity-75'}`}>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-wrap gap-1.5">
                                                    {rule.antecedents.map((a: string, ai: number) => (
                                                        <span key={ai} className="px-2.5 py-1 bg-blue-50/80 text-blue-700 rounded-md text-xs border border-blue-100/50 font-medium tracking-wide">{a}</span>
                                                    ))}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex flex-wrap gap-1.5">
                                                    {rule.consequents.map((c: string, ci: number) => (
                                                        <span key={ci} className="px-2.5 py-1 bg-indigo-50/80 text-indigo-700 rounded-md text-xs border border-indigo-100/50 font-medium tracking-wide">{c}</span>
                                                    ))}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-center font-bold text-[#555]">{(rule.support * 100).toFixed(1)}%</td>
                                            <td className="px-6 py-4 text-center">
                                                <div className="flex flex-col items-center gap-1.5">
                                                    <span className="font-bold text-[#37352f]">{(rule.confidence * 100).toFixed(0)}%</span>
                                                    <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                                        <div className="h-full bg-amber-400" style={{ width: `${rule.confidence * 100}%` }} />
                                                    </div>
                                                </div>
                                            </td>
                                            <td className={`px-6 py-4 text-center font-black ${rule.lift > 1.2 ? 'text-indigo-600' : 'text-[#8e8e8e]'}`}>
                                                {rule.lift.toFixed(2)}
                                                <span className="block text-[10px] font-normal text-[#8e8e8e] mt-1">LIFT</span>
                                            </td>
                                            <td className={`px-6 py-4 text-center ${rule.significant ? 'text-emerald-600' : 'text-gray-400'}`}>
                                                <div className="font-bold text-base">{rule.p_value < 0.001 ? '<0.001' : rule.p_value.toFixed(4)}</div>
                                                {rule.significant ?
                                                    <span className="inline-block mt-0.5 px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-sm text-[9px] font-bold tracking-widest">SIGNIFICANT</span>
                                                    :
                                                    <span className="inline-block mt-0.5 px-2 py-0.5 bg-gray-100 text-gray-500 rounded-sm text-[9px] font-bold tracking-widest">NOT SIG.</span>
                                                }
                                            </td>
                                        </tr>
                                    ))}
                                    {rules.length === 0 && (
                                        <tr>
                                            <td colSpan={6} className="px-6 py-24 text-center">
                                                <AlertCircle className="mx-auto mb-4 text-[#8e8e8e]" size={36} />
                                                <p className="text-[#37352f] font-bold text-lg mb-2">未挖掘出关联规则</p>
                                                <p className="text-[#8e8e8e] text-sm">未能找到满足当前统计阈值的特征对。您可以尝试在「算法配置」中降低支持度或置信度要求。</p>
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}

            {task.status === 'failed' && (
                <div className="notion-card p-24 text-center border-rose-200 bg-rose-50/30">
                    <AlertCircle className="mx-auto mb-6 text-rose-500" size={56} />
                    <h3 className="text-2xl font-bold mb-3 text-rose-800">分析任务意外终止</h3>
                    <p className="text-rose-600/80 mb-10 max-w-lg mx-auto leading-relaxed">{task.message}</p>
                    <button onClick={() => window.location.reload()} className="notion-btn-primary bg-rose-600 hover:bg-rose-700 shadow-md">重新尝试分析</button>
                </div>
            )}
        </div>
    );
};

export default AnalysisResult;
