import React, { useState } from 'react';
import { Shield, Smartphone, Monitor, AlertTriangle } from 'lucide-react';

interface EmailSimulatorProps {
    subject: string;
    from: string;
    body: string; // This can be HTML or plain text
    riskHighlights?: {
        word: string;
        reason: string;
        severity: 'low' | 'medium' | 'high';
    }[];
    attachments?: { filename: string; size: string }[];
}

export const EmailSimulator: React.FC<EmailSimulatorProps> = ({
    subject,
    from,
    body,
    riskHighlights = [],
    attachments = []
}) => {
    const [deviceMode, setDeviceMode] = useState<'desktop' | 'mobile'>('desktop');
    const [safeMode, setSafeMode] = useState(true);

    // Sanitize and highlight function
    const processContent = (content: string) => {
        let safeContent = content;

        // Basic sanitization (in production use DOMPurify)
        safeContent = safeContent.replace(/<script\b[^>]*>([\s\S]*?)<\/script>/gm, "");
        safeContent = safeContent.replace(/<iframe\b[^>]*>([\s\S]*?)<\/iframe>/gm, "");

        // Highlight risky words if safe mode is on
        if (safeMode && riskHighlights.length > 0) {
            riskHighlights.forEach(highlight => {
                const regex = new RegExp(`(${highlight.word})`, 'gi');
                const color = highlight.severity === 'high' ? 'bg-red-500/30 border-red-500' :
                    highlight.severity === 'medium' ? 'bg-orange-500/30 border-orange-500' :
                        'bg-yellow-500/30 border-yellow-500';

                safeContent = safeContent.replace(regex,
                    `<span class="${color} border-b-2 px-1 rounded cursor-help" title="${highlight.reason}">$1</span>`
                );
            });
        }

        // Disable links in safe mode
        if (safeMode) {
            safeContent = safeContent.replace(/<a\s+(?:[^>]*?\s+)?href=(["'])(.*?)\1/gi,
                '<span class="text-blue-400 underline cursor-not-allowed opacity-70" title="Link disabled in Simulator">$2</span>'
            );
        }

        return safeContent;
    };

    return (
        <div className="flex flex-col h-full bg-slate-900 rounded-xl overflow-hidden border border-slate-700 shadow-2xl">
            {/* Simulator Toolbar */}
            <div className="bg-slate-800 p-3 border-b border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 bg-slate-900/50 p-1 rounded-lg border border-slate-700/50">
                        <button
                            onClick={() => setDeviceMode('desktop')}
                            className={`p-2 rounded-md transition-all ${deviceMode === 'desktop' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-400 hover:text-white hover:bg-slate-700'}`}
                            title="Desktop View"
                        >
                            <Monitor size={16} />
                        </button>
                        <button
                            onClick={() => setDeviceMode('mobile')}
                            className={`p-2 rounded-md transition-all ${deviceMode === 'mobile' ? 'bg-blue-600 text-white shadow-lg' : 'text-slate-400 hover:text-white hover:bg-slate-700'}`}
                            title="Mobile View"
                        >
                            <Smartphone size={16} />
                        </button>
                    </div>

                    <div className="h-6 w-px bg-slate-700"></div>

                    <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Safety Layer:</span>
                        <button
                            onClick={() => setSafeMode(!safeMode)}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold transition-all border ${safeMode
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                : 'bg-red-500/10 text-red-400 border-red-500/30'
                                }`}
                        >
                            {safeMode ? <Shield size={12} /> : <AlertTriangle size={12} />}
                            {safeMode ? 'ARMED' : 'DISARMED'}
                        </button>
                    </div>
                </div>

                <div className="text-xs text-slate-500 italic">
                    <span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
                    Secure Sandbox Environment
                </div>
            </div>

            {/* Simulator Viewport */}
            <div className="flex-1 bg-slate-950 p-8 overflow-auto flex justify-center custom-scrollbar relative">
                {/* Grid Background */}
                <div className="absolute inset-0 pointer-events-none opacity-[0.05]"
                    style={{ backgroundImage: 'linear-gradient(#4f4f4f 1px, transparent 1px), linear-gradient(90deg, #4f4f4f 1px, transparent 1px)', backgroundSize: '20px 20px' }}
                />

                <div
                    className={`transition-all duration-500 ease-in-out bg-white text-slate-900 shadow-2xl overflow-hidden flex flex-col ${deviceMode === 'mobile'
                        ? 'w-[375px] h-[667px] rounded-[30px] border-[8px] border-slate-800'
                        : 'w-full max-w-4xl min-h-[500px] rounded-lg border border-slate-200'
                        }`}
                >
                    {/* Email Header */}
                    <div className="bg-gray-50 p-4 border-b border-gray-100 pb-4">
                        {deviceMode === 'mobile' && (
                            <div className="flex justify-center mb-4">
                                <div className="w-16 h-1 bg-gray-300 rounded-full"></div>
                            </div>
                        )}
                        <h1 className="text-lg font-bold text-gray-900 mb-2 leading-tight">{subject}</h1>
                        <div className="flex items-start gap-3">
                            <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-sm shrink-0">
                                {from.charAt(0).toUpperCase()}
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="font-semibold text-sm text-gray-900 truncate">{from}</div>
                                <div className="text-xs text-gray-500">to me</div>
                            </div>
                            <div className="text-xs text-gray-400 whitespace-nowrap">
                                {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </div>
                        </div>

                        {safeMode && (
                            <div className="mt-3 bg-yellow-50 border border-yellow-200 rounded p-2 flex items-start gap-2">
                                <AlertTriangle className="text-yellow-600 shrink-0 mt-0.5" size={14} />
                                <p className="text-xs text-yellow-700">
                                    External images and links are disabled in Sandbox mode.
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Email Body */}
                    <div className="p-4 overflow-auto flex-1 font-sans text-sm md:text-base leading-relaxed text-gray-800">
                        <div
                            dangerouslySetInnerHTML={{ __html: processContent(body) }}
                            className="prose prose-sm max-w-none"
                        />

                        {attachments.length > 0 && (
                            <div className="mt-8 border-t pt-4">
                                <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">Attachments</h4>
                                <div className="flex flex-wrap gap-2">
                                    {attachments.map((att, i) => (
                                        <div key={i} className="flex items-center gap-2 bg-gray-100 border border-gray-200 p-2 rounded text-xs text-gray-600">
                                            <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                                            </svg>
                                            {att.filename} <span className="text-gray-400">({att.size})</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {deviceMode === 'mobile' && (
                        <div className="p-4 bg-gray-50 border-t border-gray-100 flex justify-around text-gray-400">
                            <div className="w-6 h-6 rounded bg-gray-200"></div>
                            <div className="w-6 h-6 rounded bg-gray-200"></div>
                            <div className="w-6 h-6 rounded bg-gray-200"></div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
