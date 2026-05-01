import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  BarChart3,
  AlertCircle,
  Shield,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { Layout } from '../components/Layout';
import { ThreatTrendChart } from '../components/ThreatTrendChart';
import { AttackMap } from '../components/AttackMap';
import { ActivityHeatmap } from '../components/ActivityHeatmap';
import { RiskScoreTimeline } from '../components/RiskScoreTimeline';
import { SystemStatusWidget } from '../components/SystemStatusWidget';
import { useWebSocket } from '../contexts/WebSocketContext';
import {
  getDashboardStats,
  analysisApi,
  alertsApi,
  senderProfileApi,
} from '../services/api';
import { dashboardAnalyticsApi, ThreatDetail } from '../services/dashboardAnalytics';
import { DrillDownModal } from '../components/DrillDownModal';
import type { EmailAnalysis, Alert, SenderProfile, DashboardStats } from '../types';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { isConnected } = useWebSocket();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentAnalysis, setRecentAnalysis] = useState<EmailAnalysis[]>([]);
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([]);
  const [suspiciousSenders, setSuspiciousSenders] = useState<SenderProfile[]>([]);
  const [loading, setLoading] = useState(true);

  const [drillDownData, setDrillDownData] = useState<{ date: string; threats: ThreatDetail[]; total_threats: number } | null>(null);

  const handleDateClick = async (date: string) => {
    try {
      // Date now comes as "YYYY-MM-DD" from full_date
      const data = await dashboardAnalyticsApi.getThreatDetails(date);
      setDrillDownData(data);
    } catch (error) {
      console.error('Error fetching threat details:', error);
    }
  };

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        const [dashboardStats, analysisData, alertsData, sendersData] = await Promise.all([
          getDashboardStats(),
          analysisApi.getAnalysis(5, 0),
          alertsApi.getOpenAlerts(),
          senderProfileApi.getSuspiciousSenders(),
        ]);

        setStats(dashboardStats);
        setRecentAnalysis(analysisData?.data || []);
        setRecentAlerts((alertsData || []).slice(0, 5));
        setSuspiciousSenders((sendersData || []).slice(0, 5));
      } catch (error) {
        console.error('Error loading dashboard:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  // Real-time updates handler
  const { lastMessage } = useWebSocket();

  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === 'email_analysis' && lastMessage.data) {
      const newAnalysis = lastMessage.data as EmailAnalysis;
      setRecentAnalysis(prev => [newAnalysis, ...prev].slice(0, 5));

      // Update stats
      setStats(prev => prev ? ({
        ...prev,
        totalEmails: prev.totalEmails + 1,
        suspiciousEmails: newAnalysis.risk_score > 50 ? prev.suspiciousEmails + 1 : prev.suspiciousEmails,
        lastAnalysis: new Date().toISOString()
      }) : null);
    }

    if (lastMessage.type === 'alert' && lastMessage.data) {
      const newAlert = lastMessage.data as Alert;
      setRecentAlerts(prev => [newAlert, ...prev].slice(0, 5));
      setStats(prev => prev ? ({
        ...prev,
        alertsOpen: prev.alertsOpen + 1
      }) : null);
    }
  }, [lastMessage]);

  const StatCard: React.FC<{
    title: string;
    value: number | string;
    icon: React.ReactNode;
    trend?: number;
    color: 'blue' | 'red' | 'yellow' | 'green';
  }> = ({ title, value, icon, trend, color }) => {
    const colorMap = {
      blue: 'text-blue-400 bg-blue-500/10 glow-blue',
      red: 'text-red-400 bg-red-500/10 glow-red',
      yellow: 'text-yellow-400 bg-yellow-500/10 glow-yellow',
      green: 'text-green-400 bg-green-500/10 glow-green',
    };

    return (
      <div className={`glass-card p-6 rounded-2xl group transition-all duration-300 hover:translate-y-[-4px] animate-fadeIn`}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-slate-500 text-xs font-bold uppercase tracking-widest leading-none mb-3">{title}</p>
            <p className="text-4xl font-black text-white tracking-tight">{value}</p>
            {trend !== undefined && (
              <div className="flex items-center gap-1.5 mt-4">
                <div className={`flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-bold ${trend >= 0 ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}>
                  {trend >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                  {Math.abs(trend)}%
                </div>
                <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">vs неделя</span>
              </div>
            )}
          </div>
          <div className={`p-4 rounded-xl ${colorMap[color]} transition-transform group-hover:scale-110 duration-300`}>
            {React.cloneElement(icon as React.ReactElement, { className: 'w-6 h-6' })}
          </div>
        </div>
      </div>
    );
  };

  const RiskBadge: React.FC<{ score: number }> = ({ score }) => {
    let colorClass = 'text-green-400 bg-green-500/10 border-green-500/20';
    if (score >= 75) colorClass = 'text-red-400 bg-red-500/10 border-red-500/20';
    else if (score >= 50) colorClass = 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20';
    else if (score >= 25) colorClass = 'text-orange-400 bg-orange-500/10 border-orange-500/20';

    return (
      <div className={`px-2.5 py-1 rounded-lg text-xs font-black border tracking-wider ${colorClass}`}>
        {score.toFixed(0)}
      </div>
    );
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
          <div className="w-16 h-16 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin shadow-lg shadow-blue-500/20" />
          <p className="text-slate-500 font-bold uppercase tracking-widest text-xs animate-pulse">Инициализация систем...</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-10 pb-10">
        <div className="flex items-end justify-between animate-fadeIn">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="h-1 w-8 bg-blue-500 rounded-full" />
              <p className="text-blue-400 text-xs font-black uppercase tracking-[0.2em]">Система мониторинга</p>
            </div>
            <h1 className="text-5xl font-black text-white tracking-tighter">Дашборд</h1>
          </div>
          <div className={`flex items-center gap-3 px-4 py-2 rounded-2xl glass border border-white/5 transition-all ${isConnected ? 'glow-green' : ''}`}>
            {isConnected ? (
              <>
                <div className="w-2 h-2 bg-green-500 rounded-full animate-ping" />
                <span className="text-xs font-bold text-green-400 uppercase tracking-widest">Online</span>
              </>
            ) : (
              <>
                <div className="w-2 h-2 bg-slate-500 rounded-full" />
                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Offline</span>
              </>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Всего писем"
            value={stats?.totalEmails || 0}
            icon={<BarChart3 />}
            color="blue"
          />
          <StatCard
            title="Выявлено угроз"
            value={stats?.suspiciousEmails || 0}
            icon={<AlertCircle />}
            color="red"
            trend={12}
          />
          <StatCard
            title="Активные алерты"
            value={stats?.alertsOpen || 0}
            icon={<Shield />}
            color="yellow"
          />
          <StatCard
            title="База доверия"
            value={stats?.registrySize || 0}
            icon={<TrendingUp />}
            color="green"
          />
        </div>

        {/* System Status Widget */}
        <div className="mb-8 animate-fadeIn">
          <SystemStatusWidget />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 glass-card rounded-3xl p-8 animate-fadeIn" style={{ animationDelay: '0.1s' }}>
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-2xl font-black text-white tracking-tight">Последние анализы</h2>
              <Link to="/analysis" className="text-xs font-bold text-blue-400 uppercase tracking-widest hover:text-blue-300 transition-colors">Смотреть все →</Link>
            </div>
            <div className="space-y-4">
              {recentAnalysis.length === 0 ? (
                <div className="text-center py-20 bg-white/[0.02] rounded-3xl border border-dashed border-white/10">
                  <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">Данные отсутствуют</p>
                </div>
              ) : (
                recentAnalysis.map((analysis) => (
                  <div
                    key={analysis.id}
                    onClick={() => navigate(`/analysis/${analysis.id}`)}
                    className="group p-5 bg-white/[0.03] hover:bg-white/[0.06] rounded-2xl border border-white/5 hover:border-blue-500/30 cursor-pointer transition-all duration-300"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0 pr-4">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500/50" />
                          <p className="font-bold text-slate-100 truncate text-base tracking-tight group-hover:text-white transition-colors">
                            {analysis.subject || 'Без темы'}
                          </p>
                        </div>
                        <p className="text-sm font-medium text-slate-500 truncate pl-3.5">
                          {analysis.sender_email}
                        </p>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right hidden sm:block">
                          <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-1">Вердикт</p>
                          <span
                            className={`text-[10px] font-black px-2 py-0.5 rounded-md uppercase tracking-wider ${analysis.decision === 'DELIVER'
                              ? 'bg-green-500/10 text-green-500'
                              : analysis.decision === 'QUARANTINE'
                                ? 'bg-yellow-500/10 text-yellow-500'
                                : analysis.decision === 'BLOCK'
                                  ? 'bg-red-500/10 text-red-500'
                                  : 'bg-slate-500/10 text-slate-500'
                              }`}
                          >
                            {analysis.decision}
                          </span>
                        </div>
                        <RiskBadge score={analysis.risk_score} />
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="space-y-8 animate-fadeIn" style={{ animationDelay: '0.2s' }}>
            <div className="glass-card rounded-3xl p-8">
              <h2 className="text-2xl font-black text-white tracking-tight mb-6">Алерты</h2>
              <div className="space-y-4">
                {recentAlerts.length === 0 ? (
                  <p className="text-slate-600 text-center py-10 font-bold uppercase tracking-widest text-[10px]">Система стабильна</p>
                ) : (
                  recentAlerts.map((alert) => (
                    <div
                      key={alert.id}
                      className={`p-4 rounded-2xl border transition-all hover:scale-[1.02] ${alert.severity === 'CRITICAL'
                        ? 'bg-red-500/10 border-red-500/20 text-red-100 glow-red'
                        : alert.severity === 'HIGH'
                          ? 'bg-orange-500/10 border-orange-500/20 text-orange-100'
                          : alert.severity === 'MEDIUM'
                            ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-100'
                            : 'bg-blue-500/10 border-blue-500/20 text-blue-100'
                        }`}
                    >
                      <p className="font-black text-sm uppercase tracking-tight">{alert.title}</p>
                      <p className="text-xs opacity-60 mt-1 font-medium leading-relaxed">{alert.description}</p>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="glass-card rounded-3xl p-8">
              <h2 className="text-2xl font-black text-white tracking-tight mb-6">Источники риска</h2>
              <div className="space-y-4">
                {suspiciousSenders.length === 0 ? (
                  <p className="text-slate-600 text-center py-10 font-bold uppercase tracking-widest text-[10px]">Угроз не обнаружено</p>
                ) : (
                  suspiciousSenders.map((sender) => (
                    <div key={sender.id} className="p-4 bg-white/[0.03] hover:bg-white/[0.06] rounded-2xl border border-white/5 transition-all group">
                      <p className="text-sm font-bold text-slate-300 truncate group-hover:text-white transition-colors">{sender.email_address}</p>
                      <div className="flex items-center justify-between mt-3">
                        <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">{sender.email_count} писем</span>
                        <RiskBadge score={sender.risk_score} />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Visualization Components */}
        <div className="space-y-10 animate-fadeIn" style={{ animationDelay: '0.3s' }}>
          <ThreatTrendChart onDateClick={handleDateClick} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <AttackMap />
            <ActivityHeatmap />
          </div>

          <RiskScoreTimeline />
        </div>

        {/* Drill-down Modal */}
        {drillDownData && (
          <DrillDownModal
            date={drillDownData.date}
            threats={drillDownData.threats}
            totalThreats={drillDownData.total_threats}
            onClose={() => setDrillDownData(null)}
          />
        )}
      </div>
    </Layout>
  );
};
