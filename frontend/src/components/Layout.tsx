import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { ToastContainer } from './ToastContainer';
import {
  Shield,
  BarChart3,
  AlertCircle,
  Users,
  Settings,
  LogOut,
  Menu,
  X,
  Bell,
  Search,
  Building2,
  FileText,
} from 'lucide-react';
import { alertsApi } from '../services/api';
import type { Alert } from '../types';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { signOut, profile, user } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<Alert[]>([]);
  const [notifLoading, setNotifLoading] = useState(false);

  const menuItems = [
    { icon: BarChart3, label: 'Дашборд', path: '/dashboard' },
    { icon: FileText, label: 'Анализ', path: '/analysis' },
    { icon: AlertCircle, label: 'Алерты', path: '/alerts' },
    { icon: Users, label: 'Реестр', path: '/registry' },
    ...(user?.role === 'admin' ? [{ icon: Building2, label: 'Организации', path: '/organizations' }] : []),
    { icon: Settings, label: 'Настройки', path: '/settings' },
  ];

  const isActive = (path: string) => location.pathname === path;

  const handleLogout = async () => {
    await signOut();
    navigate('/login');
  };

  useEffect(() => {
    const loadNotifications = async () => {
      setNotifLoading(true);
      try {
        const openAlerts = await alertsApi.getOpenAlerts();
        setNotifications(openAlerts.slice(0, 5));
      } catch (err) {
        console.error('Failed to load notifications', err);
      } finally {
        setNotifLoading(false);
      }
    };
    loadNotifications();
  }, []);

  const severityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
      case 'HIGH':
        return 'text-red-400';
      case 'MEDIUM':
        return 'text-yellow-300';
      default:
        return 'text-slate-200';
    }
  };

  return (
    <div className="flex h-screen bg-[#0f172a] text-white relative overflow-hidden">
      {/* Ambient Background Glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/10 rounded-full blur-[120px] animate-pulse-slow active" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-600/10 rounded-full blur-[120px] animate-pulse-slow" />

      <aside
        className={`${sidebarOpen ? 'w-64' : 'w-20'
          } glass border-r border-white/5 transition-[width] duration-300 flex flex-col z-10`}
      >
        <div className="p-6 border-b border-white/5 flex items-center justify-between">
          <div className={`flex items-center gap-3 ${!sidebarOpen && 'flex-col'}`}>
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-600/20">
              <Shield className="w-6 h-6 text-white flex-shrink-0" />
            </div>
            {sidebarOpen && <h1 className="font-bold text-lg tracking-tight">SPEAR-GUARD</h1>}
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 hover:bg-white/5 rounded-lg transition-colors text-slate-400 hover:text-white"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${active
                  ? 'bg-blue-600 shadow-lg shadow-blue-600/20 text-white'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white'
                  } ${!sidebarOpen && 'justify-center'}`}
              >
                <Icon className={`w-5 h-5 flex-shrink-0 ${active ? 'text-white' : 'group-hover:scale-110 transition-transform'}`} />
                {sidebarOpen && <span className="font-medium">{item.label}</span>}
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-white/5">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-3 text-slate-400 hover:bg-red-500/10 hover:text-red-400 rounded-xl transition-all duration-200"
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            {sidebarOpen && <span className="font-medium">Выйти</span>}
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col z-10">
        <header className="px-8 py-4 flex items-center justify-between bg-white/[0.02] backdrop-blur-sm border-b border-white/5 relative z-50">
          <div className="flex-1 flex items-center gap-4">
            <div className="relative flex-1 max-w-md group">
              <input
                type="text"
                placeholder="Поиск по системе (CMD+K)..."
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 pl-10 text-sm focus:outline-none focus:border-blue-500/50 focus:bg-white/10 transition-all"
              />
              <Search className="absolute left-3 top-3 w-4 h-4 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="relative">
              <button
                className="relative p-2.5 hover:bg-white/5 rounded-xl transition-all text-slate-400 hover:text-white"
                onClick={() => setNotifOpen((v) => !v)}
              >
                <Bell className="w-5 h-5" />
                {notifications.length > 0 && (
                  <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                )}
              </button>
              {notifOpen && (
                <div
                  className="absolute right-0 mt-3 w-80 glass-card rounded-2xl shadow-2xl z-notifications origin-top-right animate-fadeIn overflow-hidden"
                >
                  <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between bg-white/[0.05]">
                    <span className="font-bold text-sm">Уведомления</span>
                    <button
                      className="text-xs text-blue-400 hover:text-blue-300 font-medium"
                      onClick={() => {
                        setNotifOpen(false);
                        navigate('/alerts');
                      }}
                    >
                      Открыть все
                    </button>
                  </div>
                  <div className="max-h-[400px] overflow-auto custom-scrollbar">
                    {notifLoading ? (
                      <div className="p-8 text-center">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-400 mx-auto" />
                      </div>
                    ) : notifications.length === 0 ? (
                      <div className="p-10 text-center">
                        <Bell className="w-8 h-8 text-slate-600 mx-auto mb-2 opacity-20" />
                        <p className="text-sm text-slate-500">Уведомлений пока нет</p>
                      </div>
                    ) : (
                      notifications.map((alert) => (
                        <div
                          key={alert.id}
                          className="p-4 border-b border-white/5 hover:bg-white/[0.03] cursor-pointer transition-colors"
                          onClick={() => {
                            setNotifOpen(false);
                            navigate('/alerts');
                          }}
                        >
                          <div className="flex items-center justify-between text-[10px] uppercase tracking-wider mb-1">
                            <span className={`font-bold ${severityColor(alert.severity)}`}>
                              {alert.severity}
                            </span>
                            <span className="text-slate-500 font-medium">{new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                          <div className="text-sm font-semibold truncate text-slate-200">{alert.title}</div>
                          <div className="text-xs text-slate-500 mt-0.5 truncate italic">
                            {alert.sender_email}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center gap-3 pl-6 border-l border-white/10">
              <div className="text-right">
                <div className="text-sm font-bold text-slate-200 leading-tight">{profile?.full_name || 'Admin'}</div>
                <div className="text-[10px] text-blue-400/80 uppercase tracking-widest font-bold mt-0.5">{profile?.job_role || 'Security Officer'}</div>
              </div>
              <div className="relative group">
                <div className="absolute -inset-0.5 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full blur opacity-30 group-hover:opacity-60 transition duration-300" />
                <div className="relative w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center border border-white/10 overflow-hidden ring-2 ring-transparent group-hover:ring-blue-500/30 transition-all">
                  {profile?.avatar_url ? (
                    <img
                      src={profile.avatar_url}
                      alt="Avatar"
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <span className="text-sm font-black text-blue-400">
                      {(profile?.full_name || 'S')[0].toUpperCase()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto custom-scrollbar relative">
          <div className="absolute top-0 left-0 w-full h-full pointer-events-none opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(#fff 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
          <div className="relative p-8 max-w-[1600px] mx-auto w-full">{children}</div>
        </main>
        <ToastContainer />
      </div>
    </div>
  );
};
