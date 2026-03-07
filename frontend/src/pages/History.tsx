import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    History as HistoryIcon, Clock, ArrowRight, RefreshCw, Search, Trash2,
    CheckCircle2, AlertCircle, Loader2, Ban
} from 'lucide-react';
import { cn } from '../utils/cn';
import { motion, AnimatePresence } from 'framer-motion';
import { algorithmService } from '../services/api';
import { useToast } from '../components/Toast';
import { Button } from '../components/ui/button';
import type { TaskHistoryItem } from '../types';

export default function History() {
    const [tasks, setTasks] = useState<TaskHistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const navigate = useNavigate();
    const { toast, confirm } = useToast();

    useEffect(() => {
        fetchHistory();
    }, []);

    const fetchHistory = async () => {
        setLoading(true);
        try {
            const res = await algorithmService.getHistory();
            setTasks(res.tasks || []);
        } catch {
            console.error('Failed to fetch task archive');
        } finally {
            setLoading(false);
        }
    };

    const getStatusInfo = (status: string) => {
        switch (status) {
            case 'completed': return { label: '已完成', dot: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]', badge: 'border-emerald-200 bg-emerald-50 text-emerald-700', Icon: CheckCircle2 };
            case 'running':   return { label: '进行中', dot: 'bg-blue-500 animate-pulse', badge: 'border-blue-200 bg-blue-50 text-blue-700', Icon: Loader2 };
            case 'pending':   return { label: '等待中', dot: 'bg-blue-400 animate-pulse', badge: 'border-blue-200 bg-blue-50 text-blue-600', Icon: Loader2 };
            case 'failed':    return { label: '已失败', dot: 'bg-red-500', badge: 'border-red-200 bg-red-50 text-red-700', Icon: AlertCircle };
            case 'cancelled': return { label: '已取消', dot: 'bg-amber-400', badge: 'border-amber-200 bg-amber-50 text-amber-700', Icon: Ban };
            case 'stopped':   return { label: '已终止', dot: 'bg-amber-500', badge: 'border-amber-200 bg-amber-50 text-amber-700', Icon: Ban };
            default:          return { label: status, dot: 'bg-gray-400', badge: 'border-gray-200 bg-gray-50 text-gray-600', Icon: Clock };
        }
    };

    const formatDate = (dateStr: string) => {
        if (!dateStr) return '未知时间';
        const d = new Date(dateStr);
        return d.toLocaleString('zh-CN', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
    };

    const filteredTasks = tasks.filter(t =>
        t.task_id.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const deleteTask = async (e: React.MouseEvent, tid: string) => {
        e.stopPropagation();
        const ok = await confirm('确定要永久销毁此演算记录吗？此操作无法撤销。');
        if (!ok) return;

        try {
            await algorithmService.deleteTask(tid);
            setTasks(prev => prev.filter(t => t.task_id !== tid));
            toast.success('记录已永久删除');
        } catch {
            toast.error('删除失败，可能该记录正在被引擎锁定。');
        }
    };

    return (
        <div className="max-w-6xl mx-auto py-8 px-4 h-full flex flex-col">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 gap-6">
                <div className="flex items-center gap-4">
                    <div className="bg-primary-50 p-3 rounded-2xl text-primary-600 shadow-sm border border-primary-100">
                        <HistoryIcon size={28} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-black tracking-tight text-[#37352f]">历史任务</h1>
                        <p className="text-[#787774] text-sm mt-0.5 font-medium">持久化存储的所有算法演算历程</p>
                    </div>
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto">
                    <div className="relative flex-1 md:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#d3d3d3]" size={16} />
                        <input
                            type="text"
                            placeholder="检索任务 UUID..."
                            className="bg-white border border-[#e9e9e8] pl-10 pr-4 py-2 rounded-lg text-sm outline-none focus:border-primary-500 shadow-inner transition-all w-full"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <Button
                        variant="outline"
                        size="icon"
                        onClick={fetchHistory}
                        title="刷新列表"
                    >
                        <RefreshCw size={18} className={cn(loading && "animate-spin")} />
                    </Button>
                </div>
            </div>

            {loading ? (
                <div className="flex-1 flex flex-col items-center justify-center text-primary-600 opacity-50">
                    <RefreshCw className="w-8 h-8 animate-spin mb-4" />
                    <span className="text-sm font-bold tracking-widest uppercase">正在同步磁盘数据库...</span>
                </div>
            ) : filteredTasks.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center p-20 bg-white rounded-3xl border-2 border-dashed border-[#e9e9e8] text-center">
                    <div className="w-20 h-20 bg-[#f9f9f8] rounded-full flex items-center justify-center text-[#d3d3d3] mb-6">
                        <HistoryIcon size={40} />
                    </div>
                    <h3 className="text-lg font-bold text-[#37352f] mb-2">暂无历史记录</h3>
                    <p className="text-sm text-[#787774] max-w-xs">您的演算历程将在此持久化。请先前往算法大厅投递新的计算任务。</p>
                    <Button
                        onClick={() => navigate('/algorithm')}
                        className="mt-8"
                    >
                        前往算法配置 <ArrowRight size={16} />
                    </Button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <AnimatePresence>
                        {filteredTasks.map((task, idx) => (
                            <motion.div
                                key={task.task_id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.05 }}
                                className="notion-card p-0 overflow-hidden bg-white border-[#e9e9e8] group hover:border-primary-300 hover:shadow-xl hover:shadow-primary-500/5 transition-all cursor-pointer relative"
                                onClick={() => navigate(`/analysis_result?task_id=${task.task_id}`)}
                            >
                                <div className="p-5 border-b border-[#f9f9f8] flex items-center justify-between">
                                    <div className="flex items-center gap-2.5">
                                        {(() => {
                                            const s = getStatusInfo(task.status);
                                            return (
                                                <>
                                                    <div className={cn('w-2.5 h-2.5 rounded-full shrink-0', s.dot)} />
                                                    <span className={cn('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-black', s.badge)}>
                                                        {task.status === 'running' || task.status === 'pending'
                                                            ? <s.Icon size={10} className="animate-spin" />
                                                            : <s.Icon size={10} />}
                                                        {s.label}
                                                    </span>
                                                </>
                                            );
                                        })()}
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={(e) => deleteTask(e, task.task_id)}
                                            className="p-1.5 text-[#d3d3d3] hover:text-[#ea5b5c] hover:bg-red-50 rounded-lg transition-all"
                                            title="清理记录"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                        <span className="text-[11px] font-mono text-[#b4b4b3]">{task.task_id.slice(0, 8)}...</span>
                                    </div>
                                </div>

                                <div className="p-5 space-y-4">
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <div className="text-xs font-bold text-[#b4b4b3] mb-1 flex items-center gap-1.5 leading-none">
                                                <Clock size={12} /> {formatDate(task.start_time)}
                                            </div>
                                            <h4 className="text-sm font-black text-[#37352f] line-clamp-1">
                                                {task.type === 'algorithm_mining' ? '关联映射演算' : '非参数统计分析'}
                                            </h4>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-6">
                                        <div className="flex flex-col">
                                            <span className="text-[10px] font-bold text-[#b4b4b3] uppercase tracking-tighter">发现规则</span>
                                            <span className="text-lg font-black text-[#37352f] tabular-nums">{task.rules_found} <span className="text-[10px] font-medium opacity-30 text-[#37352f]">Rules</span></span>
                                        </div>
                                        <div className="w-px h-8 bg-[#e9e9e8]" />
                                        <div className="flex flex-col">
                                            <span className="text-[10px] font-bold text-[#b4b4b3] uppercase tracking-tighter">样本吞吐</span>
                                            <span className="text-lg font-black text-[#37352f] tabular-nums">{task.records} <span className="text-[10px] font-medium opacity-30 text-[#37352f]">Lines</span></span>
                                        </div>
                                    </div>
                                </div>

                                <div className="px-5 py-3.5 bg-[#fbfbfa] border-t border-[#f9f9f8] flex items-center justify-between group-hover:bg-primary-50 transition-colors">
                                    <span className="text-[11px] font-bold text-[#787774] group-hover:text-primary-600 transition-colors">点击追溯完整报表</span>
                                    <ArrowRight size={14} className="text-[#d3d3d3] group-hover:text-primary-500 group-hover:translate-x-1 transition-all" />
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            )}
        </div>
    );
}
