import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
} from 'recharts';
import { ExportButton } from './ExportButton';
import { LoadingSkeleton } from './LoadingSkeleton';
import { dashboardAnalyticsApi, ActivityData } from '../services/dashboardAnalytics';
import { Clock, Flame, Moon, Sun } from 'lucide-react';

export const ActivityHeatmap: React.FC = () => {
    const [data, setData] = useState<ActivityData[]>([]);
    const [loading, setLoading] = useState(true);

    const { lastMessage } = useWebSocket();

    useEffect(() => {
        loadData();
    }, []);

    useEffect(() => {
        if (lastMessage && (lastMessage.type === 'threat_alert' || lastMessage.type === 'alert' || lastMessage.type === 'email_analysis')) {
            loadData();
        }
    }, [lastMessage]);

    const loadData = async () => {
        try {
            const result = await dashboardAnalyticsApi.getActivityHeatmap();
            setData(result);
        } catch (error) {
            console.error('Error loading activity heatmap:', error);
        } finally {
            setLoading(false);
        }
    };

    const getBarColor = (count: number) => {
        if (count === 0) return '#1e293b';
        if (count < 5) return '#3b82f6';
        if (count < 10) return '#eab308';
        if (count < 20) return '#f97316';
        return '#ef4444';
    };

    const getBarGlow = (count: number) => {
        if (count >= 20) return '0 0 15px rgba(239,68,68,0.5)';
        if (count >= 10) return '0 0 10px rgba(249,115,22,0.4)';
        return 'none';
    };

    // Find peak hour
    const peakHour = data.reduce((max, d) => d.count > max.count ? d : max, { hour: '00:00', count: 0 });
    const totalCount = data.reduce((sum, d) => sum + d.count, 0);

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            const count = payload[0].value;
            return (
                <div className="glass-card rounded-2xl p-4 shadow-2xl border border-white/10 min-w-[140px]">
                    <p className="text-white font-black text-lg">{label}</p>
                    <div className="flex items-center gap-2 mt-2">
                        <Flame className={`w-4 h-4 ${count >= 10 ? 'text-red-400' : count >= 5 ? 'text-yellow-400' : 'text-blue-400'}`} />
                        <span className="text-slate-400 text-sm font-medium">{count} атак</span>
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
        <div id="activity-heatmap-container" className="glass-card rounded-3xl p-8 flex flex-col h-[450px]">
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-blue-500/10 rounded-2xl">
                        <Clock className="w-6 h-6 text-blue-400" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-black text-white tracking-tight">Активность</h2>
                        <p className="text-sm text-slate-500 font-medium mt-0.5">
                            Распределение угроз по часам
                        </p>
                    </div>
                </div>
                <ExportButton elementId="activity-heatmap-container" filename="activity-heatmap" />
            </div>

            {/* Stats Row */}
            <div className="flex items-center gap-4 mb-6">
                <div className="flex items-center gap-2 px-4 py-2 bg-red-500/10 border border-red-500/20 rounded-xl">
                    <Flame className="w-4 h-4 text-red-400" />
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Пик:</span>
                    <span className="text-xs font-black text-white">{peakHour.hour}</span>
                </div>
                <div className="flex items-center gap-2 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Всего:</span>
                    <span className="text-xs font-black text-blue-400">{totalCount}</span>
                </div>
            </div>

            {/* Chart */}
            <div className="flex-1">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} barCategoryGap="15%">
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis
                            dataKey="hour"
                            stroke="#475569"
                            style={{ fontSize: '10px', fontWeight: 600 }}
                            interval={2}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis
                            stroke="#475569"
                            style={{ fontSize: '11px', fontWeight: 600 }}
                            tickLine={false}
                            axisLine={false}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                        <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                            {data.map((entry, index) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={getBarColor(entry.count)}
                                    style={{ filter: entry.count >= 10 ? `drop-shadow(${getBarGlow(entry.count)})` : 'none' }}
                                />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div className="flex items-center justify-center gap-6 mt-6 pt-6 border-t border-white/5">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-slate-700" />
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">0</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">1-4</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-yellow-500" />
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">5-9</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-orange-500" />
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">10-19</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500 shadow-lg shadow-red-500/30" />
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">20+</span>
                </div>
            </div>
        </div>
    );
};
