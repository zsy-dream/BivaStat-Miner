import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Database, Settings2, LineChart, HelpCircle, User, LogOut } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface LayoutProps {
    children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
    const menuItems = [
        { label: '首页总览', path: '/', icon: LayoutDashboard },
        { label: '数据管理', path: '/data', icon: Database },
        { label: '算法配置', path: '/algorithm', icon: Settings2 },
        { label: '分析结果', path: '/analysis', icon: LineChart },
    ];

    return (
        <div className="flex h-screen bg-[#fbfbfa]">
            {/* Sidebar */}
            <aside className="w-[240px] border-r border-[#e9e9e8] flex flex-col pt-4">
                <div className="px-5 mb-8 flex items-center gap-2">
                    <div className="w-8 h-8 bg-primary-500 rounded-md flex items-center justify-center text-white font-bold">
                        B
                    </div>
                    <span className="font-bold text-sm text-[#37352f] truncate">
                        双变量挖掘平台 V1.0
                    </span>
                </div>

                <nav className="flex-1 px-3 space-y-1">
                    <div className="text-[11px] font-semibold text-[#8e8e8e] px-3 mb-2 uppercase tracking-wider">
                        主菜单
                    </div>
                    {menuItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            className={({ isActive }) =>
                                cn(
                                    "flex items-center gap-2.5 px-3 py-1 text-[14px] text-[#37352f]/90 rounded cursor-pointer transition-all duration-200 hover:bg-[#efefee]",
                                    isActive && "bg-[#efefee] font-semibold text-[#37352f]"
                                )
                            }
                        >
                            <item.icon size={18} strokeWidth={2.5} />
                            <span>{item.label}</span>
                        </NavLink>
                    ))}
                </nav>

                <div className="p-4 border-t border-[#e9e9e8]">
                    <div className="sidebar-item">
                        <HelpCircle size={18} />
                        <span className="text-[14px]">帮助文档</span>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
                <header className="h-[45px] border-b border-[#e9e9e8] bg-white/80 backdrop-blur-md flex items-center justify-between px-6 z-10">
                    <div className="flex items-center gap-2 text-xs text-[#8e8e8e]">
                        <span>工作空间</span>
                        <span>/</span>
                        <span className="text-[#37352f] font-medium">智能分析平台</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <button className="p-1 hover:bg-[#efefee] rounded-full transition-colors">
                            <User size={18} className="text-[#37352f]" />
                        </button>
                        <button className="p-1 hover:bg-[#efefee] rounded-full transition-colors">
                            <LogOut size={18} className="text-red-500" />
                        </button>
                    </div>
                </header>

                <main className="flex-1 overflow-y-auto p-10 bg-[#fbfbfa]">
                    {children}
                </main>
            </div>
        </div>
    );
};

export default Layout;
