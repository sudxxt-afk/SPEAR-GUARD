import React from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface StatCardProps {
    title: string;
    value: number | string;
    icon: React.ReactNode;
    trend?: number;
    color: 'blue' | 'red' | 'yellow' | 'green' | 'purple';
    subtitle?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
    title,
    value,
    icon,
    trend,
    color,
    subtitle
}) => {
    const colorClasses = {
        blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
        red: 'bg-red-500/20 text-red-400 border-red-500/30',
        yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
        green: 'bg-green-500/20 text-green-400 border-green-500/30',
        purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    };

    return (
        <div className={`rounded-lg border p-6 ${colorClasses[color]} transition-all hover:scale-105 cursor-pointer`}>
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <p className="text-slate-400 text-sm font-medium">{title}</p>
                    <p className="text-3xl font-bold mt-2">{value}</p>
                    {subtitle && (
                        <p className="text-xs text-slate-500 mt-1">{subtitle}</p>
                    )}
                    {trend !== undefined && (
                        <div className="flex items-center gap-1 mt-2">
                            {trend >= 0 ? (
                                <ArrowUpRight className="w-4 h-4 text-red-400" />
                            ) : (
                                <ArrowDownRight className="w-4 h-4 text-green-400" />
                            )}
                            <span className="text-xs text-slate-400">
                                {Math.abs(trend)}% vs прошлой недели
                            </span>
                        </div>
                    )}
                </div>
                <div className="text-3xl opacity-50">{icon}</div>
            </div>
        </div>
    );
};
