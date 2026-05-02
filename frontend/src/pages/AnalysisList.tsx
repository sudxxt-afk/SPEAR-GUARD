import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { analysisApi } from '../services/api';
import type { EmailAnalysis } from '../types';
import {
    Search,
    ChevronLeft,
    ChevronRight,
    ShieldAlert,
    ShieldCheck,
    ShieldQuestion,
    ShieldX,
    FileText,
    Terminal,
    Shield
} from 'lucide-react';
import { LiveConsole } from '../components/LiveConsole';

export const AnalysisList: React.FC = () => {
    const navigate = useNavigate();
    const [analyses, setAnalyses] = useState<EmailAnalysis[]>([]);
    const [loading, setLoading] = useState(true);
    const [totalCount, setTotalCount] = useState(0);
    const [page, setPage] = useState(1);
    const [showConsole, setShowConsole] = useState(false);
    const limit = 20;

    useEffect(() => {
        const loadAnalysis = async () => {
            setLoading(true);
            try {
                const offset = (page - 1) * limit;
                const response = await analysisApi.getAnalysis(limit, offset);
                setAnalyses(response.data);
                setTotalCount(response.count);
            } catch (error) {
                console.error('Failed to load analysis list:', error);
            } finally {
                setLoading(false);
            }
        };

        loadAnalysis();
    }, [page]);

    const totalPages = Math.ceil(totalCount / limit);

    const getRiskColor = (score: number) => {
        if (score >= 80) return 'text-red-400';
        if (score >= 50) return 'text-yellow-400';
        return 'text-green-400';
    };

    const getRiskBg = (score: number) => {
        if (score >= 80) return 'bg-red-500/10 border-red-500/20';
        if (score >= 50) return 'bg-yellow-500/10 border-yellow-500/20';
        return 'bg-green-500/10 border-green-500/20';
    };

    return (
        <Layout>
            <div className="space-y-8 animate-fadeIn">
                <div className="flex items-center justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <span className="h-1 w-8 bg-blue-500 rounded-full" />
                            <p className="text-blue-400 text-xs font-black uppercase tracking-[0.2em]">Журнал событий</p>
                        </div>
                        <h1 className="text-4xl font-black text-white tracking-tighter">Все анализы</h1>
                    </div>

                    <button
                        onClick={() => setShowConsole(!showConsole)}
                        className={`
                            flex items-center gap-2 px-4 py-2 rounded-xl border transition-all
                            ${showConsole
                                ? 'bg-green-500/10 border-green-500/50 text-green-400 shadow-[0_0_15px_rgba(74,222,128,0.2)]'
                                : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10 hover:text-white'
                            }
                        `}
                    >
                        <Terminal className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase tracking-wider">
                            {showConsole ? 'Скрыть консоль' : 'Live Логи'}
                        </span>
                    </button>
                </div>

                {showConsole && <LiveConsole onClose={() => setShowConsole(false)} />}

                {/* Filter Bar (Placeholder for now) */}
                <div className="flex items-center gap-4 bg-white/[0.02] p-4 rounded-2xl border border-white/5">
                    <div className="relative flex-1 max-w-md group">
                        <input
                            type="text"
                            placeholder="Поиск по теме или отправителю..."
                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 pl-10 text-sm focus:outline-none focus:border-blue-500/50 focus:bg-white/10 transition-all"
                        />
                        <Search className="absolute left-3 top-3 w-4 h-4 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
                    </div>
                </div>

                {/* Create Table */}
                <div className="glass-card rounded-3xl overflow-hidden border border-white/5">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm text-slate-400">
                            <thead className="bg-white/[0.02] text-xs font-bold uppercase tracking-wider text-slate-300">
                                <tr>
                                    <th className="px-6 py-4">Статус</th>
                                    <th className="px-6 py-4">Отправитель</th>
                                    <th className="px-6 py-4">Тема</th>
                                    <th className="px-6 py-4 text-center">Риск</th>
                                    <th className="px-6 py-4 text-right">Вердикт</th>
                                    <th className="px-6 py-4 text-right">Дата</th>
                                    <th className="px-6 py-4 text-right">Фор</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {loading ? (
                                    Array.from({ length: 5 }).map((_, i) => (
                                        <tr key={i} className="animate-pulse">
                                            <td className="px-6 py-4"><div className="h-4 w-4 bg-white/10 rounded-full" /></td>
                                            <td className="px-6 py-4"><div className="h-4 w-32 bg-white/10 rounded" /></td>
                                            <td className="px-6 py-4"><div className="h-4 w-48 bg-white/10 rounded" /></td>
                                            <td className="px-6 py-4"><div className="h-6 w-12 bg-white/10 rounded mx-auto" /></td>
                                            <td className="px-6 py-4"><div className="h-6 w-20 bg-white/10 rounded ml-auto" /></td>
                                            <td className="px-6 py-4"><div className="h-4 w-24 bg-white/10 rounded ml-auto" /></td>
                                            <td className="px-6 py-4"><div className="h-6 w-8 bg-white/10 rounded ml-auto" /></td>
                                        </tr>
                                    ))
                                ) : analyses.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="px-6 py-12 text-center text-slate-500 font-medium">
                                            Нет данных для при отображения
                                        </td>
                                    </tr>
                                ) : (
                                    analyses.map((item) => (
                                        <tr
                                            key={item.id}
                                            onClick={() => navigate(`/analysis/${item.id}`)}
                                            className="hover:bg-white/[0.04] transition-colors cursor-pointer group"
                                        >
                                            <td className="px-6 py-4">
                                                {item.risk_score >= 80 ? <ShieldX className="w-5 h-5 text-red-500" /> :
                                                    item.risk_score >= 50 ? <ShieldAlert className="w-5 h-5 text-yellow-500" /> :
                                                        <ShieldCheck className="w-5 h-5 text-green-500" />
                                                }
                                            </td>
                                            <td className="px-6 py-4 font-medium text-slate-200 group-hover:text-white transition-colors">
                                                {item.sender_email}
                                            </td>
                                            <td className="px-6 py-4 truncate max-w-xs " title={item.subject || ''}>
                                                {item.subject || <span className="italic text-slate-600">Без темы</span>}
                                            </td>
                                            <td className="px-6 py-4 text-center">
                                                <span className={`px-2 py-1 rounded-lg text-xs font-black border tracking-wider ${getRiskColor(item.risk_score)} ${getRiskBg(item.risk_score)}`}>
                                                    {item.risk_score.toFixed(0)}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <span
                                                    className={`text-[10px] font-black px-2 py-0.5 rounded-md uppercase tracking-wider ${item.decision === 'DELIVER' ? 'bg-green-500/10 text-green-500' :
                                                        item.decision === 'QUARANTINE' ? 'bg-yellow-500/10 text-yellow-500' :
                                                            item.decision === 'BLOCK' ? 'bg-red-500/10 text-red-500' :
                                                                'bg-slate-500/10 text-slate-500'
                                                        }`}
                                                >
                                                    {item.decision}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-right text-xs font-mono text-slate-500">
                                                {new Date(item.created_at).toLocaleString('ru-RU')}
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        navigate(`/analysis/${item.id}?forensic=true`);
                                                    }}
                                                    className="px-2 py-1 text-xs bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 rounded border border-cyan-500/20"
                                                >
                                                    🔍
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination */}
                    <div className="px-6 py-4 border-t border-white/5 flex items-center justify-between bg-white/[0.02]">
                        <p className="text-xs text-slate-500 uppercase tracking-wider font-bold">
                            Всего: {totalCount}
                        </p>
                        <div className="flex items-center gap-2">
                            <button
                                disabled={page === 1}
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                className="p-2 rounded-lg hover:bg-white/5 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                            >
                                <ChevronLeft className="w-4 h-4" />
                            </button>
                            <div className="px-4 py-1.5 bg-white/5 rounded-lg text-xs font-bold">
                                {page} / {totalPages || 1}
                            </div>
                            <button
                                disabled={page >= totalPages}
                                onClick={() => setPage(p => p + 1)}
                                className="p-2 rounded-lg hover:bg-white/5 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                            >
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
};
