import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Database, Settings2, LineChart, HelpCircle, User, LogOut, Menu } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface LayoutProps {
    children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    const menuItems = [
        { label: '首页总览', path: '/', icon: LayoutDashboard },
        { label: '数据管理', path: '/data', icon: Database },
        { label: '算法配置', path: '/algorithm', icon: Settings2 },
        { label: '分析结果', path: '/analysis', icon: LineChart },
    ];

    return (
        <div className="flex h-screen bg-[#fbfbfa] overflow-hidden relative">
            {/* Mobile Sidebar Overlay */}
            {isMobileMenuOpen && (
                <div
                    className="fixed inset-0 bg-black/20 z-40 md:hidden transition-opacity"
                    onClick={() => setIsMobileMenuOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={cn(
                "fixed md:static inset-y-0 left-0 z-50 w-64 md:w-68 flex flex-col border-r border-[#e9e9e8] bg-[#fbfbfa] h-full transition-transform duration-300 ease-in-out md:transform-none shadow-2xl md:shadow-none",
                isMobileMenuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
            )}>
                <div className="p-6 flex items-center gap-3">
                    <div className="w-9 h-9 bg-emerald-500 rounded-md flex items-center justify-center text-white font-bold text-xl shadow-sm">
                        B
                    </div>
                    <div>
                        <h1 className="text-sm font-bold tracking-tight text-[#37352f]">双变量挖掘平台</h1>
                        <p className="text-[10px] text-emerald-600 font-bold opacity-80 uppercase tracking-tighter">Edition V1.0</p>
                    </div>
                </div>

                <nav className="flex-1 px-3 py-4 space-y-1.5 flex flex-col">
                    <div className="px-3 mb-3">
                        <span className="text-[11px] font-bold text-[#8e8e8e] uppercase tracking-widest opacity-60">
                            主菜单 (Menu)
                        </span>
                    </div>{menuItems.map((item) => (
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
                            <span className="text-sm font-semibold">{item.label}</span>
                        </NavLink>
                    ))}
                </nav>

                <div className="p-4 mt-auto border-t border-[#e9e9e8]/50">
                    <button className="flex items-center gap-3 px-3 py-2 w-full text-[#37352f]/70 hover:bg-[#efefee] rounded-md transition-all group">
                        <HelpCircle size={18} className="group-hover:text-emerald-500 transition-colors" />
                        <span className="text-sm font-medium">解析帮助文档</span>
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col overflow-hidden w-full max-w-full">
                <header className="h-[50px] md:h-[45px] border-b border-[#e9e9e8] bg-white/80 backdrop-blur-md flex items-center justify-between px-4 md:px-6 z-10 shrink-0">
                    <div className="flex items-center gap-3">
                        <button
                            className="p-1.5 hover:bg-[#efefee] rounded-md md:hidden transition-colors"
                            onClick={() => setIsMobileMenuOpen(true)}
                        >
                            <Menu size={20} className="text-[#37352f]" />
                        </button>
                        <div className="flex items-center gap-2 text-xs text-[#8e8e8e] hidden sm:flex">
                            <span>工作空间</span>
                            <span>/</span>
                            <span className="text-[#37352f] font-medium">智能分析平台</span>
                        </div>
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

                <main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-10 bg-[#fbfbfa] w-full">
                    {children}
                </main>
            </div>
        </div>
    );
};

export default Layout;
