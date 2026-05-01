import React from 'react';
import { Calendar } from 'lucide-react';

export type TimeRange = '7d' | '14d' | '30d' | '90d';

interface DateFilterProps {
    value: TimeRange;
    onChange: (range: TimeRange) => void;
    label?: string;
}

export const DateFilter: React.FC<DateFilterProps> = ({ value, onChange, label }) => {
    const options: { value: TimeRange; label: string }[] = [
        { value: '7d', label: '7 дней' },
        { value: '14d', label: '14 дней' },
        { value: '30d', label: '30 дней' },
        { value: '90d', label: '90 дней' },
    ];

    return (
        <div className="flex items-center gap-2">
            {label && <span className="text-sm text-slate-400">{label}</span>}
            <div className="flex items-center gap-1 bg-slate-700/50 rounded-lg p-1">
                <Calendar className="w-4 h-4 text-slate-400 ml-2" />
                {options.map((option) => (
                    <button
                        key={option.value}
                        onClick={() => onChange(option.value)}
                        className={`
              px-3 py-1.5 text-sm rounded-md transition-all
              ${value === option.value
                                ? 'bg-blue-500 text-white font-semibold'
                                : 'text-slate-300 hover:text-white hover:bg-slate-600/50'
                            }
            `}
                    >
                        {option.label}
                    </button>
                ))}
            </div>
        </div>
    );
};

export const parseDaysFromRange = (range: TimeRange): number => {
    switch (range) {
        case '7d':
            return 7;
        case '14d':
            return 14;
        case '30d':
            return 30;
        case '90d':
            return 90;
        default:
            return 7;
    }
};
