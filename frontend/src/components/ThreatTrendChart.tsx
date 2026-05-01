import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import { ExportButton } from './ExportButton';
import { DateFilter, TimeRange, parseDaysFromRange } from './DateFilter';
import { LoadingSkeleton } from './LoadingSkeleton';
import { dashboardAnalyticsApi, ThreatTrendData } from '../services/dashboardAnalytics';
import { TrendingUp } from 'lucide-react';

interface ThreatTrendChartProps {
    onDateClick?: (date: string) => void;
}

export const ThreatTrendChart: React.FC<ThreatTrendChartProps> = ({
    onDateClick
}) => {
    const [data, setData] = useState<ThreatTrendData[]>([]);
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState<TimeRange>('7d');

    const { lastMessage } = useWebSocket();

    useEffect(() => {
        loadData();
    }, [timeRange]);

    useEffect(() => {
        if (lastMessage && (lastMessage.type === 'threat_alert' || lastMessage.type === 'alert' || lastMessage.type === 'email_analysis')) {
            loadData();
        }
    }, [lastMessage]);

    const loadData = async () => {
        setLoading(true);
        try {
            const days = parseDaysFromRange(timeRange);
            const result = await dashboardAnalyticsApi.getThreatTrend(days);
            setData(result);
        } catch (error) {
            console.error('Error loading threat trend:', error);
        } finally {
            setLoading(false);
        }
    };

    // Calculate summary stats
    const totalThreats = data.reduce((sum, d) => sum + d.threats, 0);
    const totalBlocked = data.reduce((sum, d) => sum + d.blocked, 0);
    const totalQuarantined = data.reduce((sum, d) => sum + d.quarantined, 0);

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            const fullDate = payload[0].payload.full_date;

            return (
                <div className="glass-card rounded-2xl p-4 shadow-2xl border border-white/10 min-w-[180px]">
                    <p className="text-white font-black text-sm mb-3 pb-2 border-b border-white/10">{label}</p>
                    {payload.map((entry: any, index: number) => (
                        <div key={index} className="flex items-center justify-between gap-4 text-sm py-1">
                            <div className="flex items-center gap-2">
                                <div
                                    className="w-2.5 h-2.5 rounded-full"
                                    style={{ backgroundColor: entry.color }}
                                />
                                <span className="text-slate-400 font-medium">{entry.name}</span>
                            </div>
                            <span className="text-white font-black">{entry.value}</span>
                        </div>
                    ))}
                    {onDateClick && (
                        <button
                            onClick={() => onDateClick(fullDate || label)}
                            className="mt-3 w-full text-xs font-bold text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-xl py-2 transition-all"
                        >
                            Показать детали →
                        </button>
                    )}
                </div>
            );
        }
        return null;
    };

    if (loading) {
        return <LoadingSkeleton height={400} />;
    }

    return (
        <div id="threat-trend-chart" className="glass-card rounded-3xl p-8">
            {/* Header */}
            <div className="flex items-start justify-between mb-8">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-red-500/10 rounded-2xl">
                        <TrendingUp className="w-6 h-6 text-red-400" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-black text-white tracking-tight">Динамика угроз</h2>
                        <div className="flex items-center gap-2">
                            <p className="text-sm text-slate-500 font-medium mt-0.5">
                                Статистика обнаруженных инцидентов
                            </p>
                            <span className="flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-red-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                            </span>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <DateFilter value={timeRange} onChange={setTimeRange} />
                    <ExportButton elementId="threat-trend-chart" filename="threat-trend" />
                </div>
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-3 gap-4 mb-8">
                <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-4 text-center">
                    <p className="text-[10px] font-bold text-red-400/60 uppercase tracking-widest mb-1">Угрозы</p>
                    <p className="text-3xl font-black text-red-400">{totalThreats}</p>
                </div>
                <div className="bg-orange-500/10 border border-orange-500/20 rounded-2xl p-4 text-center">
                    <p className="text-[10px] font-bold text-orange-400/60 uppercase tracking-widest mb-1">Заблокировано</p>
                    <p className="text-3xl font-black text-orange-400">{totalBlocked}</p>
                </div>
                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-2xl p-4 text-center">
                    <p className="text-[10px] font-bold text-yellow-400/60 uppercase tracking-widest mb-1">Карантин</p>
                    <p className="text-3xl font-black text-yellow-400">{totalQuarantined}</p>
                </div>
            </div>

            {/* Chart */}
            <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={data}>
                    <defs>
                        <linearGradient id="colorThreats" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorBlocked" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f97316" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorQuarantined" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#eab308" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#eab308" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis
                        dataKey="date"
                        stroke="#475569"
                        style={{ fontSize: '11px', fontWeight: 600 }}
                        tickLine={false}
                        axisLine={false}
                    />
                    <YAxis
                        stroke="#475569"
                        style={{ fontSize: '11px', fontWeight: 600 }}
                        tickLine={false}
                        axisLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#3b82f6', strokeWidth: 1, strokeDasharray: '5 5' }} />
                    <Area
                        type="monotone"
                        dataKey="threats"
                        stroke="#ef4444"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorThreats)"
                        name="Угрозы"
                        dot={false}
                        activeDot={{ r: 6, fill: '#ef4444', stroke: '#0f172a', strokeWidth: 3 }}
                    />
                    <Area
                        type="monotone"
                        dataKey="blocked"
                        stroke="#f97316"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorBlocked)"
                        name="Заблокировано"
                        dot={false}
                        activeDot={{ r: 6, fill: '#f97316', stroke: '#0f172a', strokeWidth: 3 }}
                    />
                    <Area
                        type="monotone"
                        dataKey="quarantined"
                        stroke="#eab308"
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#colorQuarantined)"
                        name="Карантин"
                        dot={false}
                        activeDot={{ r: 6, fill: '#eab308', stroke: '#0f172a', strokeWidth: 3 }}
                    />
                </AreaChart>
            </ResponsiveContainer>

            {/* Legend */}
            <div className="flex items-center justify-center gap-8 mt-6 pt-6 border-t border-white/5">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500 shadow-lg shadow-red-500/30" />
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Угрозы</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-orange-500 shadow-lg shadow-orange-500/30" />
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Заблокировано</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-yellow-500 shadow-lg shadow-yellow-500/30" />
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Карантин</span>
                </div>
            </div>
        </div>
    );
};
