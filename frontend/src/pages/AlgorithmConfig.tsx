import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Settings2, Play, Info, Check, BrainCircuit } from 'lucide-react';
import { API_ENDPOINTS } from '../utils/api';

const API_ALGO = API_ENDPOINTS.ALGORITHM;

const AlgorithmConfig: React.FC = () => {
    const navigate = useNavigate();
    const [params, setParams] = useState({
        min_support: 0.05,
        min_confidence: 0.4,
        min_lift: 1.0,
        max_len: 2,
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const runAnalysis = async () => {
        setLoading(true);
        setError('');
        try {
            const resp = await axios.post(`${API_ALGO}/start_task`, { params });
            if (resp.data.success) {
                // 跳转到结果页，并带上 task_id
                navigate(`/analysis?task_id=${resp.data.task_id}`);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || '启动失败');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto py-4">
            <div className="mb-10 flex items-center gap-3">
                <div className="bg-primary-50 p-3 rounded-2xl text-primary-600">
                    <BrainCircuit size={32} />
                </div>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">智能算法配置</h1>
                    <p className="text-[#8e8e8e] text-sm">调节启发式挖掘因子，平衡规则的广度与显著性。</p>
                </div>
            </div>

            <div className="grid grid-cols-3 gap-8">
                <div className="col-span-2 space-y-6">
                    <section className="notion-card p-8">
                        <h3 className="font-bold flex items-center gap-2 mb-6 text-lg border-b pb-4">
                            <Settings2 size={20} className="text-primary-500" />
                            关联规则参数
                        </h3>

                        <div className="grid grid-cols-2 gap-x-10 gap-y-8">
                            <div>
                                <label className="text-xs font-bold text-[#8e8e8e] uppercase block mb-2 px-1">最小支持度 (Min Support)</label>
                                <div className="flex items-center gap-4">
                                    <input
                                        type="range" min="0.001" max="1" step="0.01"
                                        className="flex-1 h-1 bg-[#efefee] rounded-full appearance-none cursor-pointer accent-primary-500"
                                        value={params.min_support}
                                        onChange={e => setParams({ ...params, min_support: parseFloat(e.target.value) })}
                                    />
                                    <span className="text-sm font-bold w-12 text-right">{(params.min_support * 100).toFixed(1)}%</span>
                                </div>
                                <p className="text-[10px] text-[#8e8e8e] mt-2 px-1 italic">通常设为 1%-10%，过高可能漏掉长尾关联。</p>
                            </div>

                            <div>
                                <label className="text-xs font-bold text-[#8e8e8e] uppercase block mb-2 px-1">最小置信度 (Min Confidence)</label>
                                <div className="flex items-center gap-4">
                                    <input
                                        type="range" min="0.1" max="1" step="0.05"
                                        className="flex-1 h-1 bg-[#efefee] rounded-full appearance-none cursor-pointer accent-primary-500"
                                        value={params.min_confidence}
                                        onChange={e => setParams({ ...params, min_confidence: parseFloat(e.target.value) })}
                                    />
                                    <span className="text-sm font-bold w-12 text-right">{(params.min_confidence * 100).toFixed(0)}%</span>
                                </div>
                                <p className="text-[10px] text-[#8e8e8e] mt-2 px-1 italic">推荐 {'>'} 50%，反映 A 发生时 B 发生的确定性。</p>
                            </div>

                            <div>
                                <label className="text-xs font-bold text-[#8e8e8e] uppercase block mb-2 px-1">最小提升度 (Min Lift)</label>
                                <div className="flex items-center gap-4">
                                    <input
                                        type="number" step="0.1" min="0"
                                        className="flex-1 border rounded px-3 py-1.5 text-sm bg-white"
                                        value={params.min_lift}
                                        onChange={e => setParams({ ...params, min_lift: parseFloat(e.target.value) })}
                                    />
                                </div>
                                <p className="text-[10px] text-[#8e8e8e] mt-2 px-1 italic">提升度 {'>'} 1 表示正相关，推荐设为 1.1 或更高。</p>
                            </div>

                            <div>
                                <label className="text-xs font-bold text-[#8e8e8e] uppercase block mb-2 px-1">挖掘层级 (Max Depth)</label>
                                <select
                                    className="w-full border rounded px-3 py-1.5 text-sm bg-white"
                                    value={params.max_len}
                                    onChange={e => setParams({ ...params, max_len: parseInt(e.target.value) })}
                                >
                                    <option value={2}>2级 (双变量 / 推荐)</option>
                                    <option value={3}>3级 (三元组合)</option>
                                    <option value={4}>4级 (高维挖掘)</option>
                                </select>
                                <p className="text-[10px] text-[#8e8e8e] mt-2 px-1 italic">层级越高计算开销越大，软著版本默认聚焦双变量。</p>
                            </div>
                        </div>

                        <div className="mt-14 flex items-center justify-between p-4 bg-primary-50 rounded-xl border border-primary-100/50">
                            <div className="flex items-center gap-3">
                                <div className="bg-white p-2 rounded-full shadow-sm text-primary-500">
                                    <Check size={16} strokeWidth={3} />
                                </div>
                                <div>
                                    <p className="text-sm font-bold text-primary-900">配置已就绪</p>
                                    <p className="text-[10px] text-primary-700/70 uppercase font-bold tracking-widest">Scientific Protocol Ready</p>
                                </div>
                            </div>
                            <button
                                onClick={runAnalysis}
                                disabled={loading}
                                className="notion-btn-primary flex items-center gap-2 px-6 py-2.5 shadow-lg shadow-primary-500/20 active:scale-95 disabled:opacity-50"
                            >
                                <Play size={18} fill="white" />
                                {loading ? '初始化引擎...' : '开始挖掘分析'}
                            </button>
                        </div>
                        {error && <p className="text-red-500 text-xs mt-4 text-center font-bold">⚠️ {error}</p>}
                    </section>
                </div>

                <div className="col-span-1 space-y-4">
                    <div className="notion-card p-6 bg-[#f7f6f3] border-none shadow-none text-sm">
                        <h4 className="flex items-center gap-2 font-bold mb-3 text-[#37352f]">
                            <Info size={16} className="text-[#37352f]" />
                            算法说明
                        </h4>
                        <p className="text-[#8e8e8e] leading-relaxed mb-4">
                            本平台采用优化后的 <strong>启发式 Apriori 算法</strong>。在每一轮生成项集时，系统会自动剔除不满足最小支持度的无效分支，大幅缩减搜索空间。
                        </p>
                        <p className="text-[#8e8e8e] leading-relaxed">
                            所有生成的规则将自动进行 <strong>Fisher/Chi-Square 统计显著性校验</strong>，确保结果非随机共现。
                        </p>
                    </div>

                    <div className="notion-card p-6 bg-amber-50/30 border-amber-100 border text-sm">
                        <h4 className="flex items-center gap-2 font-bold mb-3 text-amber-900/80">
                            ⚡ 性能提示
                        </h4>
                        <p className="text-amber-800/60 leading-relaxed text-xs italic">
                            对于超过 10 万行的数据集，建议将最小支持度略微提高到 5% 以上，以获得秒级响应体验。
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AlgorithmConfig;
