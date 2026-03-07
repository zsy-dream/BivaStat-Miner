/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useCallback, useRef, useMemo } from 'react';
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react';
import { cn } from '../utils/cn';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
} from './ui/dialog';
import { Button } from './ui/button';

// ======================== Types ========================

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface ToastItem {
    id: number;
    type: ToastType;
    message: string;
}

interface ToastContextValue {
    toast: {
        success: (msg: string) => void;
        error: (msg: string) => void;
        info: (msg: string) => void;
        warning: (msg: string) => void;
    };
    /** 替代 window.confirm 的异步确认 */
    confirm: (message: string) => Promise<boolean>;
}

// ======================== Context ========================

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
    const ctx = useContext(ToastContext);
    if (!ctx) throw new Error('useToast must be used within ToastProvider');
    return ctx;
}

// ======================== Provider ========================

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [toasts, setToasts] = useState<ToastItem[]>([]);
    const [confirmState, setConfirmState] = useState<{
        message: string;
        resolve: (val: boolean) => void;
    } | null>(null);
    const idRef = useRef(0);

    const addToast = useCallback((type: ToastType, message: string) => {
        const id = ++idRef.current;
        // 控制最多同时展示 2 条，避免刷屏
        setToasts(prev => {
            const next = [...prev, { id, type, message }];
            const MAX = 2;
            return next.slice(Math.max(0, next.length - MAX), next.length);
        });
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.id !== id));
        }, 4000);
    }, []);

    const removeToast = useCallback((id: number) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    const toast = useMemo(() => ({
        success: (msg: string) => addToast('success', msg),
        error: (msg: string) => addToast('error', msg),
        info: (msg: string) => addToast('info', msg),
        warning: (msg: string) => addToast('warning', msg),
    }), [addToast]);

    const confirm = useCallback((message: string): Promise<boolean> => {
        return new Promise(resolve => {
            setConfirmState({ message, resolve });
        });
    }, []);

    const handleConfirm = (result: boolean) => {
        confirmState?.resolve(result);
        setConfirmState(null);
    };

    const iconMap: Record<ToastType, React.ReactNode> = {
        success: <CheckCircle size={16} className="text-emerald-500" />,
        error: <AlertCircle size={16} className="text-red-500" />,
        info: <Info size={16} className="text-blue-500" />,
        warning: <AlertCircle size={16} className="text-amber-500" />,
    };

    const bgMap: Record<ToastType, string> = {
        success: 'border-emerald-200 bg-emerald-50',
        error: 'border-red-200 bg-red-50',
        info: 'border-blue-200 bg-blue-50',
        warning: 'border-amber-200 bg-amber-50',
    };

    return (
        <ToastContext.Provider value={{ toast, confirm }}>
            {children}

            {/* Toast 容器 */}
            <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none max-w-sm">
                {toasts.map(t => (
                    <div
                        key={t.id}
                        className={cn(
                            "pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-xl border shadow-lg backdrop-blur-sm animate-in slide-in-from-right fade-in duration-300",
                            bgMap[t.type]
                        )}
                    >
                        <span className="mt-0.5 shrink-0">{iconMap[t.type]}</span>
                        <p className="text-sm font-medium text-[#37352f] flex-1 leading-relaxed">{t.message}</p>
                        <button
                            onClick={() => removeToast(t.id)}
                            className="shrink-0 text-[#b4b4b3] hover:text-[#37352f] transition-colors mt-0.5"
                        >
                            <X size={14} />
                        </button>
                    </div>
                ))}
            </div>

            {/* Confirm 对话框 - 使用 shadcn Dialog */}
            <Dialog open={!!confirmState} onOpenChange={(open) => { if (!open) handleConfirm(false); }}>
                <DialogContent className="max-w-sm">
                    <DialogHeader>
                        <div className="flex items-center gap-3 mb-1">
                            <div className="w-9 h-9 bg-amber-50 rounded-xl flex items-center justify-center shrink-0 border border-amber-100">
                                <AlertCircle size={18} className="text-amber-500" />
                            </div>
                            <DialogTitle>操作确认</DialogTitle>
                        </div>
                        <DialogDescription>{confirmState?.message}</DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => handleConfirm(false)}>
                            取消
                        </Button>
                        <Button size="sm" onClick={() => handleConfirm(true)}>
                            确认
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </ToastContext.Provider>
    );
};
