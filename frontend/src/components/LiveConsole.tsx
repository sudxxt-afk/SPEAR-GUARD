import React, { useEffect, useRef, useState } from 'react';
import { Terminal, Pause, Play, Trash2, Maximize2, Minimize2, X } from 'lucide-react';
import { useWebSocket } from '../contexts/WebSocketContext';

interface LogEntry {
    id: string;
    message: string;
    level: 'info' | 'success' | 'warning' | 'danger';
    timestamp: string;
}

interface LiveConsoleProps {
    onClose?: () => void;
}

export const LiveConsole: React.FC<LiveConsoleProps> = ({ onClose }) => {
    const { lastMessage } = useWebSocket();
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isPaused, setIsPaused] = useState(false);
    const [isExpanded, setIsExpanded] = useState(false);

    // Initial position: Center of screen (approximate, refined safely in useEffect)
    const [position, setPosition] = useState({ x: window.innerWidth / 2 - 300, y: window.innerHeight / 2 - 200 });
    const [isDragging, setIsDragging] = useState(false);
    const dragStartRef = useRef<{ x: number, y: number } | null>(null);
    const logsEndRef = useRef<HTMLDivElement>(null);
    const consoleRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Recenter on mount
        setPosition({
            x: Math.max(0, window.innerWidth / 2 - (isExpanded ? 400 : 250)),
            y: Math.max(0, window.innerHeight / 2 - (isExpanded ? 300 : 175))
        });
    }, [isExpanded]);

    useEffect(() => {
        if (!lastMessage || isPaused) return;

        if (lastMessage.type === 'analysis_log' && lastMessage.data) {
            const data = lastMessage.data;
            const newLog: LogEntry = {
                id: Math.random().toString(36).substr(2, 9),
                message: data.message,
                level: data.level || 'info',
                timestamp: data.timestamp
            };

            setLogs(prev => [...prev, newLog].slice(-100)); // Keep last 100 logs
        }
    }, [lastMessage, isPaused]);

    useEffect(() => {
        if (!isPaused) {
            logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs, isPaused]);

    // Drag Handlers
    const handleMouseDown = (e: React.MouseEvent) => {
        setIsDragging(true);
        dragStartRef.current = {
            x: e.clientX - position.x,
            y: e.clientY - position.y
        };
    };

    const handleMouseMove = (e: MouseEvent) => {
        if (isDragging && dragStartRef.current) {
            e.preventDefault();
            setPosition({
                x: e.clientX - dragStartRef.current.x,
                y: e.clientY - dragStartRef.current.y
            });
        }
    };

    const handleMouseUp = () => {
        setIsDragging(false);
        dragStartRef.current = null;
    };

    useEffect(() => {
        if (isDragging) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
        } else {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        }
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging]);

    const getLevelColor = (level: string) => {
        switch (level) {
            case 'success': return 'text-green-400';
            case 'warning': return 'text-yellow-400';
            case 'danger': return 'text-red-400';
            default: return 'text-blue-200';
        }
    };

    return (
        <div
            ref={consoleRef}
            style={{
                left: position.x,
                top: position.y,
                width: isExpanded ? 800 : 500,
                height: isExpanded ? 600 : 350
            }}
            className="fixed bg-[#0f172a]/95 backdrop-blur-md border border-white/10 rounded-xl shadow-2xl z-50 flex flex-col font-mono text-xs transition-[width,height] duration-300"
        >

            {/* Header - Draggable Area */}
            <div
                onMouseDown={handleMouseDown}
                className={`flex items-center justify-between px-4 py-2 border-b border-white/10 bg-white/5 rounded-t-xl cursor-move select-none ${isDragging ? 'cursor-grabbing' : ''}`}
            >
                <div className="flex items-center gap-2 pointer-events-none">
                    <Terminal className="w-4 h-4 text-green-400" />
                    <span className="font-bold text-slate-200 uppercase tracking-wider">Live Analysis Console</span>
                    <span className="px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 text-[10px] font-bold animate-pulse">LIVE</span>
                </div>

                <div className="flex items-center gap-2" onMouseDown={(e) => e.stopPropagation()}>
                    <button
                        onClick={() => setIsPaused(!isPaused)}
                        className={`p-1.5 rounded hover:bg-white/10 transition-colors ${isPaused ? 'text-yellow-400' : 'text-slate-400'}`}
                        title={isPaused ? "Resume" : "Pause"}
                    >
                        {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
                    </button>

                    <button
                        onClick={() => setLogs([])}
                        className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-red-400 transition-colors"
                        title="Clear Logs"
                    >
                        <Trash2 className="w-3.5 h-3.5" />
                    </button>

                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                        title={isExpanded ? "Collapse" : "Expand"}
                    >
                        {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                    </button>

                    {onClose && (
                        <button
                            onClick={onClose}
                            className="p-1.5 rounded hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors ml-1"
                            title="Close"
                        >
                            <X className="w-3.5 h-3.5" />
                        </button>
                    )}
                </div>
            </div>

            {/* Logs Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-1.5 custom-scrollbar bg-black/40">
                {logs.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-600 opacity-50 select-none">
                        <Terminal className="w-12 h-12 mb-2" />
                        <p>Waiting for analysis events...</p>
                    </div>
                ) : (
                    logs.map((log) => (
                        <div key={log.id} className="flex gap-3 hover:bg-white/5 p-0.5 rounded transition-colors group text-left">
                            <span className="text-slate-600 shrink-0 select-none">
                                [{new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}]
                            </span>
                            <span className={`break-all ${getLevelColor(log.level)}`}>
                                {log.level === 'success' && '✓ '}
                                {log.level === 'warning' && '⚠ '}
                                {log.level === 'danger' && '✗ '}
                                {log.message}
                            </span>
                        </div>
                    ))
                )}
                <div ref={logsEndRef} />
            </div>
        </div>
    );
};
