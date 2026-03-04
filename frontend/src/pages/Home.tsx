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
        <div className="max-w-6xl mx-auto py-8 px-5 md:py-12 md:px-6">
            <div className="mb-10 md:mb-16 text-center md:text-left">
                <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-[#37352f] mb-4 md:mb-6 leading-tight">
                    双变量关联挖掘与非参数统计分析平台
                </h1>
                <p className="text-base sm:text-lg md:text-xl text-[#8e8e8e] max-w-3xl leading-relaxed mx-auto md:mx-0">
                    基于启发式方案深度挖掘变量间关联关系，让非专业统计人员也能通过简单的配置，获得专业、科学的成对变量关联洞察与统计检验支持。
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 md:gap-8 mb-10 md:mb-16">
                {features.map((f, i) => (
                    <div
                        key={i}
                        onClick={() => navigate(f.path)}
                        className="group notion-card p-5 sm:p-6 md:p-8 cursor-pointer flex gap-4 md:gap-6 items-start hover:bg-[#efefee]/30 transition-all border border-[#e9e9e8] h-full"
                    >
                        <div className={`w-12 h-12 md:w-14 md:h-14 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${f.color} group-hover:scale-105 transition-transform`}>
                            <f.icon className="w-6 h-6 md:w-7 md:h-7" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-extrabold text-lg md:text-xl mb-2 md:mb-3 flex items-center gap-2 text-[#37352f]">
                                {f.title}
                                <ArrowRight size={18} className="opacity-0 md:group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0 text-emerald-500 hidden sm:block" />
                            </h3>
                            <p className="text-[#8e8e8e] text-sm md:text-base leading-relaxed">{f.desc}</p>
                        </div>
                    </div>
                ))}
            </div>

            <div className="border-2 border-dashed border-[#e9e9e8] rounded-2xl p-8 sm:p-12 md:p-20 text-center bg-white shadow-sm hover:border-emerald-200 transition-colors">
                <div className="w-16 h-16 md:w-20 md:h-20 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6 md:mb-8 shadow-inner">
                    <Upload className="w-8 h-8 md:w-10 md:h-10" />
                </div>
                <h3 className="text-xl md:text-2xl font-bold mb-3 md:mb-4 text-[#37352f]">立即开启智能分析之旅</h3>
                <p className="text-base md:text-lg text-[#8e8e8e] mb-8 md:mb-10 max-w-md mx-auto leading-relaxed">导入您的数据集（CSV/Excel），让系统引擎自动为您探索变量间的深层联系。</p>
                <button
                    onClick={() => navigate('/data')}
                    className="notion-btn-primary px-8 py-3 md:px-12 md:py-4 text-base md:text-lg shadow-lg hover:shadow-xl transition-all w-full sm:w-auto"
                >
                    上传我的数据集
                </button>
            </div>
        </div>
    );
};

export default Home;
