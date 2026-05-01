import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { AuthContext } from './AuthContext';

// WebSocket message types
export interface WebSocketMessage {
    type: 'connection_established' | 'alert' | 'email_analysis' | 'registry_update' | 'threat_alert' | 'system_status' | 'ping' | 'analysis_log';
    data?: any;
    timestamp: string;
    message?: string;
    user_id?: number;
}

export interface AlertData {
    id: number;
    type: string;
    severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    title: string;
    message?: string;
    sender_email: string;
    recipient_email: string;
    created_at: string;
}

export interface EmailAnalysisData {
    message_id: string;
    from_address: string;
    to_address: string;
    subject: string;
    risk_score: number;
    status: string;
    in_registry: boolean;
    analyzed_at: string;
}

export interface RegistryUpdateData {
    action: 'added' | 'updated' | 'removed' | 'approved';
    email_address: string;
    trust_level?: number;
    status?: string;
    timestamp: string;
}

interface WebSocketContextType {
    isConnected: boolean;
    lastMessage: WebSocketMessage | null;
    alerts: AlertData[];
    sendMessage: (message: any) => void;
    clearAlerts: () => void;
    connectionError: string | null;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
    children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
    const authContext = useContext(AuthContext);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<number | null>(null);
    const reconnectDelayRef = useRef(1000); // Start with 1 second
    const maxReconnectDelay = 30000; // Max 30 seconds

    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
    const [alerts, setAlerts] = useState<AlertData[]>([]);
    const [connectionError, setConnectionError] = useState<string | null>(null);

    const connect = useCallback(() => {
        if (!authContext?.user) {
            console.log('WebSocket: No authenticated user, skipping connection');
            return;
        }

        // Get token from localStorage
        const token = localStorage.getItem('spear_guard_token');
        if (!token) {
            console.log('WebSocket: No token found, skipping connection');
            return;
        }

        const userId = authContext.user.id;
        const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
        const fullUrl = `${wsUrl}/ws/${userId}?token=${token}&client_type=dashboard`;

        console.log('WebSocket: Connecting to', fullUrl);

        try {
            const ws = new WebSocket(fullUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('✓ WebSocket connected');
                setIsConnected(true);
                setConnectionError(null);
                reconnectDelayRef.current = 1000; // Reset delay on successful connection
            };

            ws.onmessage = (event) => {
                try {
                    const data: WebSocketMessage = JSON.parse(event.data);
                    console.log('WebSocket message received:', data.type);

                    setLastMessage(data);

                    // Handle different message types
                    switch (data.type) {
                        case 'alert':
                            if (data.data) {
                                setAlerts(prev => [data.data as AlertData, ...prev].slice(0, 50)); // Keep last 50 alerts
                            }
                            break;

                        case 'ping':
                            // Respond to heartbeat
                            ws.send(JSON.stringify({ type: 'pong' }));
                            break;

                        case 'connection_established':
                            console.log('WebSocket: Connection confirmed');
                            break;

                        default:
                            console.log('WebSocket: Unknown message type:', data.type);
                    }
                } catch (error) {
                    console.error('WebSocket: Error parsing message:', error);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                setConnectionError('WebSocket connection error');
            };

            ws.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                setIsConnected(false);
                wsRef.current = null;

                // Attempt to reconnect if user is still authenticated
                if (authContext?.user) {
                    const delay = reconnectDelayRef.current;
                    console.log(`WebSocket: Reconnecting in ${delay}ms...`);

                    reconnectTimeoutRef.current = setTimeout(() => {
                        connect();
                    }, delay);

                    // Exponential backoff
                    reconnectDelayRef.current = Math.min(
                        reconnectDelayRef.current * 2,
                        maxReconnectDelay
                    );
                }
            };

        } catch (error) {
            console.error('WebSocket: Connection failed:', error);
            setConnectionError('Failed to connect to WebSocket');
        }
    }, [authContext?.user]);

    const disconnect = useCallback(() => {
        console.log('WebSocket: Disconnecting...');

        // Clear reconnect timeout
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        // Close WebSocket
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }

        setIsConnected(false);
    }, []);

    const sendMessage = useCallback((message: any) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
            console.log('WebSocket: Message sent:', message);
        } else {
            console.warn('WebSocket: Cannot send message, not connected');
        }
    }, []);

    const clearAlerts = useCallback(() => {
        setAlerts([]);
    }, []);

    // Connect when user logs in
    useEffect(() => {
        if (authContext?.user) {
            connect();
        } else {
            disconnect();
        }

        // Cleanup on unmount
        return () => {
            disconnect();
        };
    }, [authContext?.user, connect, disconnect]);

    return (
        <WebSocketContext.Provider
            value={{
                isConnected,
                lastMessage,
                alerts,
                sendMessage,
                clearAlerts,
                connectionError,
            }}
        >
            {children}
        </WebSocketContext.Provider>
    );
};

// Custom hook to use WebSocket context
export const useWebSocket = () => {
    const context = useContext(WebSocketContext);
    if (context === undefined) {
        throw new Error('useWebSocket must be used within a WebSocketProvider');
    }
    return context;
};
