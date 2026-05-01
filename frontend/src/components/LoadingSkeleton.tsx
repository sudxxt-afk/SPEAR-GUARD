import React from 'react';

interface LoadingSkeletonProps {
    height?: number;
    className?: string;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
    height = 300,
    className = ''
}) => {
    return (
        <div
            className={`bg-slate-800 rounded-lg border border-slate-700 p-6 ${className}`}
            style={{ height: `${height}px` }}
        >
            <div className="animate-pulse space-y-4">
                {/* Header skeleton */}
                <div className="flex items-center justify-between">
                    <div className="space-y-2">
                        <div className="h-6 bg-slate-700 rounded w-48"></div>
                        <div className="h-4 bg-slate-700/50 rounded w-32"></div>
                    </div>
                    <div className="flex gap-2">
                        <div className="h-8 bg-slate-700 rounded w-20"></div>
                        <div className="h-8 bg-slate-700 rounded w-20"></div>
                    </div>
                </div>

                {/* Chart skeleton */}
                <div className="relative" style={{ height: `${height - 100}px` }}>
                    <div className="absolute inset-0 flex items-end justify-around gap-2">
                        {Array.from({ length: 12 }).map((_, i) => (
                            <div
                                key={i}
                                className="bg-slate-700/50 rounded-t w-full"
                                style={{
                                    height: `${Math.random() * 60 + 20}%`,
                                    animationDelay: `${i * 0.1}s`,
                                }}
                            ></div>
                        ))}
                    </div>
                </div>

                {/* Legend skeleton */}
                <div className="flex items-center justify-center gap-6">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-slate-700 rounded-full"></div>
                            <div className="h-4 bg-slate-700 rounded w-16"></div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

interface FadeInProps {
    children: React.ReactNode;
    delay?: number;
    className?: string;
}

export const FadeIn: React.FC<FadeInProps> = ({
    children,
    delay = 0,
    className = ''
}) => {
    return (
        <div
            className={`animate-fadeIn ${className}`}
            style={{ animationDelay: `${delay}ms` }}
        >
            {children}
        </div>
    );
};
