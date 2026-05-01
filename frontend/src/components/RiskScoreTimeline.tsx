import React, { useState, useEffect } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine,
    Area,
    ComposedChart,
} from 'recharts';
import { ExportButton } from './ExportButton';
import { DateFilter, TimeRange, parseDaysFromRange } from './DateFilter';
import { LoadingSkeleton } from './LoadingSkeleton';
import { dashboardAnalyticsApi, RiskTimelineData } from '../services/dashboardAnalytics';
import { Activity, AlertTriangle, ShieldCheck, TrendingDown, TrendingUp } from 'lucide-react';

export const RiskScoreTimeline: React.FC = () => {
    const [data, setData] = useState<RiskTimelineData[]>([]);
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState<TimeRange>('14d');

    useEffect(() => {
        loadData();
    }, [timeRange]);

    const loadData = async () => {
        setLoading(true);
        try {
            const days = parseDaysFromRange(timeRange);
            const result = await dashboardAnalyticsApi.getRiskTimeline(days);
            setData(result);
        } catch (error) {
            console.error('Error loading risk timeline:', error);
        } finally {
            setLoading(false);
        }
    };

    // Calculate stats
    const currentScore = data.length > 0 ? Math.round(data[data.length - 1].score) : 0;
    const previousScore = data.length > 1 ? Math.round(data[data.length - 2].score) : currentScore;
    const trend = currentScore - previousScore;
    const avgScore = data.length > 0 ? Math.round(data.reduce((sum, d) => sum + d.average, 0) / data.length) : 0;
    const maxScore = data.length > 0 ? Math.round(Math.max(...data.map(d => d.score))) : 0;

    const getRiskLevel = (score: number) => {
        if (score >= 75) return { label: 'Критический', color: '#ef4444', bg: 'bg-red-500/10', border: 'border-red-500/20' };
        if (score >= 50) return { label: 'Высокий', color: '#f97316', bg: 'bg-orange-500/10', border: 'border-orange-500/20' };
        if (score >= 25) return { label: 'Средний', color: '#eab308', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20' };
        return { label: 'Низкий', color: '#22c55e', bg: 'bg-green-500/10', border: 'border-green-500/20' };
    };

    const currentLevel = getRiskLevel(currentScore);

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            const score = payload[0]?.value || 0;
            const avg = payload[1]?.value || 0;
            const level = getRiskLevel(score);

            return (
                <div className="glass-card rounded-2xl p-4 shadow-2xl border border-white/10 min-w-[180px]">
                    <p className="text-white font-black text-sm mb-3 pb-2 border-b border-white/10">{label}</p>
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-slate-400 text-sm">Макс. риск:</span>
                            <span className="font-black text-white">{score}</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-slate-400 text-sm">Средний:</span>
                            <span className="font-bold text-slate-300">{avg}</span>
                        </div>
                    </div>
                    <div
                        className={`mt-3 text-[10px] font-black text-center px-3 py-1.5 rounded-lg uppercase tracking-widest ${level.bg} ${level.border} border`}
                        style={{ color: level.color }}
                    >
                        {level.label}
                    </div>
                </div>
            );
        }
        return null;
    };

    if (loading) {
        return <LoadingSkeleton height={450} />;
    }

    return (
        <div id="risk-score-timeline" className="glass-card rounded-3xl p-8">
            {/* Header */}
            <div className="flex items-start justify-between mb-8">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-purple-500/10 rounded-2xl">
                        <Activity className="w-6 h-6 text-purple-400" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-black text-white tracking-tight">Индекс риска</h2>
                        <p className="text-sm text-slate-500 font-medium mt-0.5">
                            Динамика угроз в системе
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <DateFilter value={timeRange} onChange={setTimeRange} />
                    <ExportButton elementId="risk-score-timeline" filename="risk-timeline" />
                </div>
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div className={`${currentLevel.bg} ${currentLevel.border} border rounded-2xl p-4 text-center`}>
                    <p className="text-[10px] font-bold uppercase tracking-widest mb-1" style={{ color: `${currentLevel.color}80` }}>Текущий</p>
                    <p className="text-3xl font-black" style={{ color: currentLevel.color }}>{currentScore}</p>
                    <div className="flex items-center justify-center gap-1 mt-2">
                        {trend > 0 ? (
                            <TrendingUp className="w-3 h-3 text-red-400" />
                        ) : trend < 0 ? (
                            <TrendingDown className="w-3 h-3 text-green-400" />
                        ) : null}
                        <span className={`text-[10px] font-bold ${trend > 0 ? 'text-red-400' : trend < 0 ? 'text-green-400' : 'text-slate-500'}`}>
                            {trend > 0 ? `+${trend}` : trend}
                        </span>
                    </div>
                </div>
                <div className="bg-slate-500/10 border border-slate-500/20 rounded-2xl p-4 text-center">
                    <p className="text-[10px] font-bold text-slate-500/60 uppercase tracking-widest mb-1">Средний</p>
                    <p className="text-3xl font-black text-slate-400">{avgScore}</p>
                </div>
                <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-4 text-center">
                    <p className="text-[10px] font-bold text-red-400/60 uppercase tracking-widest mb-1">Максимум</p>
                    <p className="text-3xl font-black text-red-400">{maxScore}</p>
                </div>
                <div className={`${currentLevel.bg} ${currentLevel.border} border rounded-2xl p-4 text-center flex flex-col items-center justify-center`}>
                    <p className="text-[10px] font-bold uppercase tracking-widest mb-2" style={{ color: `${currentLevel.color}80` }}>Статус</p>
                    {currentScore < 50 ? (
                        <ShieldCheck className="w-8 h-8" style={{ color: currentLevel.color }} />
                    ) : (
                        <AlertTriangle className="w-8 h-8" style={{ color: currentLevel.color }} />
                    )}
                </div>
            </div>

            {/* Chart */}
            <div className="h-[280px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={data}>
                        <defs>
                            <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis
                            dataKey="timestamp"
                            stroke="#475569"
                            style={{ fontSize: '11px', fontWeight: 600 }}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis
                            stroke="#475569"
                            style={{ fontSize: '11px', fontWeight: 600 }}
                            domain={[0, 100]}
                            tickLine={false}
                            axisLine={false}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#3b82f6', strokeWidth: 1, strokeDasharray: '5 5' }} />
                        <ReferenceLine y={25} stroke="#eab308" strokeDasharray="3 3" strokeOpacity={0.5} />
                        <ReferenceLine y={50} stroke="#f97316" strokeDasharray="3 3" strokeOpacity={0.5} />
                        <ReferenceLine y={75} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.5} />
                        <Area
                            type="monotone"
                            dataKey="score"
                            fill="url(#riskGradient)"
                            stroke="transparent"
                        />
                        <Line
                            type="monotone"
                            dataKey="score"
                            stroke="#ef4444"
                            strokeWidth={3}
                            dot={false}
                            activeDot={{ r: 6, fill: '#ef4444', stroke: '#0f172a', strokeWidth: 3 }}
                            name="Макс. риск"
                        />
                        <Line
                            type="monotone"
                            dataKey="average"
                            stroke="#64748b"
                            strokeWidth={2}
                            strokeDasharray="5 5"
                            dot={false}
                            name="Средний риск"
                        />
                    </ComposedChart>
                </ResponsiveContainer>
            </div>

            {/* Risk Level Legend */}
            <div className="flex items-center justify-center gap-6 mt-6 pt-6 border-t border-white/5">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">&lt; 25</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-yellow-500" />
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">25-49</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-orange-500" />
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">50-74</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500 shadow-lg shadow-red-500/30" />
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">75+</span>
                </div>
            </div>
        </div>
    );
};
