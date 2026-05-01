import React from 'react';
import { X, AlertCircle, Mail, Shield } from 'lucide-react';
import { ThreatDetail } from '../services/dashboardAnalytics';

interface DrillDownModalProps {
    date: string;
    threats: ThreatDetail[];
    totalThreats: number;
    onClose: () => void;
}

export const DrillDownModal: React.FC<DrillDownModalProps> = ({
    date,
    threats,
    totalThreats,
    onClose,
}) => {
    const getSeverityColor = (score: number) => {
        if (score >= 75) return 'text-red-400 bg-red-500/10 border-red-500/30';
        if (score >= 50) return 'text-orange-400 bg-orange-500/10 border-orange-500/30';
        if (score >= 25) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
        return 'text-green-400 bg-green-500/10 border-green-500/30';
    };

    const getSeverityLabel = (score: number) => {
        if (score >= 75) return 'Критический';
        if (score >= 50) return 'Высокий';
        if (score >= 25) return 'Средний';
        return 'Низкий';
    };

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-lg border border-slate-700 max-w-4xl w-full max-h-[80vh] overflow-hidden shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-700">
                    <div>
                        <h2 className="text-2xl font-semibold text-white flex items-center gap-2">
                            <AlertCircle className="w-6 h-6 text-red-400" />
                            Детали угроз
                        </h2>
                        <p className="text-sm text-slate-400 mt-1">
                            {date} • Всего угроз: {totalThreats}
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-slate-400" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto max-h-[calc(80vh-100px)]">
                    <div className="space-y-3">
                        {threats.map((threat) => (
                            <div
                                key={threat.id}
                                className="bg-slate-700/50 rounded-lg border border-slate-600 p-4 hover:bg-slate-700 transition-colors"
                            >
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex-1 min-w-0">
                                        {/* Subject */}
                                        <div className="flex items-center gap-2 mb-2">
                                            <Mail className="w-4 h-4 text-slate-400 flex-shrink-0" />
                                            <p className="text-white font-medium truncate">
                                                {threat.subject || 'Без темы'}
                                            </p>
                                        </div>

                                        {/* From/To */}
                                        <div className="grid grid-cols-2 gap-4 text-sm">
                                            <div>
                                                <span className="text-slate-400">От:</span>{' '}
                                                <span className="text-slate-200">{threat.from_address}</span>
                                            </div>
                                            <div>
                                                <span className="text-slate-400">Кому:</span>{' '}
                                                <span className="text-slate-200">{threat.to_address}</span>
                                            </div>
                                        </div>

                                        {/* Status & Decision */}
                                        <div className="flex items-center gap-3 mt-3">
                                            <span className="text-xs px-2 py-1 rounded bg-slate-600 text-slate-300">
                                                {threat.status}
                                            </span>
                                            <span className="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                                                {threat.decision}
                                            </span>
                                            <span className="text-xs text-slate-400">
                                                {new Date(threat.analyzed_at).toLocaleString('ru-RU')}
                                            </span>
                                        </div>
                                    </div>

                                    <div className={`flex flex-col items-center gap-1 px-4 py-2 rounded-lg border ${getSeverityColor(threat.risk_score)}`}>
                                        <Shield className="w-5 h-5" />
                                        <span className="text-2xl font-bold">{threat.risk_score.toFixed(0)}</span>
                                        <span className="text-xs">{getSeverityLabel(threat.risk_score)}</span>
                                    </div>
                                </div>

                                {/* Analysis Explanations */}
                                {threat.analysis_details && (
                                    <div className="mt-4 pt-4 border-t border-slate-600/50 grid grid-cols-2 gap-4">
                                        {/* Fallback for safe access during demo */}
                                        {threat.analysis_details.technical?.length > 0 && (
                                            <div>
                                                <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Технические детали</h4>
                                                <ul className="space-y-1">
                                                    {threat.analysis_details.technical.map((item, idx) => (
                                                        <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                                                            <span>•</span> {item}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {threat.analysis_details.linguistic?.length > 0 && (
                                            <div>
                                                <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Лингвистика</h4>
                                                <ul className="space-y-1">
                                                    {threat.analysis_details.linguistic.map((item, idx) => (
                                                        <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                                                            <span>•</span> {item}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {threat.analysis_details.contextual?.length > 0 && (
                                            <div>
                                                <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Контекст</h4>
                                                <ul className="space-y-1">
                                                    {threat.analysis_details.contextual.map((item, idx) => (
                                                        <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                                                            <span>•</span> {item}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {threat.analysis_details.behavioral?.length > 0 && (
                                            <div>
                                                <h4 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">Поведение</h4>
                                                <ul className="space-y-1">
                                                    {threat.analysis_details.behavioral.map((item, idx) => (
                                                        <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                                                            <span>•</span> {item}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    {threats.length === 0 && (
                        <div className="text-center py-12">
                            <AlertCircle className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                            <p className="text-slate-400">Нет данных за выбранную дату</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
