import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Database, Settings2, LineChart, FileText,
    ArrowRight, Sparkles, ShieldCheck, Zap, Globe, Activity, Brain, Server
} from 'lucide-react';
import { motion } from 'framer-motion';
import { algorithmService } from '../services/api';
import { useCountUp } from '../hooks/useCountUp';
import { useAbortEffect } from '../hooks/useAbortEffect';
import type { HomeStats } from '../types';

// 静态数据移到组件外部，避免每次渲染重新创建
const features = [
    {
        title: '智能数据管理',
        desc: '支持多维数据导入与自动化质量评估，内置鲁棒的异常值检测与缺失值补全引擎。',
        icon: Database,
        color: 'text-emerald-500',
        bgColor: 'bg-emerald-50',
        path: '/data'
    },
    {
        title: '算法引擎配置',
        desc: '深度集成启发式关联挖掘策略，支持对变量间相关系数及统计显著性的毫秒级计算。',
        icon: Settings2,
        color: 'text-blue-500',
        bgColor: 'bg-blue-50',
        path: '/algorithm'
    },
    {
        title: '全景可视化交互',
        desc: '通过热力图、关联网络图及非参数分布图，直观呈现变量间错综复杂的关联脉络。',
        icon: LineChart,
        color: 'text-indigo-500',
        bgColor: 'bg-indigo-50',
        path: '/visualization'
    },
    {
        title: '专业分析报告',
        desc: '一键生成符合公文规范的分析全宗，涵盖所有统计检验结论及高分辨率视觉成果。',
        icon: FileText,
        color: 'text-amber-500',
        bgColor: 'bg-amber-50',
        path: '/report'
    },
];

const trustStats = [
    { label: '支持检测变量对', val: '10,000+', icon: Globe },
    { label: '非参数检验模型', val: '12 种', icon: ShieldCheck },
    { label: '平均 P 值计算精度', val: '1e-12', icon: Zap },
    { label: '合规性报告模板', val: '3 套', icon: FileText }
];

const HOME_STATS_STORAGE_KEY = 'home:stats-cache';

function getCachedHomeStats(): { stats: HomeStats; hasCache: boolean } {
    try {
        const raw = localStorage.getItem(HOME_STATS_STORAGE_KEY);
        if (!raw) {
            return { stats: { tasks: 0, rules: 0, records: 0 }, hasCache: false };
        }
        const parsed = JSON.parse(raw) as Partial<HomeStats>;
        const stats: HomeStats = {
            tasks: Number(parsed.tasks ?? 0),
            rules: Number(parsed.rules ?? 0),
            records: Number(parsed.records ?? 0)
        };
        return {
            stats,
            hasCache: Boolean(stats.tasks || stats.rules || stats.records)
        };
    } catch {
        return { stats: { tasks: 0, rules: 0, records: 0 }, hasCache: false };
    }
}

const Home: React.FC = () => {
    const navigate = useNavigate();
    const [stats, setStats] = useState<HomeStats>(() => getCachedHomeStats().stats);
    const [statsCached, setStatsCached] = useState(() => getCachedHomeStats().hasCache);

    useAbortEffect((signal) => {
        algorithmService.getHistory(signal)
            .then(res => {
                const tasks = res.tasks || [];
                const totalRules = tasks.reduce((acc, t) => acc + (t.rules_found || 0), 0);
                const totalRecords = tasks.reduce((acc, t) => acc + (t.records || 0), 0);
                const nextStats = { tasks: tasks.length, rules: totalRules, records: totalRecords };
                setStats(nextStats);
                setStatsCached(false);
                try {
                    localStorage.setItem(HOME_STATS_STORAGE_KEY, JSON.stringify(nextStats));
                } catch {
                    // ignore cache write errors
                }
            })
            .catch(() => { /* 忽略取消和网络错误 */ });
    }, []);

    const animTasks = useCountUp(stats.tasks);
    const animRules = useCountUp(stats.rules);
    const animRecords = useCountUp(stats.records);

    return (
        <div className="min-h-full bg-[#fbfbfa] overflow-x-hidden">
            {/* Compact Hero Section */}
            <div className="relative w-full bg-white border-b border-[#e9e9e8] overflow-hidden">
                <div className="max-w-6xl mx-auto px-6 pt-14 pb-20 md:pt-20 md:pb-24 text-center space-y-7 md:space-y-8 relative z-10">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-[10px] font-black tracking-widest uppercase border border-emerald-100 mb-2">
                        <Sparkles size={12} /> 启发式算法驱动 · 专业版 V1.0
                    </div>
                    <h1 className="text-[38px] sm:text-[44px] md:text-[58px] font-black text-[#37352f] leading-[1.06] tracking-[-0.05em]">
                        <span className="block">
                            专业的{' '}
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 via-teal-500 to-blue-600">
                                双变量关联挖掘
                            </span>
                        </span>
                        <span className="mt-1 block">
                            <span className="mr-2 text-[#37352f]/85">与</span>
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#111827] via-[#1f2937] to-[#334155]">
                                非参数统计分析
                            </span>
                            <span className="ml-2 text-[#37352f]">平台</span>
                        </span>
                    </h1>
                    <p className="text-[15px] md:text-lg text-[#787774] max-w-3xl leading-8 mx-auto font-medium px-2 break-keep">
                        “ 让繁杂的统计建模回归业务本质，通过启发式计算引擎释放潜藏的数据价值。 ”
                    </p>
                    <div className="flex flex-col sm:flex-row items-center gap-4 justify-center pt-3">
                        <button
                            onClick={() => navigate('/data')}
                            className="w-full sm:w-auto min-w-[220px] px-8 py-3.5 bg-[#2383e2] hover:bg-[#1d6dbd] text-white rounded-xl font-bold shadow-lg shadow-blue-500/20 transition-all flex items-center justify-center gap-2 group"
                        >
                            开始数据分析 <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                        </button>
                        <button
                            onClick={() => navigate('/help')}
                            className="w-full sm:w-auto min-w-[220px] px-8 py-3.5 bg-white border border-[#e9e9e8] text-[#37352f] rounded-xl font-bold hover:bg-[#f9f9f8] transition-all flex items-center justify-center gap-2"
                        >
                            查阅业务逻辑说明
                        </button>
                    </div>
                </div>

                {/* Subtle Background Decoration */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-50/30 rounded-full blur-3xl opacity-50 -translate-y-1/2 translate-x-1/2"></div>
                <div className="absolute bottom-0 left-0 w-64 h-64 bg-blue-50/30 rounded-full blur-3xl opacity-50 translate-y-1/2 -translate-x-1/2"></div>

                {/* Real-time System Pulse Bar */}
                <div className="max-w-5xl mx-auto px-6 -mt-7 md:-mt-8 relative z-20">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-[#1a1a1e] text-white rounded-[24px] px-6 py-6 md:px-8 md:py-7 shadow-2xl flex flex-col md:flex-row items-center justify-around gap-6 md:gap-8 border border-white/5"
                    >
                        <div className="flex items-center gap-4 group min-w-[180px]">
                            <div className="w-12 h-12 rounded-xl bg-primary-500/20 flex items-center justify-center text-primary-400">
                                <Activity size={24} className="animate-pulse" />
                            </div>
                            <div>
                                <div className="text-[10px] font-black uppercase tracking-widest text-gray-500">累计处理演算</div>
                                <div className="text-xl font-black tabular-nums">{animTasks} <span className="text-[10px] text-gray-500">Tasks</span></div>
                                {statsCached && <div className="mt-1 text-[10px] text-amber-300/80">缓存数据</div>}
                            </div>
                        </div>
                        <div className="w-px h-8 bg-white/10 hidden md:block" />
                        <div className="flex items-center gap-4 min-w-[180px]">
                            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                                <Brain size={24} />
                            </div>
                            <div>
                                <div className="text-[10px] font-black uppercase tracking-widest text-gray-500">析出有效规则</div>
                                <div className="text-xl font-black tabular-nums">{animRules} <span className="text-[10px] text-gray-500">Found</span></div>
                            </div>
                        </div>
                        <div className="w-px h-8 bg-white/10 hidden md:block" />
                        <div className="flex items-center gap-4 min-w-[180px]">
                            <div className="w-12 h-12 rounded-xl bg-orange-500/20 flex items-center justify-center text-orange-400">
                                <Server size={24} />
                            </div>
                            <div>
                                <div className="text-[10px] font-black uppercase tracking-widest text-gray-500">历史样本吞吐</div>
                                <div className="text-xl font-black tabular-nums">{animRecords.toLocaleString()} <span className="text-[10px] text-gray-500">Rows</span></div>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </div>

            {/* Feature Grid */}
            <div className="max-w-7xl mx-auto px-6 py-16 md:py-20">
                <div className="text-center mb-14 md:mb-16">
                    <h2 className="text-[28px] md:text-3xl font-bold text-[#37352f] mb-4">核心业务架构</h2>
                    <p className="max-w-2xl mx-auto text-sm md:text-base text-[#8e8e8e] leading-7 px-2 break-keep">
                        从数据接入、算法配置到结果解释与报告交付，形成完整的一站式分析闭环。
                    </p>
                    <div className="w-12 h-1 bg-emerald-500 mx-auto rounded-full"></div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 xl:gap-7">
                    {features.map((f, i) => (
                        <div
                            key={i}
                            onClick={() => navigate(f.path)}
                            className="group notion-card p-7 md:p-8 cursor-pointer bg-white hover:bg-[#fbfbfa] transition-all flex flex-col items-center text-center border-[#e9e9e8] h-full min-h-[320px]"
                        >
                            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-6 shadow-sm border border-[#f1f1f0] ${f.bgColor} ${f.color} group-hover:scale-110 group-hover:shadow-md transition-all`}>
                                <f.icon size={30} />
                            </div>
                            <h3 className="font-bold text-lg mb-3 text-[#37352f] group-hover:text-[#2383e2] transition-colors">
                                {f.title}
                            </h3>
                            <p className="text-[#8e8e8e] text-sm leading-relaxed mb-6 flex-grow">{f.desc}</p>
                            <div className="flex items-center gap-1 text-xs font-bold text-[#2383e2] opacity-0 group-hover:opacity-100 transition-opacity">
                                进入页面 <ArrowRight size={14} />
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Trust / Stats Section */}
            <div className="bg-white border-y border-[#e9e9e8] py-14 md:py-16">
                <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
                    {trustStats.map((s, i) => (
                        <div key={i} className="text-center space-y-2.5">
                            <div className="text-[#787774] flex justify-center mb-2"><s.icon size={20} /></div>
                            <div className="text-2xl md:text-3xl font-black text-[#37352f]">{s.val}</div>
                            <div className="text-xs text-[#8e8e8e] font-bold uppercase tracking-widest">{s.label}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Bottom CTA */}
            <div className="max-w-7xl mx-auto px-6 py-20 md:py-24 text-center">
                <div className="notion-card bg-gradient-to-r from-emerald-600 to-blue-700 px-8 py-12 md:px-12 md:py-16 lg:px-16 lg:py-20 text-white shadow-2xl relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl pointer-events-none group-hover:scale-150 transition-transform duration-1000"></div>
                    <div className="relative z-10">
                        <h2 className="text-[30px] md:text-[38px] font-black mb-5 leading-tight">准备好挖掘您的数据财富了吗？</h2>
                        <p className="text-base md:text-lg opacity-85 mb-10 max-w-3xl mx-auto leading-8 break-keep px-2">
                            基于启发式算法，我们将帮助您在海量数据中精准筛选出具有真实统计意义的关联因子。
                        </p>
                        <button
                            onClick={() => navigate('/data')}
                            className="px-10 md:px-12 py-4 md:py-5 bg-white text-blue-700 rounded-xl font-black shadow-xl hover:scale-105 active:scale-95 transition-all"
                        >
                            立刻导入首批数据
                        </button>
                    </div>
                </div>
            </div>

            {/* Simple Footer */}
            <footer className="py-12 border-t border-[#e9e9e8] text-center text-[#8e8e8e] text-xs">
                <p>© 2026 BivaStat-Miner 智能数据挖掘团队 · 软著证书号 V1.0.0-PRO-2026</p>
            </footer>
        </div>
    );
};

export default Home;
