import React, { useState, useEffect } from 'react';
import { forensicApi, ForensicTimeline, ForensicTimelineItem } from '../services/api';
import { Shield, AlertTriangle, Search, Download, Users, Clock, TrendingUp, Activity } from 'lucide-react';

interface ForensicTimelineProps {
  senderEmail: string;
  onSelectEmail?: (emailId: number) => void;
}

export const ForensicTimelineComponent: React.FC<ForensicTimelineProps> = ({ 
  senderEmail, 
  onSelectEmail 
}) => {
  const [timeline, setTimeline] = useState<ForensicTimeline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'high' | 'medium' | 'safe'>('all');

  useEffect(() => {
    loadTimeline();
  }, [senderEmail]);

  const loadTimeline = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await forensicApi.getSenderTimeline(senderEmail, 365);
      setTimeline(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load timeline');
    } finally {
      setLoading(false);
    }
  };

  const getFilteredEmails = () => {
    if (!timeline) return [];
    switch (selectedFilter) {
      case 'high':
        return timeline.timeline.filter(e => e.risk_score >= 75);
      case 'medium':
        return timeline.timeline.filter(e => e.risk_score >= 50 && e.risk_score < 75);
      case 'safe':
        return timeline.timeline.filter(e => e.risk_score < 50);
      default:
        return timeline.timeline;
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 75) return 'text-red-500';
    if (score >= 50) return 'text-orange-500';
    return 'text-green-500';
  };

  const getRiskBg = (score: number) => {
    if (score >= 75) return 'bg-red-500/10 border-red-500/30';
    if (score >= 50) return 'bg-orange-500/10 border-orange-500/30';
    return 'bg-green-500/10 border-green-500/30';
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Unknown';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', { 
      day: 'numeric', 
      month: 'short', 
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleExport = async () => {
    try {
      const report = await forensicApi.exportReport(senderEmail, 'json', 365);
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `forensic-report-${senderEmail.replace('@', '-at-')}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500"></div>
        <span className="ml-3 text-gray-400">Загрузка timeline...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
        <div className="flex items-center gap-2 text-red-400">
          <AlertTriangle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  if (!timeline) return null;

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Activity className="w-4 h-4" />
            Всего писем
          </div>
          <div className="text-2xl font-bold text-white mt-1">{timeline.statistics.total_emails}</div>
        </div>
        
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertTriangle className="w-4 h-4" />
            Высокий риск
          </div>
          <div className="text-2xl font-bold text-red-400 mt-1">{timeline.statistics.high_risk}</div>
        </div>
        
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Users className="w-4 h-4" />
            Получателей
          </div>
          <div className="text-2xl font-bold text-white mt-1">{timeline.statistics.unique_recipients}</div>
        </div>
        
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Clock className="w-4 h-4" />
            Первый контакт
          </div>
          <div className="text-sm text-white mt-1">
            {timeline.statistics.first_seen 
              ? new Date(timeline.statistics.first_seen).toLocaleDateString('ru-RU')
              : 'N/A'}
          </div>
        </div>
      </div>

      {/* Filters & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex gap-2">
          {(['all', 'high', 'medium', 'safe'] as const).map(filter => (
            <button
              key={filter}
              onClick={() => setSelectedFilter(filter)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                selectedFilter === filter
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'bg-slate-800/50 text-gray-400 border border-slate-700 hover:bg-slate-700'
              }`}
            >
              {filter === 'all' && 'Все'}
              {filter === 'high' && 'Высокий риск'}
              {filter === 'medium' && 'Средний'}
              {filter === 'safe' && 'Безопасные'}
            </button>
          ))}
        </div>
        
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg border border-cyan-500/30 hover:bg-cyan-500/30 transition-colors"
        >
          <Download className="w-4 h-4" />
          Экспорт отчёта
        </button>
      </div>

      {/* Timeline */}
      <div className="space-y-3">
        {getFilteredEmails().map((email, index) => (
          <div
            key={email.id || index}
            onClick={() => onSelectEmail?.(email.id)}
            className={`p-4 rounded-lg border cursor-pointer transition-all hover:scale-[1.01] ${getRiskBg(email.risk_score)}`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`font-medium ${getRiskColor(email.risk_score)}`}>
                    {email.risk_score}%
                  </span>
                  <span className="text-gray-500">•</span>
                  <span className="text-gray-400 text-sm">{email.to}</span>
                  {email.in_registry && (
                    <Shield className="w-4 h-4 text-green-500" />
                  )}
                </div>
                <div className="text-white font-medium truncate">{email.subject}</div>
                <div className="text-gray-500 text-sm mt-1">
                  {email.analyzed_at && formatDate(email.analyzed_at)}
                </div>
              </div>
              
              <div className="text-right shrink-0">
                <div className={`text-xs px-2 py-1 rounded ${
                  email.status === 'danger' ? 'bg-red-500/20 text-red-400' :
                  email.status === 'warning' ? 'bg-orange-500/20 text-orange-400' :
                  'bg-green-500/20 text-green-400'
                }`}>
                  {email.status === 'danger' && 'Опасно'}
                  {email.status === 'warning' && 'Подозрительно'}
                  {email.status === 'caution' && 'Внимание'}
                  {email.status === 'safe' && 'Безопасно'}
                </div>
              </div>
            </div>
            
            {/* Score breakdown */}
            <div className="flex gap-4 mt-3 text-xs">
              <span className="text-gray-500">Тех: <span className="text-gray-300">{Math.round(email.technical_score || 0)}</span></span>
              <span className="text-gray-500">Линг: <span className="text-gray-300">{Math.round(email.linguistic_score || 0)}</span></span>
              <span className="text-gray-500">Повед: <span className="text-gray-300">{Math.round(email.behavioral_score || 0)}</span></span>
              <span className="text-gray-500">Контекст: <span className="text-gray-300">{Math.round(email.contextual_score || 0)}</span></span>
            </div>
          </div>
        ))}
        
        {getFilteredEmails().length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Писем не найдено</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ForensicTimelineComponent;