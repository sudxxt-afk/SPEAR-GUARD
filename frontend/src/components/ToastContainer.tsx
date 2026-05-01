import React, { useEffect } from 'react';
import { useWebSocket, type AlertData } from '../contexts/WebSocketContext';

interface ToastProps {
    alert: AlertData;
    onClose: () => void;
}

const Toast: React.FC<ToastProps> = ({ alert, onClose }) => {
    useEffect(() => {
        const timer = setTimeout(() => {
            onClose();
        }, 10000); // Auto-close after 10 seconds

        return () => clearTimeout(timer);
    }, [onClose]);

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'CRITICAL':
                return 'bg-red-500';
            case 'HIGH':
                return 'bg-orange-500';
            case 'MEDIUM':
                return 'bg-yellow-500';
            case 'LOW':
                return 'bg-blue-500';
            default:
                return 'bg-gray-500';
        }
    };

    const getSeverityIcon = (severity: string) => {
        switch (severity) {
            case 'CRITICAL':
                return '🚨';
            case 'HIGH':
                return '⚠️';
            case 'MEDIUM':
                return '⚡';
            case 'LOW':
                return 'ℹ️';
            default:
                return '📢';
        }
    };

    return (
        <div className="bg-white rounded-lg shadow-2xl p-4 mb-3 border-l-4 border-red-500 animate-slide-in max-w-md">
            <div className="flex items-start">
                <div className={`flex-shrink-0 w-10 h-10 rounded-full ${getSeverityColor(alert.severity)} flex items-center justify-center text-white text-xl`}>
                    {getSeverityIcon(alert.severity)}
                </div>
                <div className="ml-3 flex-1">
                    <div className="flex items-center justify-between">
                        <p className="text-sm font-bold text-gray-900">{alert.title}</p>
                        <button
                            onClick={onClose}
                            className="ml-3 text-gray-400 hover:text-gray-600 transition-colors"
                        >
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                        </button>
                    </div>
                    {alert.message && (
                        <p className="mt-1 text-sm text-gray-600">{alert.message}</p>
                    )}
                    <div className="mt-2 text-xs text-gray-500">
                        <p>From: {alert.sender_email}</p>
                        <p>To: {alert.recipient_email}</p>
                    </div>
                    <div className="mt-2">
                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getSeverityColor(alert.severity)} text-white`}>
                            {alert.severity}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export const ToastContainer: React.FC = () => {
    const { alerts } = useWebSocket();
    const [visibleAlerts, setVisibleAlerts] = React.useState<AlertData[]>([]);

    useEffect(() => {
        // Show only the last 3 alerts
        setVisibleAlerts(alerts.slice(0, 3));
    }, [alerts]);

    const handleClose = (alertId: number) => {
        setVisibleAlerts(prev => prev.filter(a => a.id !== alertId));
    };

    if (visibleAlerts.length === 0) {
        return null;
    }

    return (
        <div className="fixed top-4 right-4 z-notifications space-y-2">
            {visibleAlerts.map(alert => (
                <Toast key={alert.id} alert={alert} onClose={() => handleClose(alert.id)} />
            ))}
        </div>
    );
};
