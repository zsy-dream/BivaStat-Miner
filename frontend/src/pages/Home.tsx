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
        <div className="max-w-6xl mx-auto py-12 px-6">
            <div className="mb-16">
                <h1 className="text-5xl font-extrabold tracking-tight text-[#37352f] mb-6">
                    双变量关联挖掘与非参数统计分析平台
                </h1>
                <p className="text-xl text-[#8e8e8e] max-w-3xl leading-relaxed">
                    基于启发式方案深度挖掘变量间关联关系，让非专业统计人员也能通过简单的配置，获得专业、科学的成对变量关联洞察与统计检验支持。
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
                {features.map((f, i) => (
                    <div
                        key={i}
                        onClick={() => navigate(f.path)}
                        className="group notion-card p-8 cursor-pointer flex gap-6 items-start hover:bg-[#efefee]/30 transition-all border border-[#e9e9e8] h-full"
                    >
                        <div className={`w-14 h-14 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${f.color} group-hover:scale-105 transition-transform`}>
                            <f.icon size={28} />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-extrabold text-xl mb-3 flex items-center gap-2 text-[#37352f]">
                                {f.title}
                                <ArrowRight size={18} className="opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0 text-emerald-500" />
                            </h3>
                            <p className="text-[#8e8e8e] text-base leading-relaxed">{f.desc}</p>
                        </div>
                    </div>
                ))}
            </div>

            <div className="border-2 border-dashed border-[#e9e9e8] rounded-2xl p-20 text-center bg-white shadow-sm hover:border-emerald-200 transition-colors">
                <div className="w-20 h-20 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-8 shadow-inner">
                    <Upload size={40} />
                </div>
                <h3 className="text-2xl font-bold mb-4 text-[#37352f]">立即开启智能分析之旅</h3>
                <p className="text-lg text-[#8e8e8e] mb-10 max-w-md mx-auto leading-relaxed">导入您的数据集（CSV/Excel），让系统引擎自动为您探索变量间的深层联系。</p>
                <button
                    onClick={() => navigate('/data')}
                    className="notion-btn-primary px-12 py-4 text-lg shadow-lg hover:shadow-xl transition-all"
                >
                    上传我的数据集
                </button>
            </div>
        </div>
    );
};

export default Home;
