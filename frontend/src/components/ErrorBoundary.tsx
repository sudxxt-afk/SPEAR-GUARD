import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('Uncaught error:', error, errorInfo);
    }

    public render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-[#0f172a] text-white flex items-center justify-center p-4">
                    <div className="glass-card max-w-md w-full p-8 rounded-3xl text-center border border-white/10 relative overflow-hidden">
                        {/* Ambient Background Glow */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] bg-red-500/10 blur-[80px] rounded-full pointer-events-none" />

                        <div className="relative z-10">
                            <div className="w-16 h-16 bg-red-500/10 rounded-2xl flex items-center justify-center mx-auto mb-6 border border-red-500/20 glow-red">
                                <AlertTriangle className="w-8 h-8 text-red-400" />
                            </div>

                            <h1 className="text-2xl font-black mb-2 tracking-tight">Критический сбой</h1>
                            <p className="text-slate-400 mb-6 text-sm font-medium leading-relaxed">
                                В системе обнаружена непредвиденная ошибка. Компонент интерфейса не смог отрисоваться корректно.
                            </p>

                            <div className="bg-slate-900/50 rounded-xl p-4 mb-6 text-left border border-white/5 overflow-auto max-h-32 custom-scrollbar">
                                <code className="text-[10px] font-mono text-red-300 break-all">
                                    {this.state.error?.toString()}
                                </code>
                            </div>

                            <button
                                onClick={() => window.location.reload()}
                                className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-white text-slate-900 rounded-xl font-bold hover:bg-slate-200 transition-colors"
                            >
                                <RefreshCw className="w-4 h-4" />
                                Перезагрузить систему
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
