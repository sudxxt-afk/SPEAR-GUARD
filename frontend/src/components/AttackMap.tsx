import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { ExportButton } from './ExportButton';
import { LoadingSkeleton } from './LoadingSkeleton';
import { dashboardAnalyticsApi, AttackPoint } from '../services/dashboardAnalytics';
import { Globe, Zap, MapPin } from 'lucide-react';
import { useWebSocket } from '../contexts/WebSocketContext';

const MapBoundsAdjuster = ({ attacks }: { attacks: AttackPoint[] }) => {
    const map = useMap();

    useEffect(() => {
        if (attacks.length > 0) {
            const bounds = attacks.map((a) => [a.lat, a.lng] as [number, number]);
            map.fitBounds(bounds, { padding: [50, 50] });
        }
    }, [attacks, map]);

    return null;
};

const getSeverityConfig = (severity: string) => {
    switch (severity) {
        case 'CRITICAL':
            return { color: '#ef4444', label: 'Критический', glow: '0 0 20px rgba(239,68,68,0.5)' };
        case 'HIGH':
            return { color: '#f97316', label: 'Высокий', glow: '0 0 15px rgba(249,115,22,0.4)' };
        case 'MEDIUM':
            return { color: '#eab308', label: 'Средний', glow: '0 0 10px rgba(234,179,8,0.3)' };
        case 'LOW':
            return { color: '#3b82f6', label: 'Низкий', glow: 'none' };
        default:
            return { color: '#64748b', label: severity, glow: 'none' };
    }
};

export const AttackMap: React.FC = () => {
    const [attacks, setAttacks] = useState<AttackPoint[]>([]);
    const [loading, setLoading] = useState(true);
    const { lastMessage } = useWebSocket();

    useEffect(() => {
        loadData();
        const interval = setInterval(loadData, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

    // React to real-time events
    useEffect(() => {
        if (lastMessage && (lastMessage.type === 'threat_alert' || lastMessage.type === 'alert')) {
            // If we had coordinates in the message we could append smoothly
            // For now, we refresh the map data to catch the new point
            console.log('Refreshing Attack Map due to new threat/alert');
            loadData();
        }
    }, [lastMessage]);

    const loadData = async () => {
        try {
            const result = await dashboardAnalyticsApi.getAttackMap();
            setAttacks(result);
        } catch (error) {
            console.error('Error loading attack map:', error);
        } finally {
            setLoading(false);
        }
    };

    // Stats
    const totalAttacks = attacks.reduce((sum, a) => sum + a.count, 0);
    const criticalCount = attacks.filter(a => a.severity === 'CRITICAL').length;

    if (loading) {
        return <LoadingSkeleton height={450} />;
    }

    return (
        <div id="attack-map-container" className="glass-card rounded-3xl p-8 flex flex-col h-[450px]">
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-indigo-500/10 rounded-2xl">
                        <Globe className="w-6 h-6 text-indigo-400" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-black text-white tracking-tight">География атак</h2>
                        <div className="flex items-center gap-2">
                            <p className="text-sm text-slate-500 font-medium mt-0.5">
                                Последние 24 часа
                            </p>
                            <span className="flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-green-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                            </span>
                        </div>
                    </div>
                </div>
                <ExportButton elementId="attack-map-container" filename="attack-map" />
            </div>

            {/* Stats Row */}
            <div className="flex items-center gap-4 mb-4">
                <div className="flex items-center gap-2 px-4 py-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
                    <Zap className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider">{totalAttacks} атак</span>
                </div>
                {criticalCount > 0 && (
                    <div className="flex items-center gap-2 px-4 py-2 bg-red-500/10 border border-red-500/20 rounded-xl glow-red">
                        <MapPin className="w-4 h-4 text-red-400" />
                        <span className="text-xs font-bold text-red-400 uppercase tracking-wider">{criticalCount} критических</span>
                    </div>
                )}
            </div>

            {/* Map */}
            <div className="flex-1 rounded-2xl overflow-hidden border border-white/10 relative z-0">
                <MapContainer
                    center={[20, 0]}
                    zoom={2}
                    scrollWheelZoom={false}
                    style={{ height: '100%', width: '100%', background: '#0f172a' }}
                >
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    />
                    {attacks.map((attack) => {
                        const config = getSeverityConfig(attack.severity);
                        return (
                            <CircleMarker
                                key={attack.id}
                                center={[attack.lat, attack.lng]}
                                radius={10 + Math.min(attack.count, 20)}
                                fillColor={config.color}
                                color={config.color}
                                weight={2}
                                opacity={0.9}
                                fillOpacity={0.4}
                            >
                                <Popup className="dark-popup">
                                    <div className="bg-slate-800 text-white p-3 rounded-xl min-w-[160px] -m-3">
                                        <p className="font-black text-sm border-b border-white/10 pb-2 mb-2">
                                            {attack.city}, {attack.country}
                                        </p>
                                        <div className="space-y-1 text-xs">
                                            <div className="flex justify-between">
                                                <span className="text-slate-400">Уровень:</span>
                                                <span className="font-bold" style={{ color: config.color }}>{config.label}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-slate-400">Количество:</span>
                                                <span className="font-bold text-white">{attack.count}</span>
                                            </div>
                                        </div>
                                        <p className="text-[10px] text-slate-500 mt-2 pt-2 border-t border-white/10">
                                            {new Date(attack.timestamp).toLocaleString('ru-RU')}
                                        </p>
                                    </div>
                                </Popup>
                            </CircleMarker>
                        );
                    })}
                    <MapBoundsAdjuster attacks={attacks} />
                </MapContainer>
            </div>
        </div>
    );
};
