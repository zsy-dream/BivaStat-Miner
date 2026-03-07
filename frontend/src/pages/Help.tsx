import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    ArrowRight, BarChart3, BrainCircuit, Calculator, ChevronDown, ChevronRight, Cpu, Database, FileJson,
    FileText, MousePointer2, Network, Scale, Settings2, ShieldCheck, Sparkles, Terminal, Upload
} from 'lucide-react';
import { AnimatePresence, motion, useScroll, useSpring } from 'framer-motion';
import { cn } from '../utils/cn';
import { Button } from '../components/ui/button';

type HelpSection = {
    id: string;
    title: string;
    subtitle: string;
    summary: string;
    icon: React.ComponentType<{ size?: number; className?: string }>;
    color: string;
    bg: string;
    isAI?: boolean;
    highlights: string[];
    content: React.ReactNode;
};

type FaqItem = {
    id: string;
    question: string;
    answer: string;
};

const quickStartSteps = [
    {
        step: '01',
        title: '导入数据集',
        icon: Database,
        desc: '上传 CSV / Excel 后，系统会自动识别数值列、分类型列，并生成数据画像。'
    },
    {
        step: '02',
        title: '设置挖掘参数',
        icon: Cpu,
        desc: '配置支持度、置信度、提升度和显著性阈值，决定结果的严格程度。'
    },
    {
        step: '03',
        title: '查看分析产出',
        icon: FileJson,
        desc: '获得规则列表、统计检验结论、可视化图表以及可直接引用的分析摘要。'
    }
];

const operationGuideCards = [
    {
        id: 'guide-data',
        step: '01',
        title: '数据导入',
        page: '数据管理页',
        summary: '先完成文件上传和字段检查，确保后续挖掘建立在可用数据之上。',
        icon: Upload,
        accent: 'from-sky-50 to-blue-50',
        border: 'border-sky-100',
        dot: 'bg-sky-500',
        tips: ['进入数据管理页上传 CSV / Excel', '先看数据画像，确认字段类型', '高基数 ID 字段一般不适合直接挖掘']
    },
    {
        id: 'guide-params',
        step: '02',
        title: '参数配置',
        page: '算法配置页',
        summary: '支持度、置信度和提升度决定规则筛选强度，建议先用推荐参数起步。',
        icon: Settings2,
        accent: 'from-violet-50 to-indigo-50',
        border: 'border-violet-100',
        dot: 'bg-violet-500',
        tips: ['支持度越低，规则越多但噪声也更多', '置信度越高，规则更严格', '首次可先用系统推荐参数']
    },
    {
        id: 'guide-result',
        step: '03',
        title: '结果解读',
        page: '分析结果页',
        summary: '先看规则强度与显著性，再看适配度、回退轨迹和联动关系。',
        icon: BarChart3,
        accent: 'from-amber-50 to-orange-50',
        border: 'border-amber-100',
        dot: 'bg-amber-500',
        tips: ['优先看提升度高且显著的规则', '无规则时先看适配度和回退轨迹', '结合可视化页联动查看字段关系']
    },
    {
        id: 'guide-report',
        step: '04',
        title: '报告导出',
        page: '报告生成页',
        summary: '整理规则、图表和摘要后再导出，方便展示、留档和复核。',
        icon: FileText,
        accent: 'from-emerald-50 to-teal-50',
        border: 'border-emerald-100',
        dot: 'bg-emerald-500',
        tips: ['分析完成后进入报告生成', '可结合 AI 解读整理摘要', '导出前先确认关键规则和图表已筛选']
    }
];

const faqItems: FaqItem[] = [
    {
        id: 'faq-no-rules',
        question: '为什么没有挖掘出规则？',
        answer: '最常见的原因是参数过严、字段重复模式不足，或者数据里存在高基数列占比过高。先降低最小支持度和最小置信度，再检查是否有大量近似唯一值的字段。'
    },
    {
        id: 'faq-support-confidence',
        question: '支持度和置信度应该怎么调？',
        answer: '一般先调支持度，再调置信度。支持度决定规则能不能进候选池，置信度决定规则稳不稳。数据量小或模式稀疏时，支持度可以先适当降低；如果结果太多，再提高置信度做筛选。'
    },
    {
        id: 'faq-empty-result-page',
        question: '为什么结果页会显示“无规则”或看起来没有内容？',
        answer: '这通常不是页面坏了，而是当前任务没有产出可展示规则，或者结果处于回退策略后的空输出状态。先看结果页中的适配度、告警信息和策略尝试记录，再决定是否回到参数页重试。'
    },
    {
        id: 'faq-what-to-check-first',
        question: '第一次跑分析时，最先应该检查什么？',
        answer: '先看数据画像是否合理：字段类型是否正确、缺失值是否过多、是否存在 ID 类字段。然后再看推荐参数和候选字段数量，这两项通常决定第一次分析能否快速得到结果。'
    }
];

const ruleMetrics = [
    {
        label: '支持度',
        formula: 'P(A, B)',
        desc: '表示 A 和 B 同时出现的频率，用于过滤过于稀疏、难以稳定复现的组合。'
    },
    {
        label: '置信度',
        formula: 'P(B | A)',
        desc: '表示在 A 已发生时 B 也发生的概率，是判断规则可靠性的核心指标。'
    },
    {
        label: '提升度',
        formula: 'Conf(A→B) / P(B)',
        desc: '用于判断这条规则是否真的优于随机共现。大于 1 越多，关联越值得关注。'
    }
];

const nonparametricTests = [
    {
        title: 'Mann-Whitney U',
        desc: '用于比较两组独立样本的分布差异，适合替代对正态性要求更高的参数检验。'
    },
    {
        title: 'Chi-Square / 卡方检验',
        desc: '判断分类变量之间是否独立，常用于验证规则提升度是否具备显著性支持。'
    },
    {
        title: 'Kruskal-Wallis',
        desc: '在三组及以上样本之间比较分布差异，适合多类别分组分析。'
    },
    {
        title: 'Bootstrap 重采样',
        desc: '通过反复抽样估计规则稳定性，为 P 值和置信区间提供更稳健的参考。'
    }
];

const Help: React.FC = () => {
    const [activeSection, setActiveSection] = useState('quick-start');
    const [openFaqId, setOpenFaqId] = useState('faq-no-rules');
    const navigate = useNavigate();
    const { scrollYProgress } = useScroll();
    const scaleX = useSpring(scrollYProgress, {
        stiffness: 110,
        damping: 28,
        restDelta: 0.001
    });

    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        setActiveSection(entry.target.id);
                    }
                });
            },
            {
                root: null,
                rootMargin: '-18% 0px -64% 0px',
                threshold: 0
            }
        );

        const targets = document.querySelectorAll('section[data-help-section="true"]');
        targets.forEach((section) => observer.observe(section));

        return () => observer.disconnect();
    }, []);

    const sections: HelpSection[] = [
        {
            id: 'quick-start',
            title: '快速上手',
            subtitle: 'Quick Start',
            summary: '如果你是第一次使用，先看这一节。它会告诉你最短路径：先导入数据，再配置参数，最后查看规则、图表和报告。',
            icon: MousePointer2,
            color: 'text-amber-600',
            bg: 'bg-amber-50',
            highlights: ['适合首次使用', '3 步完成流程', '可直接开始操作'],
            content: (
                <div className="space-y-8">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {quickStartSteps.map((item) => (
                            <div
                                key={item.step}
                                className="rounded-2xl border border-[#e9e9e8] bg-[#fbfbfa] p-5 transition-all hover:-translate-y-0.5 hover:border-[#cfd8e3] hover:shadow-lg"
                            >
                                <div className="mb-4 flex items-center justify-between">
                                    <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-white border border-[#e9e9e8] text-[#2383e2] shadow-sm">
                                        <item.icon size={18} />
                                    </div>
                                    <span className="text-[11px] font-black tracking-[0.18em] text-[#b4b4b3]">{item.step}</span>
                                </div>
                                <h4 className="text-sm font-black text-[#37352f]">{item.title}</h4>
                                <p className="mt-2 text-xs leading-relaxed text-[#787774]">{item.desc}</p>
                            </div>
                        ))}
                    </div>

                    <div className="rounded-2xl border border-blue-100 bg-blue-50/60 p-5">
                        <div className="flex items-start gap-3">
                            <div className="mt-0.5 rounded-xl bg-white p-2 text-[#2383e2] border border-blue-100">
                                <Sparkles size={16} />
                            </div>
                            <div>
                                <h4 className="text-sm font-black text-[#37352f]">建议的阅读顺序</h4>
                                <p className="mt-2 text-sm leading-relaxed text-[#5f5e58]">
                                    先了解这里的整体流程，再看“关联挖掘”和“非参数统计检验”两节。这样你在调参数和解读结果时会更有把握。
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )
        },
        {
            id: 'operation-guide',
            title: '图文操作指南',
            subtitle: 'Operation Guide',
            summary: '如果你更习惯按照页面步骤来学，这一节更适合你。每张卡片对应一个实际操作阶段，可以直接对照系统页面使用。',
            icon: FileJson,
            color: 'text-sky-600',
            bg: 'bg-sky-50',
            highlights: ['按页面流程整理', '适合演示讲解', '覆盖四个关键步骤'],
            content: (
                <div className="space-y-6">
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        {operationGuideCards.map((card) => (
                            <div
                                key={card.id}
                                className={cn(
                                    'relative overflow-hidden rounded-[28px] border p-6 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg',
                                    card.border,
                                    `bg-gradient-to-br ${card.accent}`
                                )}
                            >
                                <div className="absolute inset-x-0 top-0 h-1 bg-white/60" />
                                <div className="mb-5 flex items-start justify-between gap-4">
                                    <div className="flex items-start gap-4">
                                        <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-white/80 bg-white/85 text-[#37352f] shadow-sm">
                                            <card.icon size={21} />
                                        </div>
                                        <div>
                                            <div className="text-[10px] font-black uppercase tracking-[0.2em] text-[#b4b4b3]">
                                                {card.page}
                                            </div>
                                            <h4 className="mt-2 text-[28px] leading-none font-black tracking-[-0.05em] text-[#37352f]">
                                                {card.title}
                                            </h4>
                                        </div>
                                    </div>
                                    <span className="inline-flex h-8 min-w-8 items-center justify-center rounded-xl border border-white/70 bg-white/80 px-2 text-[11px] font-black tracking-[0.18em] text-[#8f8f8b] shadow-sm">
                                        {card.step}
                                    </span>
                                </div>
                                <p className="text-[13px] font-medium leading-6 text-[#6a6963]">
                                    {card.summary}
                                </p>
                                <div className="my-5 h-px bg-black/5" />
                                <div className="space-y-3">
                                    {card.tips.map((tip) => (
                                        <div key={tip} className="flex items-start gap-3 text-sm leading-6 text-[#5f5e58]">
                                            <span className={cn(
                                                'mt-2 inline-flex h-2 w-2 shrink-0 rounded-full shadow-[0_0_0_4px_rgba(255,255,255,0.65)]',
                                                card.dot
                                            )} />
                                            <span className="font-medium">{tip}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )
        },
        {
            id: 'ai-reasoning',
            title: 'AI 解读能力',
            subtitle: 'AI Reasoning',
            summary: 'AI 模块不是替代统计检验，而是在统计结果之上提供结构化摘要、业务化解释和可读性更高的结论整理。',
            icon: BrainCircuit,
            color: 'text-purple-600',
            bg: 'bg-purple-50',
            isAI: true,
            highlights: ['辅助解读规则', '自动生成摘要', '保留统计依据'],
            content: (
                <div className="space-y-6">
                    <div className="rounded-3xl border border-purple-100 bg-gradient-to-br from-purple-50 to-indigo-50 p-6">
                        <div className="mb-4 inline-flex items-center rounded-full bg-purple-600 px-3 py-1 text-[10px] font-black tracking-[0.16em] text-white">
                            DEEPSEEK-V3.2
                        </div>
                        <p className="text-sm leading-relaxed text-[#37352f]">
                            系统会基于规则强度、显著性结果和上下文信息，对结果做进一步解释：哪些关系值得关注、哪些只是弱信号、哪些更适合作为管理建议或后续验证线索。
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="rounded-2xl border border-[#e9e9e8] bg-white p-5 shadow-sm">
                            <div className="mb-3 flex items-center gap-2">
                                <Sparkles size={16} className="text-purple-500" />
                                <h4 className="text-sm font-black text-[#37352f]">结构化解读</h4>
                            </div>
                            <p className="text-xs leading-relaxed text-[#787774]">
                                把支持度、置信度、提升度和显著性信息组织成“结论—依据—建议”的表达方式，降低阅读门槛。
                            </p>
                        </div>
                        <div className="rounded-2xl border border-[#e9e9e8] bg-white p-5 shadow-sm">
                            <div className="mb-3 flex items-center gap-2">
                                <Terminal size={16} className="text-blue-500" />
                                <h4 className="text-sm font-black text-[#37352f]">面向报告输出</h4>
                            </div>
                            <p className="text-xs leading-relaxed text-[#787774]">
                                便于把分析结果整理成执行摘要、汇报材料或项目说明，但最终仍应结合统计结论一起使用。
                            </p>
                        </div>
                    </div>
                </div>
            )
        },
        {
            id: 'bivariate',
            title: '关联挖掘原理',
            subtitle: 'Association Mining',
            summary: '平台使用 Apriori 系列思路来筛选高价值规则。你真正需要关注的是：这条规则出现得多不多、稳定不稳定、是不是显著高于随机共现。',
            icon: Calculator,
            color: 'text-blue-600',
            bg: 'bg-blue-50',
            highlights: ['关注三大指标', '区分强弱规则', '避免误判随机共现'],
            content: (
                <div className="space-y-6">
                    <div className="grid grid-cols-1 gap-4">
                        {ruleMetrics.map((metric) => (
                            <div
                                key={metric.label}
                                className="rounded-2xl border border-[#e9e9e8] bg-white p-5 transition-all hover:border-blue-200 hover:shadow-lg"
                            >
                                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                                    <div>
                                        <h4 className="text-sm font-black text-[#37352f]">{metric.label}</h4>
                                        <p className="mt-2 text-xs leading-relaxed text-[#787774]">{metric.desc}</p>
                                    </div>
                                    <div className="inline-flex items-center rounded-xl border border-blue-100 bg-blue-50 px-3 py-2 font-mono text-[11px] font-bold text-blue-700">
                                        {metric.formula}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="rounded-2xl border border-[#e9e9e8] bg-[#fbfbfa] p-5">
                        <h4 className="text-sm font-black text-[#37352f]">实际理解方式</h4>
                        <p className="mt-2 text-sm leading-relaxed text-[#5f5e58]">
                            一条“好规则”通常不是某一个指标高就够了，而是要同时满足：支持度不过低、置信度足够稳定、提升度明显大于 1。平台会帮助你把这些条件一起筛出来。
                        </p>
                    </div>
                </div>
            )
        },
        {
            id: 'nonparametric',
            title: '非参数统计检验',
            subtitle: 'Nonparametric Tests',
            summary: '统计检验的作用是确认规则是否只是“看起来有关”，还是在统计上也站得住脚。当前页面主要帮助你理解为什么系统会做这一步。',
            icon: ShieldCheck,
            color: 'text-emerald-600',
            bg: 'bg-emerald-50',
            highlights: ['验证规则可靠性', '适合非正态数据', '降低误报风险'],
            content: (
                <div className="space-y-6">
                    <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 p-5">
                        <div className="flex items-start gap-3">
                            <div className="mt-0.5 rounded-xl bg-white p-2 text-emerald-600 border border-emerald-100">
                                <Scale size={16} />
                            </div>
                            <p className="text-sm leading-relaxed text-emerald-900">
                                当数据分布不理想、样本量不大，或者变量之间不满足参数检验前提时，非参数方法能提供更稳妥的统计判断。
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {nonparametricTests.map((test) => (
                            <div
                                key={test.title}
                                className="rounded-2xl border border-[#e9e9e8] bg-white p-5 transition-all hover:border-emerald-200 hover:shadow-lg"
                            >
                                <h4 className="text-sm font-black text-[#37352f]">{test.title}</h4>
                                <p className="mt-2 text-xs leading-relaxed text-[#787774]">{test.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )
        },
        {
            id: 'faq',
            title: '常见问题 FAQ',
            subtitle: 'Questions & Answers',
            summary: '这里收集的是最容易卡住新用户的几个问题。你可以先在这里排查，再决定回到数据页、参数页还是结果页继续处理。',
            icon: Sparkles,
            color: 'text-rose-600',
            bg: 'bg-rose-50',
            highlights: ['新手常见误区', '覆盖空规则问题', '参数调整建议'],
            content: (
                <div className="space-y-3">
                    {faqItems.map((faq) => {
                        const isOpen = openFaqId === faq.id;
                        return (
                            <motion.div
                                key={faq.id}
                                layout
                                transition={{ type: 'spring', stiffness: 260, damping: 26 }}
                                className={cn(
                                    'overflow-hidden rounded-2xl border text-left transition-all',
                                    isOpen
                                        ? 'border-rose-200 bg-rose-50/60 shadow-sm'
                                        : 'border-[#e9e9e8] bg-white hover:border-rose-100 hover:bg-[#fcfcfc]'
                                )}
                            >
                                <button
                                key={faq.id}
                                type="button"
                                onClick={() => setOpenFaqId((prev) => prev === faq.id ? '' : faq.id)}
                                className="w-full text-left"
                            >
                                <div className="flex items-center justify-between gap-4 px-5 py-4">
                                    <div className="pr-2 text-sm font-black text-[#37352f]">{faq.question}</div>
                                    <div className={cn(
                                        'flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border transition-colors duration-300',
                                        isOpen
                                            ? 'border-rose-200 bg-white text-rose-600'
                                            : 'border-[#e9e9e8] bg-[#fbfbfa] text-[#787774]'
                                    )}>
                                        <ChevronDown size={16} className={cn('transition-transform duration-300 ease-out', isOpen && 'rotate-180')} />
                                    </div>
                                </div>
                                </button>
                                <AnimatePresence initial={false}>
                                    {isOpen && (
                                        <motion.div
                                            key={`${faq.id}-content`}
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: 'auto', opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            transition={{
                                                height: { duration: 0.28, ease: [0.22, 1, 0.36, 1] },
                                                opacity: { duration: 0.2, ease: 'easeOut' }
                                            }}
                                            className="overflow-hidden"
                                        >
                                            <motion.div
                                                initial={{ y: -6, opacity: 0 }}
                                                animate={{ y: 0, opacity: 1 }}
                                                exit={{ y: -4, opacity: 0 }}
                                                transition={{ duration: 0.22, ease: 'easeOut' }}
                                                className="px-5 pb-5 text-sm leading-7 text-[#5f5e58]"
                                            >
                                                {faq.answer}
                                            </motion.div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </motion.div>
                        );
                    })}
                </div>
            )
        }
    ];

    const jumpToSection = (id: string) => {
        const element = document.getElementById(id);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    const getSectionNumber = (index: number) => String(index + 1).padStart(2, '0');

    return (
        <div className="relative pb-20">
            <motion.div
                className="fixed left-0 right-0 top-0 z-50 h-1 origin-[0%] bg-gradient-to-r from-[#2383e2] via-[#6d5efc] to-[#8b5cf6]"
                style={{ scaleX }}
            />

            <div className="pointer-events-none fixed right-4 top-1/2 z-20 hidden -translate-y-1/2 2xl:flex">
                <div className="pointer-events-auto rounded-full border border-[#e9e9e8] bg-white/80 p-2 shadow-lg backdrop-blur-md">
                    <div className="mb-2 px-1 text-center text-[9px] font-black uppercase tracking-[0.18em] text-[#b4b4b3]">
                        TOC
                    </div>
                    <div className="space-y-2">
                        {sections.map((section, index) => {
                            const active = activeSection === section.id;
                            return (
                                <button
                                    key={`floating-${section.id}`}
                                    type="button"
                                    onClick={() => jumpToSection(section.id)}
                                    className={cn(
                                        'group relative flex w-full items-center justify-center rounded-2xl transition-all',
                                        active ? 'bg-[#111827] text-white shadow-md' : 'text-[#5f5e58] hover:bg-[#f6f7f9]'
                                    )}
                                    title={section.title}
                                >
                                    <span className={cn(
                                        'inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border text-[11px] font-black tracking-[0.12em]',
                                        active
                                            ? 'border-white/10 bg-white/10 text-white'
                                            : 'border-[#e9e9e8] bg-white text-[#37352f]'
                                    )}>
                                        {getSectionNumber(index)}
                                    </span>
                                    <span className={cn(
                                        'pointer-events-none absolute right-[calc(100%+10px)] top-1/2 hidden -translate-y-1/2 whitespace-nowrap rounded-xl border px-3 py-2 text-xs font-semibold shadow-lg transition-all 2xl:block',
                                        active
                                            ? 'border-[#111827] bg-[#111827] text-white opacity-100'
                                            : 'border-[#e9e9e8] bg-white text-[#37352f] opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:-translate-x-0'
                                    )}>
                                        {section.title}
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                </div>
            </div>

            <div className="mx-auto max-w-7xl space-y-8">
                <section className="space-y-4">
                    <motion.div
                        initial={{ opacity: 0, y: 18 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="rounded-[28px] border border-[#e9e9e8] bg-white p-7 shadow-sm md:p-8"
                    >
                        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
                            <div className="flex min-w-0 flex-1 items-start gap-5">
                                <div className="flex h-18 w-18 shrink-0 items-center justify-center rounded-3xl border border-[#e9e9e8] bg-[#f8fbff] p-5 text-[#2383e2] shadow-sm">
                                    <Network size={34} />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <div className="mb-3 flex flex-wrap items-center gap-2">
                                        <span className="rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-[10px] font-black tracking-[0.16em] text-blue-700">
                                            HELP CENTER
                                        </span>
                                        <span className="rounded-full border border-[#e9e9e8] bg-[#fbfbfa] px-3 py-1 text-[10px] font-bold text-[#787774]">
                                            V1.0 使用说明
                                        </span>
                                    </div>
                                    <h1 className="text-4xl font-black tracking-tight text-[#37352f] md:text-5xl">
                                        平台帮助文档
                                    </h1>
                                    <p className="mt-4 max-w-3xl text-sm leading-7 text-[#5f5e58] md:text-[15px]">
                                        面向实际操作的使用指南。建议先看快速上手和图文操作指南，再按需阅读 AI 解读、关联挖掘和统计检验部分。
                                    </p>
                                </div>
                            </div>
                            <div className="flex flex-wrap gap-3 md:justify-end">
                                <Button onClick={() => navigate('/algorithm')} size="lg">
                                    前往算法配置
                                    <ArrowRight size={16} />
                                </Button>
                                <Button variant="outline" size="lg" onClick={() => navigate('/data')}>
                                    先去导入数据
                                </Button>
                            </div>
                        </div>
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, y: 18 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.08 }}
                        className="grid grid-cols-1 gap-4 md:grid-cols-3"
                    >
                        {[
                            {
                                label: '建议入口',
                                value: '快速上手',
                                hint: '首次使用建议先阅读这里',
                                icon: MousePointer2,
                                iconWrap: 'bg-amber-50 text-amber-600 border-amber-100'
                            },
                            {
                                label: '核心能力',
                                value: '规则 + 检验',
                                hint: '挖掘结果与统计验证联动',
                                icon: ShieldCheck,
                                iconWrap: 'bg-blue-50 text-blue-600 border-blue-100'
                            },
                            {
                                label: '输出形式',
                                value: '图表 / 报告',
                                hint: '支持后续汇报、留档和复核',
                                icon: FileText,
                                iconWrap: 'bg-emerald-50 text-emerald-600 border-emerald-100'
                            }
                        ].map((item) => (
                            <div
                                key={item.label}
                                className="rounded-3xl border border-[#e9e9e8] bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg"
                            >
                                <div className="flex items-start justify-between gap-4">
                                    <div>
                                        <div className="text-[10px] font-black uppercase tracking-[0.2em] text-[#b4b4b3]">{item.label}</div>
                                        <div className="mt-3 text-[34px] leading-none font-black tracking-[-0.04em] text-[#37352f]">
                                            {item.value}
                                        </div>
                                    </div>
                                    <div className={cn(
                                        'inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border shadow-sm',
                                        item.iconWrap
                                    )}>
                                        <item.icon size={20} />
                                    </div>
                                </div>
                                <div className="mt-4 text-[13px] font-medium leading-6 text-[#787774]">{item.hint}</div>
                            </div>
                        ))}
                    </motion.div>
                </section>

                <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
                    <aside className="space-y-5 lg:col-span-3 lg:sticky lg:top-6 h-fit">
                        <div className="rounded-3xl border border-[#e9e9e8] bg-white p-5 shadow-sm">
                            <div className="mb-4 text-[11px] font-black uppercase tracking-[0.18em] text-[#787774]">
                                文档导航
                            </div>
                            <nav className="space-y-2">
                                {sections.map((section, index) => (
                                    <button
                                        key={section.id}
                                        type="button"
                                        onClick={() => jumpToSection(section.id)}
                                        className={cn(
                                            'group flex w-full items-center justify-between rounded-[20px] border px-4 py-3 text-left transition-all',
                                            activeSection === section.id
                                                ? 'border-[#111827] bg-gradient-to-r from-[#2d2b28] to-[#16181d] text-white shadow-[0_12px_24px_rgba(17,24,39,0.18)]'
                                                : 'border-transparent bg-[#fbfbfa] text-[#5f5e58] hover:border-[#eceeed] hover:bg-[#f7f8fa] hover:text-[#37352f]'
                                        )}
                                    >
                                        <div className="flex min-w-0 items-center gap-3">
                                            <span className={cn(
                                                'inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border text-[11px] font-black tracking-[0.12em]',
                                                activeSection === section.id
                                                    ? 'border-white/10 bg-white/10 text-white'
                                                    : 'border-[#e9e9e8] bg-white text-[#37352f]'
                                            )}>
                                                {getSectionNumber(index)}
                                            </span>
                                            <div className={cn(
                                                'flex h-8 w-8 shrink-0 items-center justify-center rounded-xl',
                                                activeSection === section.id ? 'bg-white/15' : section.bg
                                            )}>
                                                <section.icon
                                                    size={15}
                                                    className={activeSection === section.id ? 'text-white' : section.color}
                                                />
                                            </div>
                                            <div className="min-w-0 leading-none">
                                                <div className="truncate text-[15px] font-black tracking-[-0.02em]">{section.title}</div>
                                                <div className={cn(
                                                    'mt-1 truncate text-[9px] uppercase tracking-[0.16em]',
                                                    activeSection === section.id ? 'text-white/45' : 'text-[#c4c3bf]'
                                                )}>
                                                    {section.subtitle}
                                                </div>
                                            </div>
                                        </div>
                                        <ChevronRight
                                            size={14}
                                            className={cn(
                                                'shrink-0 transition-all duration-200',
                                                activeSection === section.id ? 'translate-x-0 opacity-100' : '-translate-x-1 opacity-25 group-hover:opacity-60'
                                            )}
                                        />
                                    </button>
                                ))}
                            </nav>
                        </div>

                        <div className="rounded-3xl bg-[#37352f] p-5 text-white shadow-xl">
                            <Sparkles size={16} className="mb-3 text-blue-300" />
                            <h3 className="text-sm font-black">阅读建议</h3>
                            <p className="mt-2 text-xs leading-relaxed text-white/75">
                                如果你是来解决“为什么没有规则”或“参数怎么调”，重点看“快速上手”和“关联挖掘原理”。
                            </p>
                        </div>
                    </aside>

                    <main className="space-y-8 lg:col-span-9">
                        {sections.map((section, index) => (
                            <motion.section
                                key={section.id}
                                id={section.id}
                                data-help-section="true"
                                initial={{ opacity: 0, y: 24 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true, margin: '-80px' }}
                                transition={{ duration: 0.45, delay: index * 0.04 }}
                                className="scroll-mt-24"
                            >
                                <div className="rounded-[30px] border border-[#e9e9e8] bg-white p-7 shadow-sm md:p-8">
                                    <div className="mb-6 flex flex-col gap-4 border-b border-[#f1f1f0] pb-6 md:flex-row md:items-start md:justify-between">
                                        <div className="flex items-start gap-4">
                                            <div className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-[#e9e9e8] bg-white text-[13px] font-black tracking-[0.16em] text-[#37352f] shadow-sm">
                                                {getSectionNumber(index)}
                                            </div>
                                            <div className={cn('flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl', section.bg)}>
                                                <section.icon size={22} className={section.color} />
                                            </div>
                                            <div>
                                                <div className="flex flex-wrap items-center gap-2">
                                                    <span className="text-[10px] font-black uppercase tracking-[0.18em] text-[#b4b4b3]">
                                                        Chapter {getSectionNumber(index)}
                                                    </span>
                                                    <span className="rounded-full border border-[#e9e9e8] bg-[#fbfbfa] px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] text-[#787774]">
                                                        {section.subtitle}
                                                    </span>
                                                </div>
                                                <h2 className="mt-1 text-3xl font-black tracking-tight text-[#37352f]">
                                                    {section.title}
                                                </h2>
                                                <p className="mt-3 max-w-3xl text-sm leading-7 text-[#5f5e58]">
                                                    {section.summary}
                                                </p>
                                            </div>
                                        </div>

                                        {section.isAI && (
                                            <div className="inline-flex items-center gap-2 self-start rounded-full border border-purple-100 bg-purple-50 px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-purple-700">
                                                <div className="h-1.5 w-1.5 rounded-full bg-purple-500" />
                                                AI 已集成
                                            </div>
                                        )}
                                    </div>

                                    <div className="mb-6 flex flex-wrap gap-2">
                                        {section.highlights.map((item) => (
                                            <span
                                                key={item}
                                                className="inline-flex items-center rounded-full border border-[#e9e9e8] bg-[#fbfbfa] px-3 py-1 text-[11px] font-semibold text-[#5f5e58]"
                                            >
                                                {item}
                                            </span>
                                        ))}
                                    </div>

                                    <div className="text-sm text-[#787774]">
                                        {section.content}
                                    </div>
                                </div>
                            </motion.section>
                        ))}

                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            className="rounded-[30px] border border-[#e9e9e8] bg-gradient-to-r from-[#111827] to-[#2b2b2b] p-8 text-white shadow-xl"
                        >
                            <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
                                <div className="flex items-start gap-4">
                                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white/10 border border-white/10">
                                        <ShieldCheck size={26} className="text-white" />
                                    </div>
                                    <div className="max-w-xl">
                                        <h3 className="text-2xl font-black tracking-tight">准备开始正式分析？</h3>
                                        <p className="mt-2 text-sm leading-7 text-white/75">
                                            如果你已经了解基本流程，下一步建议直接去导入数据或进入算法配置页，边操作边看帮助文档会更高效。
                                        </p>
                                    </div>
                                </div>
                                <div className="flex flex-wrap gap-3">
                                    <Button variant="secondary" size="lg" onClick={() => navigate('/data')}>
                                        前往数据管理
                                    </Button>
                                    <Button size="lg" onClick={() => navigate('/algorithm')}>
                                        前往算法配置
                                        <ArrowRight size={16} />
                                    </Button>
                                </div>
                            </div>
                        </motion.div>
                    </main>
                </div>
            </div>
        </div>
    );
};

export default Help;
