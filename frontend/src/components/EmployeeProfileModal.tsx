import React, { useEffect, useState } from 'react';
import {
    X,
    Shield,
    Mail,
    AlertTriangle,
    Clock,
    Activity,
    User,
    Globe,
    Lock
} from 'lucide-react';
import { EmployeeStats, employeesApi } from '../services/api';

interface EmployeeProfileModalProps {
    userId: number;
    onClose: () => void;
}

export const EmployeeProfileModal: React.FC<EmployeeProfileModalProps> = ({ userId, onClose }) => {
    const [stats, setStats] = useState<EmployeeStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadStats();
    }, [userId]);

    const loadStats = async () => {
        try {
            setLoading(true);
            const data = await employeesApi.getStats(userId);
            setStats(data);
        } catch (err) {
            setError('Не удалось загрузить профиль сотрудника');
        } finally {
            setLoading(false);
        }
    };

    if (!userId) return null;

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 animate-fadeIn p-4">
            <div className="glass-card w-full max-w-5xl h-[85vh] rounded-3xl border border-white/10 flex flex-col overflow-hidden relative shadow-2xl">

                {/* Close Button */}
                <button
                    onClick={onClose}
                    className="absolute top-6 right-6 p-2 rounded-full bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors z-10"
                >
                    <X className="w-6 h-6" />
                </button>

                {loading ? (
                    <div className="flex-1 flex flex-col items-center justify-center gap-4">
                        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                        <p className="text-slate-500 font-mono text-sm uppercase tracking-widest animate-pulse">Загрузка досье...</p>
                    </div>
                ) : error || !stats ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-red-400 gap-2">
                        <AlertTriangle className="w-12 h-12" />
                        <p>{error || 'Данные недоступны'}</p>
                    </div>
                ) : (
                    <div className="flex flex-col h-full overflow-hidden">

                        {/* Header Section */}
                        <div className="p-8 pb-6 border-b border-white/5 bg-gradient-to-r from-blue-900/10 to-transparent">
                            <div className="flex items-start gap-6">
                                {/* Avatar */}
                                <div className="relative">
                                    <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center border border-white/10 shadow-lg">
                                        <span className="text-3xl font-black text-white/20">
                                            {stats.user_info.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                                        </span>
                                    </div>
                                    <div className={`absolute -bottom-2 -right-2 w-6 h-6 rounded-full border-4 border-[#0f172a] ${stats.user_info.is_online ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]' : 'bg-slate-500'}`} />
                                </div>

                                <div className="flex-1 pt-1">
                                    <h2 className="text-3xl font-black text-white tracking-tight mb-1">{stats.user_info.full_name}</h2>
                                    <div className="flex items-center gap-4 text-slate-400 text-sm mb-4">
                                        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-white/5 border border-white/5">
                                            <Mail className="w-3.5 h-3.5" />
                                            {stats.user_info.email}
                                        </span>
                                        <span className="flex items-center gap-1.5">
                                            <User className="w-3.5 h-3.5" />
                                            {stats.user_info.role.toUpperCase()}
                                        </span>
                                        {stats.user_info.department && (
                                            <span className="px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 text-xs font-bold uppercase tracking-wider">
                                                {stats.user_info.department}
                                            </span>
                                        )}
                                    </div>

                                    <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
                                        <Clock className="w-3.5 h-3.5" />
                                        LAST SEEN: {stats.user_info.last_active ? new Date(stats.user_info.last_active).toLocaleString() : 'NEVER'}
                                    </div>
                                </div>

                                {/* Trust Score */}
                                <div className="flex flex-col items-center">
                                    <div className="relative w-20 h-20">
                                        <svg className="w-full h-full transform -rotate-90">
                                            <circle cx="40" cy="40" r="36" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-slate-800" />
                                            <circle cx="40" cy="40" r="36" stroke="currentColor" strokeWidth="8" fill="transparent"
                                                strokeDasharray={226}
                                                strokeDashoffset={226 - (226 * stats.stats.trust_score) / 100}
                                                className={`${stats.stats.trust_score > 70 ? 'text-green-500' : stats.stats.trust_score > 40 ? 'text-yellow-500' : 'text-red-500'} transition-all duration-1000 ease-out`}
                                            />
                                        </svg>
                                        <div className="absolute inset-0 flex items-center justify-center flex-col">
                                            <span className="text-xl font-bold text-white">{Math.round(stats.stats.trust_score)}</span>
                                            <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wide">Trust</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Content Scrollable */}
                        <div className="flex-1 overflow-y-auto custom-scrollbar p-8 pt-6 space-y-6">

                            {/* KPI Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
                                    <div className="flex items-start justify-between mb-2">
                                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Всего писем</p>
                                        <Mail className="w-4 h-4 text-blue-400" />
                                    </div>
                                    <p className="text-2xl font-black text-white">{stats.stats.total_emails}</p>
                                </div>

                                <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
                                    <div className="flex items-start justify-between mb-2">
                                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Высокий риск</p>
                                        <AlertTriangle className="w-4 h-4 text-red-500" />
                                    </div>
                                    <p className="text-2xl font-black text-red-400">{stats.stats.high_risk}</p>
                                    <p className="text-xs text-slate-500 mt-1">Попыток взлома</p>
                                </div>

                                <div className="bg-white/5 rounded-2xl p-4 border border-white/5">
                                    <div className="flex items-start justify-between mb-2">
                                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Репорты</p>
                                        <Shield className="w-4 h-4 text-green-400" />
                                    </div>
                                    <p className="text-2xl font-black text-green-400">{stats.stats.phishing_reports}</p>
                                    <p className="text-xs text-slate-500 mt-1">Отправлено пользователем</p>
                                </div>

                                <div className="bg-white/5 rounded-2xl p-4 border border-white/5 relative overflow-hidden">
                                    <div className="flex items-start justify-between mb-2 relative z-10">
                                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Трафик</p>
                                        <Globe className="w-4 h-4 text-purple-400" />
                                    </div>
                                    <div className="flex items-center gap-4 relative z-10 mt-1">
                                        <div>
                                            <p className="text-lg font-bold text-white">{stats.stats.internal_emails}</p>
                                            <p className="text-[10px] text-slate-400 uppercase">Внутр.</p>
                                        </div>
                                        <div className="h-8 w-px bg-white/10"></div>
                                        <div>
                                            <p className="text-lg font-bold text-white">{stats.stats.external_emails}</p>
                                            <p className="text-[10px] text-slate-400 uppercase">Внеш.</p>
                                        </div>
                                    </div>
                                    {/* Mini Donut Background */}
                                    <div className="absolute -bottom-4 -right-4 w-20 h-20 opacity-10">
                                        <svg viewBox="0 0 36 36" className="w-full h-full">
                                            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#fff" strokeWidth="4" />
                                            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#3b82f6" strokeWidth="4" strokeDasharray={`${(stats.stats.external_emails / (stats.stats.total_emails || 1)) * 100}, 100`} />
                                        </svg>
                                    </div>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                                {/* Left Col: Connected Accounts & Activity & Top Senders */}
                                <div className="space-y-6">

                                    {/* Mail Accounts */}
                                    <div className="bg-white/5 rounded-2xl border border-white/5 p-5">
                                        <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                                            <Lock className="w-4 h-4" /> Подключенные ящики
                                        </h3>
                                        <div className="space-y-2">
                                            {stats.mail_accounts.length === 0 ? (
                                                <p className="text-xs text-slate-500 italic">Нет подключенных ящиков</p>
                                            ) : (
                                                stats.mail_accounts.map((acc, idx) => (
                                                    <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-white/5 border border-white/5">
                                                        <span className="text-xs text-slate-300">{acc.email}</span>
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-[10px] text-slate-500 uppercase">{acc.provider}</span>
                                                            <div className={`w-1.5 h-1.5 rounded-full ${acc.is_active ? 'bg-green-500' : 'bg-red-500'}`} />
                                                        </div>
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                    </div>

                                    {/* Top Senders */}
                                    <div className="bg-white/5 rounded-2xl border border-white/5 p-5">
                                        <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                                            <Activity className="w-4 h-4" /> Топ отправителей
                                        </h3>
                                        <div className="space-y-3">
                                            {stats.top_senders.map((sender, idx) => (
                                                <div key={idx} className="flex items-center justify-between group">
                                                    <div className="flex items-center gap-3 min-w-0">
                                                        <div className="w-6 h-6 rounded bg-slate-800 flex items-center justify-center text-[10px] font-bold text-slate-400">
                                                            {idx + 1}
                                                        </div>
                                                        <div className="truncate">
                                                            <p className="text-xs font-bold text-slate-300 truncate max-w-[150px]">{sender.email}</p>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-3">
                                                        {sender.high_risk > 0 && (
                                                            <span className="text-[10px] font-bold text-red-400 bg-red-500/10 px-1.5 rounded">
                                                                {sender.high_risk} ALERT
                                                            </span>
                                                        )}
                                                        <span className="text-xs font-mono text-slate-500">{sender.count}</span>
                                                    </div>
                                                </div>
                                            ))}
                                            {stats.top_senders.length === 0 && (
                                                <p className="text-xs text-slate-500 italic">Нет данных</p>
                                            )}
                                        </div>
                                    </div>

                                    {/* Activity Heatmap */}
                                    <div className="bg-white/5 rounded-2xl border border-white/5 p-5">
                                        <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                                            <Clock className="w-4 h-4" /> Активность (24ч)
                                        </h3>
                                        <div className="flex items-end gap-1 h-24 pt-2">
                                            {stats.activity_by_hour.map((count, hour) => {
                                                const max = Math.max(...stats.activity_by_hour, 1);
                                                const height = (count / max) * 100;
                                                return (
                                                    <div key={hour} className="flex-1 flex flex-col items-center group relative">
                                                        <div
                                                            className={`w-full rounded-t-sm transition-all duration-500 ${count > 0 ? 'bg-blue-500 hover:bg-blue-400' : 'bg-slate-700/30'}`}
                                                            style={{ height: `${Math.max(height, 5)}%` }}
                                                        ></div>
                                                        {/* Tooltip */}
                                                        <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-black text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-20">
                                                            {hour}:00 - {count} писем
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                        <div className="flex justify-between mt-2 text-[9px] text-slate-600 font-mono uppercase">
                                            <span>00:00</span>
                                            <span>12:00</span>
                                            <span>23:00</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Right Col: Timeline */}
                                <div className="lg:col-span-2 bg-white/5 rounded-2xl border border-white/5 p-5 flex flex-col">
                                    <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <Activity className="w-4 h-4" /> Хронология событий (Timeline)
                                    </h3>

                                    <div className="space-y-0 relative border-l border-white/10 ml-3">
                                        {stats.recent_activity.length === 0 ? (
                                            <div className="pl-6 py-4 text-slate-500 text-sm italic">Нет активности</div>
                                        ) : (
                                            stats.recent_activity.map((act) => (
                                                <div key={act.id} className="relative pl-8 py-4 group hover:bg-white/[0.02] -ml-px border-l border-transparent hover:border-white/10 transition-colors">
                                                    {/* Dot */}
                                                    <div className={`absolute left-[-5px] top-5 w-2.5 h-2.5 rounded-full border-2 border-[#0f172a] ${act.risk_score >= 70 ? 'bg-red-500' :
                                                        act.risk_score >= 40 ? 'bg-yellow-500' : 'bg-green-500'
                                                        }`}></div>

                                                    <div className="flex items-start justify-between">
                                                        <div>
                                                            <h4 className="font-bold text-slate-200 text-sm mb-0.5">{act.subject || '(Без темы)'}</h4>
                                                            <div className="flex items-center gap-2 text-xs text-slate-500">
                                                                <span className="text-blue-400">{act.from_address}</span>
                                                                <span>•</span>
                                                                <span>{act.analyzed_at ? new Date(act.analyzed_at).toLocaleString() : 'Unknown date'}</span>
                                                            </div>
                                                        </div>
                                                        <div className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${act.risk_score >= 70 ? 'bg-red-500/20 text-red-400' :
                                                            act.risk_score >= 40 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'
                                                            }`}>
                                                            SCORE: {Math.round(act.risk_score)}
                                                        </div>
                                                    </div>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            </div>

                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
