import React, { useEffect, useState } from 'react';
import { Wifi, WifiOff, Server, Mail, RefreshCw, Play, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { systemApi, ServiceStatus } from '../services/api';

export const SystemStatusWidget: React.FC = () => {
    const [services, setServices] = useState<ServiceStatus[]>([]);
    const [loading, setLoading] = useState(true);
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message?: string; error?: string; details?: any } | null>(null);

    const fetchStatus = async () => {
        try {
            const data = await systemApi.getSystemStatus();
            setServices(data);
            setLastUpdate(new Date());
        } catch (error) {
            console.error('Failed to fetch system status:', error);
        } finally {
            setLoading(false);
        }
    };

    const testImapConnection = async () => {
        setTesting(true);
        setTestResult(null);
        try {
            const result = await systemApi.testImap();
            setTestResult(result);
        } catch (error: any) {
            setTestResult({ success: false, error: error.message || 'Connection failed' });
        } finally {
            setTesting(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 30000);
        return () => clearInterval(interval);
    }, []);

    const getServiceIcon = (name: string) => {
        if (name.includes('imap') || name.includes('smtp')) {
            return <Mail className="w-4 h-4" />;
        }
        return <Server className="w-4 h-4" />;
    };

    const getServiceLabel = (name: string) => {
        if (name === 'celery-imap-sync') return 'IMAP Синхронизация (Celery)';
        if (name === 'imap-listener') return 'IMAP (Входящие)';
        if (name === 'smtp-listener') return 'SMTP (Копии)';
        return name;
    };

    if (loading) {
        return (
            <div className="glass-card rounded-2xl p-4 animate-pulse">
                <div className="h-4 bg-white/10 rounded w-1/2 mb-3"></div>
                <div className="h-8 bg-white/5 rounded"></div>
            </div>
        );
    }

    return (
        <div className="glass-card rounded-2xl p-5 border border-white/5">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Server className="w-5 h-5 text-blue-400" />
                    <h3 className="font-bold text-white text-sm uppercase tracking-wider">Статус сервисов</h3>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={testImapConnection}
                        disabled={testing}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors text-xs font-bold disabled:opacity-50"
                        title="Проверить IMAP подключение"
                    >
                        {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                        Тест IMAP
                    </button>
                    <button
                        onClick={fetchStatus}
                        className="p-1.5 rounded-lg hover:bg-white/10 transition-colors text-slate-400 hover:text-white"
                        title="Обновить"
                    >
                        <RefreshCw className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Test Result */}
            {testResult && (
                <div className={`mb-4 p-3 rounded-xl border ${testResult.success ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                    <div className="flex items-start gap-2">
                        {testResult.success ? (
                            <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
                        ) : (
                            <XCircle className="w-5 h-5 text-red-400 shrink-0" />
                        )}
                        <div>
                            <p className={`font-bold text-sm ${testResult.success ? 'text-emerald-400' : 'text-red-400'}`}>
                                {testResult.success ? testResult.message : testResult.error}
                            </p>
                            {testResult.details && (
                                <div className="mt-2 text-xs text-slate-400 space-y-1">
                                    <p>Host: {testResult.details.host}</p>
                                    <p>User: {testResult.details.user}</p>
                                    {testResult.details.total_emails !== undefined && (
                                        <>
                                            <p>Всего писем: {testResult.details.total_emails}</p>
                                            <p>Непрочитанных: {testResult.details.unseen_emails}</p>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            <div className="space-y-3">
                {services.map((service) => (
                    <div
                        key={service.service_name}
                        className={`flex items-center justify-between p-3 rounded-xl border transition-all ${service.is_healthy
                            ? 'bg-emerald-500/10 border-emerald-500/20'
                            : 'bg-red-500/10 border-red-500/20'
                            }`}
                    >
                        <div className="flex items-center gap-3">
                            <div className={`p-2 rounded-lg ${service.is_healthy ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                                {getServiceIcon(service.service_name)}
                            </div>
                            <div>
                                <p className="font-bold text-sm text-white">{getServiceLabel(service.service_name)}</p>
                                {service.details?.user && (
                                    <p className="text-xs text-slate-400 truncate max-w-[150px]">{service.details.user}</p>
                                )}
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            {service.is_healthy ? (
                                <div className="flex items-center gap-1.5 text-emerald-400">
                                    <Wifi className="w-4 h-4" />
                                    <span className="text-xs font-bold uppercase">Online</span>
                                </div>
                            ) : (
                                <div className="flex items-center gap-1.5 text-red-400">
                                    <WifiOff className="w-4 h-4" />
                                    <span className="text-xs font-bold uppercase">Offline</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {services.length === 0 && (
                    <div className="text-center py-4 text-slate-500 text-sm">
                        Нет данных о сервисах
                    </div>
                )}
            </div>

            {lastUpdate && (
                <p className="text-xs text-slate-600 mt-3 text-right">
                    Обновлено: {lastUpdate.toLocaleTimeString()}
                </p>
            )}
        </div>
    );
};
