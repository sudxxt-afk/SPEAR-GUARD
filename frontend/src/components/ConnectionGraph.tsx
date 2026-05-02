import React, { useState, useEffect } from 'react';
import { forensicApi, RecipientNetwork } from '../services/api';
import { Users, AlertTriangle, TrendingUp, Shield } from 'lucide-react';

interface ConnectionGraphProps {
  senderEmail: string;
  onSelectRecipient?: (email: string) => void;
}

export const ConnectionGraph: React.FC<ConnectionGraphProps> = ({
  senderEmail,
  onSelectRecipient
}) => {
  const [network, setNetwork] = useState<RecipientNetwork | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showHighRiskOnly, setShowHighRiskOnly] = useState(false);

  useEffect(() => {
    loadNetwork();
  }, [senderEmail]);

  const loadNetwork = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await forensicApi.getRecipientNetwork(senderEmail);
      setNetwork(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load network');
    } finally {
      setLoading(false);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500"></div>
        <span className="ml-3 text-gray-400">Анализ связей...</span>
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

  if (!network) return null;

  const displayNetwork = showHighRiskOnly 
    ? network.high_risk_recipients 
    : network.network;

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Users className="w-4 h-4" />
            Всего получателей
          </div>
          <div className="text-2xl font-bold text-white mt-1">{network.total_recipients}</div>
        </div>
        
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertTriangle className="w-4 h-4" />
            Высокий риск
          </div>
          <div className="text-2xl font-bold text-red-400 mt-1">{network.high_risk_recipients.length}</div>
        </div>
        
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Shield className="w-4 h-4" />
            В реестре
          </div>
          <div className="text-2xl font-bold text-green-400 mt-1">
            {network.network.filter(n => n.average_risk_score < 30).length}
          </div>
        </div>
      </div>

      {/* Filter Toggle */}
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showHighRiskOnly}
            onChange={(e) => setShowHighRiskOnly(e.target.checked)}
            className="w-4 h-4 rounded bg-slate-800 border-slate-600 text-cyan-500 focus:ring-cyan-500"
          />
          <span className="text-gray-400 text-sm">Только высокий риск</span>
        </label>
      </div>

      {/* Network Graph / List */}
      <div className="space-y-3">
        {displayNetwork.map((node, index) => (
          <div
            key={node.email || index}
            onClick={() => onSelectRecipient?.(node.email)}
            className={`p-4 rounded-lg border cursor-pointer transition-all hover:scale-[1.01] ${getRiskBg(node.average_risk_score)}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  node.average_risk_score >= 75 ? 'bg-red-500/20' :
                  node.average_risk_score >= 50 ? 'bg-orange-500/20' :
                  'bg-green-500/20'
                }`}>
                  <Users className={`w-5 h-5 ${
                    node.average_risk_score >= 75 ? 'text-red-400' :
                    node.average_risk_score >= 50 ? 'text-orange-400' :
                    'text-green-400'
                  }`} />
                </div>
                <div>
                  <div className="font-medium text-white">
                    {node.user_name || node.email}
                  </div>
                  <div className="text-gray-500 text-sm">
                    {node.email}
                    {node.department && <span className="ml-2">• {node.department}</span>}
                  </div>
                </div>
              </div>
              
              <div className="text-right">
                <div className={`text-xl font-bold ${getRiskColor(node.average_risk_score)}`}>
                  {node.average_risk_score}%
                </div>
                <div className="text-gray-500 text-xs">
                  {node.emails_received} писем
                </div>
              </div>
            </div>
            
            {/* Timeline */}
            <div className="mt-3 pt-3 border-t border-slate-700/50 flex items-center justify-between text-sm">
              <div className="text-gray-500">
                Первый контакт: {node.first_contact 
                  ? new Date(node.first_contact).toLocaleDateString('ru-RU')
                  : 'N/A'}
              </div>
              <div className="text-gray-500">
                Последний: {node.last_contact 
                  ? new Date(node.last_contact).toLocaleDateString('ru-RU')
                  : 'N/A'}
              </div>
            </div>
          </div>
        ))}
        
        {displayNetwork.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Получателей не найдено</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConnectionGraph;