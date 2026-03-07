import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface Props {
    children: React.ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error('[ErrorBoundary]', error, errorInfo);
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null });
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="flex flex-col items-center justify-center min-h-[60vh] w-full gap-6 text-center p-8">
                    <div className="w-20 h-20 bg-red-50 rounded-full flex items-center justify-center text-red-400 border border-red-100">
                        <AlertCircle size={40} />
                    </div>
                    <div className="space-y-2">
                        <h2 className="text-xl font-bold text-[#37352f]">页面组件渲染异常</h2>
                        <p className="text-sm text-[#787774] max-w-md leading-relaxed">
                            该模块发生了未预期的运行时错误。您可以尝试刷新页面，或联系技术支持团队。
                        </p>
                        {this.state.error && (
                            <details className="mt-4 text-left max-w-lg mx-auto">
                                <summary className="text-xs text-[#b4b4b3] cursor-pointer hover:text-[#787774] transition-colors font-mono">
                                    展开错误详情
                                </summary>
                                <pre className="mt-2 p-4 bg-[#1a1a1e] text-red-400 rounded-xl text-[10px] overflow-auto max-h-40 font-mono">
                                    {this.state.error.message}
                                    {'\n'}
                                    {this.state.error.stack}
                                </pre>
                            </details>
                        )}
                    </div>
                    <button
                        onClick={this.handleReset}
                        className="px-6 py-2.5 bg-[#2383e2] text-white rounded-xl font-bold flex items-center gap-2 hover:bg-[#0070d2] transition-colors shadow-lg shadow-blue-500/20"
                    >
                        <RefreshCw size={16} /> 重新加载组件
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}
