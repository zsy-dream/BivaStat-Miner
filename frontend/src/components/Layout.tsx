import React, { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Database, Settings2, LineChart, HelpCircle, User, LogOut, Menu, BarChart3, Presentation, History, ChevronRight, Info } from 'lucide-react';
import { useToast } from './Toast';
import { cn } from '../utils/cn';
import logoImg from '../assets/banner.png';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem,
    DropdownMenuSeparator, DropdownMenuTrigger
} from './ui/dropdown-menu';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
} from './ui/dialog';
import { Button } from './ui/button';

interface LayoutProps {
    children: React.ReactNode;
}

const menuItems = [
    { label: '首页', path: '/', icon: LayoutDashboard },
    { label: '数据管理', path: '/data', icon: Database },
    { label: '算法配置', path: '/algorithm', icon: Settings2 },
    { label: '分析结果', path: '/analysis_result', icon: LineChart },
    { label: '历史记录', path: '/history', icon: History },
    { label: '可视化', path: '/visualization', icon: BarChart3 },
    { label: '报告生成', path: '/report', icon: Presentation },
];

const Layout: React.FC<LayoutProps> = ({ children }) => {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [showAboutModal, setShowAboutModal] = useState(false);
    const location = useLocation();
    const navigate = useNavigate();
    const { toast, confirm } = useToast();

    // 根据路径获取当前页面名称
    const getCurrentPageLabel = () => {
        const basePath = '/' + location.pathname.split('/')[1];
        const item = menuItems.find(m => m.path === basePath) || menuItems.find(m => m.path === location.pathname);
        if (item) return item.label;
        if (location.pathname === '/help') return '帮助文档';
        return '工作台';
    };

    return (
        <div className="flex h-screen bg-[#fbfbfa] overflow-hidden relative font-sans">
            {/* Mobile Sidebar Overlay */}
            {isMobileMenuOpen && (
                <div
                    className="fixed inset-0 bg-black/20 z-40 md:hidden transition-opacity"
                    onClick={() => setIsMobileMenuOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={cn(
                "fixed md:static inset-y-0 left-0 z-50 w-56 md:w-[232px] flex flex-col border-r border-[#e9e9e8] bg-[#fbfbfa] h-full transition-transform duration-300 ease-in-out md:transform-none shadow-2xl md:shadow-none",
                isMobileMenuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
            )}>
                <div className="px-4 py-5 flex items-center gap-3">
                    <img
                        src={logoImg}
                        alt="BivaStat Logo"
                        className="w-10 h-10 rounded-lg object-cover shadow-sm border border-[#e9e9e8]"
                    />
                    <div>
                        <h1 className="text-sm font-black tracking-tight text-[#37352f]">BIVASTAT 关联挖掘</h1>
                        <p className="text-[10px] text-emerald-600 font-bold opacity-80 uppercase tracking-tighter">专业版 · V1.0</p>
                    </div>
                </div>

                {/* 侧边栏底部版本信息 */}

                <nav className="flex-1 flex flex-col gap-1 p-4">
                    {menuItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            end={item.path === '/'}
                            onClick={() => setIsMobileMenuOpen(false)}
                            className={({ isActive }) => cn(
                                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group",
                                isActive
                                    ? "bg-[#ebf3fb] text-[#2383e2] font-semibold"
                                    : "text-[#37352f] hover:bg-[#efefee] hover:text-[#37352f]"
                            )}
                        >
                            {({ isActive }) => (
                                <>
                                    <item.icon size={18} className={cn(
                                        "transition-colors duration-200 shrink-0",
                                        isActive ? "text-[#2383e2]" : "text-[#8e8e8e] group-hover:text-[#37352f]"
                                    )} />
                                    <span className="text-sm">{item.label}</span>
                                </>
                            )}
                        </NavLink>
                    ))}
                </nav>

                <div className="p-4 mt-auto border-t border-[#e9e9e8]/50 space-y-1">
                    <NavLink
                        to="/help"
                        className={({ isActive }) => cn(
                            "flex items-center gap-3 px-3 py-2.5 w-full rounded-lg transition-all duration-200 group",
                            isActive
                                ? "bg-[#ebf3fb] text-[#2383e2] font-semibold"
                                : "text-[#37352f]/70 hover:bg-[#efefee] hover:text-[#37352f]"
                        )}
                    >
                        {({ isActive }) => (
                            <>
                                <HelpCircle size={18} className={cn("shrink-0 transition-colors", isActive ? "text-[#2383e2]" : "text-[#8e8e8e] group-hover:text-[#37352f]")} />
                                <span className="text-sm">帮助文档</span>
                            </>
                        )}
                    </NavLink>
                    <div className="px-3 py-2 text-[9px] text-[#b4b4b3] font-mono">
                        <div className="flex items-center gap-1.5">
                            <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                            BivaStat-Miner V1.0.0
                        </div>
                        <div className="mt-1 opacity-60">© 2026 ZSY · MIT License</div>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col overflow-hidden w-full max-w-full relative">
                <header className="h-[52px] border-b border-[#e9e9e8] bg-white flex items-center justify-between px-6 z-10 shrink-0 shadow-sm shadow-black/5">
                    <div className="flex items-center gap-4">
                        <button
                            className="p-1.5 hover:bg-[#efefee] rounded-md md:hidden transition-colors"
                            onClick={() => setIsMobileMenuOpen(true)}
                        >
                            <Menu size={20} className="text-[#37352f]" />
                        </button>
                        <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#b4b4b3] hidden sm:flex">
                            <span className="hover:text-[#37352f] cursor-default transition-colors">工作空间</span>
                            <ChevronRight size={12} className="opacity-30" />
                            <span className="text-[#37352f] bg-[#f5f5f4] px-2 py-0.5 rounded-md">{getCurrentPageLabel()}</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-[#efefee]/50 rounded-full border border-[#e9e9e8]">
                            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                            <span className="text-[10px] font-semibold text-[#37352f]">系统在线</span>
                        </div>
                        <div className="w-px h-4 bg-[#e9e9e8] hidden sm:block" />
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <button className="flex items-center gap-2 p-1.5 hover:bg-[#efefee] rounded-xl transition-all border border-transparent hover:border-[#e9e9e8] focus:outline-none">
                                    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#2383e2] to-[#0070d2] flex items-center justify-center text-white text-[11px] font-black shadow-sm">
                                        A
                                    </div>
                                </button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-56">
                                <div className="px-3 py-2.5 border-b border-[#f1f1f0]">
                                    <div className="text-sm font-semibold text-[#37352f]">分析员用户</div>
                                    <div className="text-[11px] text-[#b4b4b3] mt-0.5">admin@bivastat.local</div>
                                </div>
                                <div className="p-1 mt-1">
                                    <DropdownMenuItem
                                        onClick={() => toast.info('个人资料模块将在后续版本开放')}
                                        className="text-[#37352f]"
                                    >
                                        <User size={14} className="text-[#b4b4b3]" /> 个人资料
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                        onClick={() => setShowAboutModal(true)}
                                        className="text-[#37352f]"
                                    >
                                        <Info size={14} className="text-[#b4b4b3]" /> 关于系统
                                    </DropdownMenuItem>
                                </div>
                                <DropdownMenuSeparator />
                                <div className="p-1">
                                    <DropdownMenuItem
                                        onClick={async () => {
                                            const ok = await confirm('确定要退出当前登录状态吗？');
                                            if (ok) {
                                                toast.success('已退出登录');
                                                navigate('/');
                                            }
                                        }}
                                        className="text-red-500 focus:text-red-500 focus:bg-red-50"
                                    >
                                        <LogOut size={14} /> 退出登录
                                    </DropdownMenuItem>
                                </div>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                </header>

                <main className="flex-1 overflow-y-auto p-3 sm:p-5 md:p-8 lg:p-10 bg-[#fbfbfa] w-full overflow-x-hidden">
                    {children}
                </main>
            </div>

            {/* 关于系统弹窗 - 使用 shadcn Dialog */}
            <Dialog open={showAboutModal} onOpenChange={setShowAboutModal}>
                <DialogContent className="max-w-sm text-center">
                    <DialogHeader>
                        <img src={logoImg} alt="Logo" className="w-16 h-16 rounded-2xl mx-auto mb-3 shadow-md border border-[#e9e9e8]" />
                        <DialogTitle className="text-center text-lg font-black">BIVASTAT 关联挖掘引擎</DialogTitle>
                        <DialogDescription className="text-center">
                            <span className="text-emerald-600 font-semibold">专业版 · V1.0.0</span>
                        </DialogDescription>
                    </DialogHeader>
                    <div className="text-xs text-[#787774] space-y-1.5 leading-relaxed">
                        <p>双变量关联挖掘与非参数统计分析平台</p>
                        <p>基于启发式算法的智能数据洞察系统</p>
                        <p className="text-[#b4b4b3] mt-2">© 2026 ZSY · MIT License</p>
                    </div>
                    <DialogFooter className="mt-4 justify-center sm:justify-center">
                        <Button onClick={() => setShowAboutModal(false)} size="sm">关闭</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default Layout;
