import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Database, Settings2, LineChart, FileText, ArrowRight } from 'lucide-react';

const Home: React.FC = () => {
    const navigate = useNavigate();

    const features = [
        {
            title: '数据管理',
            desc: '支持 CSV、Excel、JSON 等多格式导入，提供质量评估、清洗、填充等全流程预处理。',
            icon: Database,
            color: 'bg-emerald-50 text-emerald-600',
            path: '/data'
        },
        {
            title: '算法配置',
            desc: '基于启发式策略配置支持度、置信度及提升度，支持双变量关联深度挖掘。',
            icon: Settings2,
            color: 'bg-blue-50 text-blue-600',
            path: '/algorithm'
        },
        {
            title: '结果分析',
            desc: '呈现挖掘关联规则、真实 P 值验证，以及 Mann-Whitney、Chi-Square 等统计结论。',
            icon: LineChart,
            color: 'bg-indigo-50 text-indigo-600',
            path: '/analysis'
        },
        {
            title: '报告导出',
            desc: '一键生成企业级分析报告，内置多维度可视化图表，支持多格式导出交付。',
            icon: FileText,
            color: 'bg-amber-50 text-amber-600',
            path: '/report'
        },
    ];

    return (
        <div className="max-w-5xl mx-auto mt-6">
            <div className="mb-14">
                <h1 className="text-4xl font-bold mb-4 tracking-tight">双变量关联挖掘与非参数统计分析平台</h1>
                <p className="text-[#8e8e8e] text-lg max-w-2xl leading-relaxed">
                    基于启发式算法，让非专业统计人员也能通过简单的配置，获得专业、科学的成对变量关联洞察与统计检验支持。
                </p>
            </div>

            <div className="grid grid-cols-2 gap-6 mb-12">
                {features.map((f, i) => (
                    <div
                        key={i}
                        onClick={() => navigate(f.path)}
                        className="group notion-card p-6 cursor-pointer flex gap-5 items-start"
                    >
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${f.color}`}>
                            <f.icon size={24} />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-bold text-lg mb-2 flex items-center gap-2">
                                {f.title}
                                <ArrowRight size={16} className="opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0" />
                            </h3>
                            <p className="text-[#8e8e8e] text-sm leading-relaxed">{f.desc}</p>
                        </div>
                    </div>
                ))}
            </div>

            <div className="border border-dashed border-[#e9e9e8] rounded-xl p-12 text-center bg-white/50">
                <div className="w-16 h-16 bg-blue-50 text-[#2383e2] rounded-full flex items-center justify-center mx-auto mb-6">
                    <Upload size={32} />
                </div>
                <h3 className="text-xl font-bold mb-3">立即开始分析</h3>
                <p className="text-[#8e8e8e] mb-8">拖入数据集或点击此处开始</p>
                <button
                    onClick={() => navigate('/data')}
                    className="notion-btn-primary px-8"
                >
                    上传我的数据集
                </button>
            </div>
        </div>
    );
};

export default Home;
