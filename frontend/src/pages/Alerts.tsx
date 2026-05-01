import React, { useEffect, useState } from 'react';
import { Layout } from '../components/Layout';
import { alertsApi } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { CheckCircle, Trash2, AlertTriangle, Clock, ShieldCheck, Mail, ArrowRight, Bell } from 'lucide-react';
import type { Alert } from '../types';

export const Alerts: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'open' | 'acknowledged' | 'resolved'>('all');
  const [page, setPage] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const { profile } = useAuth();

  const pageSize = 20;

  useEffect(() => {
    loadAlerts();
  }, [page, filter]);

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const { data, count } = await alertsApi.getAlerts(pageSize, page * pageSize);
      let filtered = data;

      if (filter !== 'all') {
        filtered = data.filter((alert) => alert.status === filter.toUpperCase());
      }

      setAlerts(filtered);
      setTotalCount(count);
    } catch (error) {
      console.error('Error loading alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (alertId: string) => {
    try {
      if (!profile) return;
      const updated = await alertsApi.acknowledgeAlert(alertId, profile.user_id);
      setAlerts(alerts.map((a) => (a.id === alertId ? updated : a)));
    } catch (error) {
      console.error('Error acknowledging alert:', error);
    }
  };

  const getSeverityConfig = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return { bg: 'bg-red-500/10', border: 'border-red-500/20', text: 'text-red-400', glow: 'glow-red', icon: AlertTriangle };
      case 'HIGH':
        return { bg: 'bg-orange-500/10', border: 'border-orange-500/20', text: 'text-orange-400', glow: '', icon: AlertTriangle };
      case 'MEDIUM':
        return { bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', text: 'text-yellow-400', glow: '', icon: Clock };
      default:
        return { bg: 'bg-blue-500/10', border: 'border-blue-500/20', text: 'text-blue-400', glow: '', icon: Bell };
    }
  };

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'OPEN':
        return { label: 'Открыт', color: 'bg-red-500/20 text-red-400 border-red-500/30' };
      case 'ACKNOWLEDGED':
        return { label: 'Принят', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' };
      case 'RESOLVED':
        return { label: 'Закрыт', color: 'bg-green-500/20 text-green-400 border-green-500/30' };
      default:
        return { label: status, color: 'bg-slate-500/20 text-slate-400 border-slate-500/30' };
    }
  };

  const filterConfig = [
    { key: 'all', label: 'Все', icon: Bell },
    { key: 'open', label: 'Открытые', icon: AlertTriangle },
    { key: 'acknowledged', label: 'Принятые', icon: Clock },
    { key: 'resolved', label: 'Закрытые', icon: ShieldCheck },
  ] as const;

  return (
    <Layout>
      <div className="space-y-8 pb-10">
        {/* Header */}
        <div className="animate-fadeIn">
          <div className="flex items-center gap-2 mb-2">
            <span className="h-1 w-8 bg-red-500 rounded-full" />
            <p className="text-red-400 text-xs font-black uppercase tracking-[0.2em]">Центр инцидентов</p>
          </div>
          <h1 className="text-5xl font-black text-white tracking-tighter">Алерты</h1>
          <p className="text-slate-500 mt-2 font-medium">Отслеживайте и управляйте угрозами в реальном времени</p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-3 flex-wrap animate-fadeIn" style={{ animationDelay: '0.1s' }}>
          {filterConfig.map((f) => {
            const Icon = f.icon;
            const isActive = filter === f.key;
            return (
              <button
                key={f.key}
                onClick={() => {
                  setFilter(f.key);
                  setPage(0);
                }}
                className={`flex items-center gap-2 px-5 py-3 rounded-2xl border font-bold text-sm uppercase tracking-wider transition-all duration-300 ${isActive
                    ? 'bg-blue-500/20 border-blue-500/30 text-blue-400 glow-blue'
                    : 'bg-white/[0.03] border-white/5 text-slate-500 hover:bg-white/[0.06] hover:text-white'
                  }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'scale-110' : ''} transition-transform`} />
                {f.label}
              </button>
            );
          })}
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="w-16 h-16 border-4 border-red-500/20 border-t-red-500 rounded-full animate-spin shadow-lg shadow-red-500/20" />
            <p className="text-slate-500 font-bold uppercase tracking-widest text-xs animate-pulse">Загрузка инцидентов...</p>
          </div>
        ) : alerts.length === 0 ? (
          <div className="text-center py-20 glass-card rounded-3xl border border-dashed border-white/10 animate-fadeIn">
            <ShieldCheck className="w-16 h-16 text-green-500/30 mx-auto mb-4" />
            <p className="text-slate-400 font-bold uppercase tracking-widest text-sm">Система стабильна</p>
            <p className="text-slate-600 text-xs mt-2">Активных алертов не обнаружено</p>
          </div>
        ) : (
          <div className="space-y-4 animate-fadeIn" style={{ animationDelay: '0.2s' }}>
            {alerts.map((alert, index) => {
              const severityConfig = getSeverityConfig(alert.severity);
              const statusConfig = getStatusConfig(alert.status);
              const SeverityIcon = severityConfig.icon;

              return (
                <div
                  key={alert.id}
                  className={`glass-card p-6 rounded-3xl border ${severityConfig.border} ${severityConfig.glow} transition-all duration-300 hover:translate-x-1 group`}
                  style={{ animationDelay: `${index * 0.05}s` }}
                >
                  <div className="flex items-start justify-between gap-6">
                    <div className="flex-1 min-w-0">
                      {/* Header Row */}
                      <div className="flex items-center gap-3 mb-3 flex-wrap">
                        <div className={`p-2 rounded-xl ${severityConfig.bg}`}>
                          <SeverityIcon className={`w-5 h-5 ${severityConfig.text}`} />
                        </div>
                        <h3 className="text-lg font-black text-white tracking-tight truncate">{alert.title}</h3>
                        <span className={`text-[10px] font-black px-3 py-1 rounded-lg border uppercase tracking-widest ${statusConfig.color}`}>
                          {statusConfig.label}
                        </span>
                        <span className={`text-[10px] font-black px-3 py-1 rounded-lg border uppercase tracking-widest ${severityConfig.bg} ${severityConfig.text} ${severityConfig.border}`}>
                          {alert.severity}
                        </span>
                      </div>

                      {/* Description */}
                      {alert.description && (
                        <p className="text-sm text-slate-400 mb-4 leading-relaxed">{alert.description}</p>
                      )}

                      {/* Email Details */}
                      <div className="flex items-center gap-6 text-sm flex-wrap">
                        <div className="flex items-center gap-2">
                          <Mail className="w-4 h-4 text-slate-600" />
                          <span className="text-slate-500 font-medium">От:</span>
                          <span className="font-mono text-slate-300 text-xs bg-white/5 px-2 py-1 rounded-lg">{alert.sender_email}</span>
                        </div>
                        <ArrowRight className="w-4 h-4 text-slate-700 hidden sm:block" />
                        <div className="flex items-center gap-2">
                          <span className="text-slate-500 font-medium">Кому:</span>
                          <span className="font-mono text-slate-300 text-xs bg-white/5 px-2 py-1 rounded-lg">{alert.recipient_email}</span>
                        </div>
                      </div>

                      {/* Timestamp */}
                      <div className="mt-4 flex items-center gap-2 text-[10px] text-slate-600 uppercase tracking-widest font-bold">
                        <Clock className="w-3 h-3" />
                        {new Date(alert.created_at).toLocaleString()}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 flex-shrink-0 opacity-50 group-hover:opacity-100 transition-opacity">
                      {alert.status === 'OPEN' && (
                        <button
                          onClick={() => handleAcknowledge(alert.id)}
                          className="p-3 bg-green-500/10 hover:bg-green-500/20 border border-green-500/20 rounded-xl transition-all text-green-400"
                          title="Принять"
                        >
                          <CheckCircle className="w-5 h-5" />
                        </button>
                      )}
                      <button
                        onClick={() => console.log('Delete:', alert.id)}
                        className="p-3 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-xl transition-all text-red-400"
                        title="Удалить"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination */}
        {totalCount > pageSize && (
          <div className="flex items-center justify-center gap-4 mt-10 animate-fadeIn">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="px-6 py-3 glass border border-white/5 hover:border-white/10 rounded-2xl font-bold text-sm uppercase tracking-widest transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            >
              ← Назад
            </button>
            <div className="px-6 py-3 text-slate-500 font-bold text-sm">
              <span className="text-white">{page + 1}</span> / {Math.ceil(totalCount / pageSize)}
            </div>
            <button
              onClick={() => setPage(Math.min(Math.ceil(totalCount / pageSize) - 1, page + 1))}
              disabled={page >= Math.ceil(totalCount / pageSize) - 1}
              className="px-6 py-3 glass border border-white/5 hover:border-white/10 rounded-2xl font-bold text-sm uppercase tracking-widest transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Далее →
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
};
