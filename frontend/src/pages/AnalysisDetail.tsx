import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { analysisApi, alertsApi } from '../services/api';
import { ArrowLeft, AlertCircle, CheckCircle, XCircle, Shield, Mail, Paperclip, Link2, FileText, Clock, AlertTriangle, ShieldCheck, ShieldX, ShieldAlert, MonitorPlay } from 'lucide-react';
import type { EmailAnalysis, Alert } from '../types';
import { EmailSimulator } from '../components/EmailSimulator';
import { ForensicTimelineComponent } from '../components/ForensicTimeline';
import { ConnectionGraph } from '../components/ConnectionGraph';
import { forensicApi, ForensicEmailDetails } from '../services/api';

export const AnalysisDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [analysis, setAnalysis] = useState<EmailAnalysis | null>(null);
  const [relatedAlerts, setRelatedAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [showSimulator, setShowSimulator] = useState(false);
  const [activeForensicTab, setActiveForensicTab] = useState<'timeline' | 'network'>('timeline');
  const [forensicDetails, setForensicDetails] = useState<ForensicEmailDetails | null>(null);
  const [showForensicPanel, setShowForensicPanel] = useState(false);

  // Auto-open forensic panel if ?forensic=true
  useEffect(() => {
    if (searchParams.get('forensic') === 'true') {
      setShowForensicPanel(true);
    }
  }, [searchParams]);

  useEffect(() => {
    const loadData = async () => {
      if (!id) return;

      try {
        const [analysisData, alertsData] = await Promise.all([
          analysisApi.getAnalysisById(id),
          alertsApi.getAlerts(100, 0),
        ]);

        setAnalysis(analysisData);
        if (analysisData) {
          const related = alertsData.data.filter(
            (a) => a.email_analysis_id === analysisData.id
          );
          setRelatedAlerts(related);
        }
      } catch (error) {
        console.error('Error loading analysis:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id]);

  const getScoreConfig = (score: number) => {
    if (score >= 75) return { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', glow: 'glow-red', gradient: 'from-red-500 to-red-600' };
    if (score >= 50) return { color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/20', glow: '', gradient: 'from-orange-500 to-orange-600' };
    if (score >= 25) return { color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', glow: '', gradient: 'from-yellow-500 to-yellow-600' };
    return { color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20', glow: 'glow-green', gradient: 'from-green-500 to-green-600' };
  };

  const getDecisionConfig = (decision: string) => {
    switch (decision) {
      case 'DELIVER':
        return { label: 'Доставлено', icon: ShieldCheck, color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20' };
      case 'QUARANTINE':
        return { label: 'Карантин', icon: ShieldAlert, color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20' };
      case 'BLOCK':
        return { label: 'Заблокировано', icon: ShieldX, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20' };
      default:
        return { label: decision, icon: Shield, color: 'text-slate-400', bg: 'bg-slate-500/10', border: 'border-slate-500/20' };
    }
  };

  const ScoreCard: React.FC<{ score: number; label: string; icon: React.ReactNode }> = ({ score, label, icon }) => {
    const config = getScoreConfig(score);
    return (
      <div className={`glass-card rounded-2xl p-6 text-center ${config.glow} transition-all hover:translate-y-[-2px]`}>
        <div className={`w-12 h-12 mx-auto rounded-2xl ${config.bg} ${config.border} border flex items-center justify-center mb-4`}>
          {icon}
        </div>
        <p className={`text-4xl font-black ${config.color}`}>{score.toFixed(0)}</p>
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-2">{label}</p>
      </div>
    );
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="w-16 h-16 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin shadow-lg shadow-blue-500/20" />
          <p className="text-slate-500 font-bold uppercase tracking-widest text-xs animate-pulse">Загрузка анализа...</p>
        </div>
      </Layout>
    );
  }

  if (!analysis) {
    return (
      <Layout>
        <div className="text-center py-20 glass-card rounded-3xl">
          <AlertCircle className="w-16 h-16 text-slate-600/30 mx-auto mb-4" />
          <p className="text-slate-400 font-bold text-lg">Анализ не найден</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-6 px-6 py-3 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-xl text-blue-400 font-bold text-sm uppercase tracking-wider transition-all"
          >
            Вернуться в дашборд
          </button>
        </div>
      </Layout>
    );
  }

  const riskConfig = getScoreConfig(analysis.risk_score);
  const decisionConfig = getDecisionConfig(analysis.decision);
  const DecisionIcon = decisionConfig.icon;

  return (
    <Layout>
      <div className="space-y-8 pb-10 animate-fadeIn">
        {/* Back Button */}
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-slate-500 hover:text-white transition-colors font-bold text-sm uppercase tracking-wider"
        >
          <ArrowLeft className="w-4 h-4" />
          Назад
        </button>

        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="h-1 w-8 bg-blue-500 rounded-full" />
            <p className="text-blue-400 text-xs font-black uppercase tracking-[0.2em]">Детальный анализ</p>
          </div>
          <h1 className="text-4xl font-black text-white tracking-tighter leading-tight">{analysis.subject || 'Без темы'}</h1>
          <div className="flex flex-wrap items-center gap-4 mt-4 text-sm">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-lg">
              <Mail className="w-4 h-4 text-slate-500" />
              <span className="font-mono text-slate-300">{analysis.sender_email}</span>
            </div>
            <span className="text-slate-600">→</span>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-lg">
              <span className="font-mono text-slate-300">{analysis.recipient_email}</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-lg">
              <Clock className="w-4 h-4 text-slate-500" />
              <span className="text-slate-400">{new Date(analysis.created_at).toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Decision Badge */}
        <div className="flex items-center justify-between">
          <div className={`inline-flex items-center gap-3 px-6 py-4 rounded-2xl border ${decisionConfig.bg} ${decisionConfig.border}`}>
            <DecisionIcon className={`w-6 h-6 ${decisionConfig.color}`} />
            <span className={`text-lg font-black uppercase tracking-wider ${decisionConfig.color}`}>{decisionConfig.label}</span>
          </div>

          <button
            onClick={() => setShowSimulator(!showSimulator)}
            className={`flex items-center gap-2 px-6 py-4 rounded-xl font-bold transition-all shadow-lg ${showSimulator
              ? 'bg-blue-600 text-white shadow-blue-500/25'
              : 'bg-white/10 text-white hover:bg-white/20'
              }`}
          >
            <MonitorPlay size={20} />
            {showSimulator ? 'СКРЫТЬ СИМУЛЯТОР' : 'ЗАПУСТИТЬ СИМУЛЯТОР'}
          </button>
        </div>

        {/* Score Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <ScoreCard score={analysis.technical_score} label="Техническая" icon={<Shield className={`w-5 h-5 ${getScoreConfig(analysis.technical_score).color}`} />} />
          <ScoreCard score={analysis.linguistic_score} label="Лингвистическая" icon={<FileText className={`w-5 h-5 ${getScoreConfig(analysis.linguistic_score).color}`} />} />
          <ScoreCard score={analysis.behavioral_score} label="Поведенческая" icon={<AlertTriangle className={`w-5 h-5 ${getScoreConfig(analysis.behavioral_score).color}`} />} />
          <ScoreCard score={analysis.contextual_score} label="Контекстная" icon={<Link2 className={`w-5 h-5 ${getScoreConfig(analysis.contextual_score).color}`} />} />
        </div>

        {/* Detailed Breakdown */}
        {analysis.analysis_details && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* NEW: Feature Importance (Golden Record Demo) */}
            {(analysis.analysis_details as any).feature_importance && (
              <div className="glass-card rounded-2xl p-6 border border-red-500/30 bg-red-500/5 col-span-1 md:col-span-2">
                <h4 className="text-sm font-black text-red-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <ShieldAlert size={16} /> Feature Importance (AI Breakdown)
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries((analysis.analysis_details as any).feature_importance).map(([key, value]) => (
                    <div key={key} className="bg-black/20 rounded-xl p-3 border border-red-500/10">
                      <p className="text-[10px] text-slate-400 uppercase tracking-wider font-bold mb-1">{key.replace('_', ' ')}</p>
                      <p className="text-xl font-black text-white">{(Number(value) * 100).toFixed(0)}%</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* NEW: Linguistic Indicators (Golden Record Demo) */}
            {(analysis.analysis_details as any).linguistic_result?.indicators && (
              <div className="glass-card rounded-2xl p-6 border border-purple-500/30 bg-purple-500/5 col-span-1 md:col-span-2">
                <h4 className="text-sm font-black text-purple-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <MonitorPlay size={16} /> AI Pattern Matching
                </h4>
                <ul className="space-y-2">
                  {((analysis.analysis_details as any).linguistic_result.indicators as string[]).map((item, idx) => (
                    <li key={idx} className="text-sm text-purple-200 flex items-start gap-2 font-medium">
                      <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-purple-400" />
                      {item}
                    </li>
                  ))}
                </ul>
                {(analysis.analysis_details as any).linguistic_result.explanation && (
                  <div className="mt-4 p-4 bg-purple-500/10 rounded-xl border border-purple-500/20">
                    <p className="text-sm text-purple-100 italic">
                      "{(analysis.analysis_details as any).linguistic_result.explanation}"
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Fallback for Legacy/Standard Structure */}
            {analysis.analysis_details.technical?.length > 0 && (
              <div className="glass-card rounded-2xl p-6 border border-slate-700/50">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <Shield size={14} /> Технические детали
                </h4>
                <ul className="space-y-2">
                  {analysis.analysis_details.technical.map((item, idx) => (
                    <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                      <div className="mt-1 w-1.5 h-1.5 rounded-full bg-slate-500" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.analysis_details.linguistic?.length > 0 && (
              <div className="glass-card rounded-2xl p-6 border border-slate-700/50">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <FileText size={14} /> Лингвистика
                </h4>
                <ul className="space-y-2">
                  {analysis.analysis_details.linguistic.map((item, idx) => (
                    <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                      <div className="mt-1 w-1.5 h-1.5 rounded-full bg-slate-500" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.analysis_details.behavioral?.length > 0 && (
              <div className="glass-card rounded-2xl p-6 border border-slate-700/50">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <AlertTriangle size={14} /> Поведение
                </h4>
                <ul className="space-y-2">
                  {analysis.analysis_details.behavioral.map((item, idx) => (
                    <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                      <div className="mt-1 w-1.5 h-1.5 rounded-full bg-slate-500" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.analysis_details.contextual?.length > 0 && (
              <div className="glass-card rounded-2xl p-6 border border-slate-700/50">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                  <Link2 size={14} /> Контекст
                </h4>
                <ul className="space-y-2">
                  {analysis.analysis_details.contextual.map((item, idx) => (
                    <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                      <div className="mt-1 w-1.5 h-1.5 rounded-full bg-slate-500" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Total Risk */}
        <div className={`glass-card rounded-3xl p-8 ${riskConfig.glow}`}>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-2xl ${riskConfig.bg} ${riskConfig.border} border`}>
                <Shield className={`w-6 h-6 ${riskConfig.color}`} />
              </div>
              <div>
                <h3 className="text-xl font-black text-white">Итоговый риск</h3>
                <p className="text-slate-500 text-sm">Агрегированная оценка угрозы</p>
              </div>
            </div>
            <p className={`text-5xl font-black ${riskConfig.color}`}>{analysis.risk_score.toFixed(1)}</p>
          </div>
          <div className="h-4 bg-white/5 rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r ${riskConfig.gradient} transition-all duration-500`}
              style={{ width: `${analysis.risk_score}%` }}
            />
          </div>
        </div>

        {/* Explanation */}
        {analysis.explanation && (
          <div className="glass-card rounded-3xl p-8">
            <div className="flex items-center gap-4 mb-6">
              <div className="p-3 bg-indigo-500/10 rounded-2xl">
                <FileText className="w-6 h-6 text-indigo-400" />
              </div>
              <h3 className="text-xl font-black text-white">Пояснение решения</h3>
            </div>
            <p className="text-slate-300 leading-relaxed">{analysis.explanation}</p>
          </div>
        )}

        {/* AI Analysis Result (if available) */}
        {analysis.raw_headers && (analysis.raw_headers as any)['x_ai_analysis'] && (
          <div className={`glass-card rounded-3xl p-8 mb-6 border border-purple-500/30 bg-purple-500/5`}>
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-purple-500/20 rounded-2xl">
                <FileText className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h3 className="text-xl font-black text-white">AI Analysis (Gemini)</h3>
                <p className="text-purple-300 text-sm">Linguistic & Psychological Profiling</p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <p className="text-slate-300 italic mb-4">"{(analysis.raw_headers as any)['x_ai_analysis'].summary}"</p>
                <div className="space-y-2">
                  {(analysis.raw_headers as any)['x_ai_analysis'].indicators?.map((ind: string, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-purple-200">
                      <AlertTriangle size={14} className="text-purple-400" />
                      {ind}
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-black/20 p-4 rounded-xl text-sm text-slate-300">
                {(analysis.raw_headers as any)['x_ai_analysis'].explanation}
              </div>
            </div>
          </div>
        )}

        {/* Details Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Email Details */}
          <div className="glass-card rounded-3xl p-8 lg:col-span-2">
            <div className="flex items-center gap-4 mb-6">
              <div className="p-3 bg-blue-500/10 rounded-2xl">
                <Mail className="w-6 h-6 text-blue-400" />
              </div>
              <h3 className="text-xl font-black text-white">Детали письма</h3>
            </div>

            <div className="space-y-4 mb-8">
              <div className="flex items-center gap-4">
                <Paperclip className="w-5 h-5 text-slate-600" />
                <span className="text-slate-500 font-medium">Вложения:</span>
                <span className="text-white font-bold">
                  {analysis.has_attachments ? `${analysis.attachment_count} файл(ов)` : 'Нет'}
                </span>
              </div>
              {analysis.suspicious_urls && analysis.suspicious_urls.length > 0 && (
                <div>
                  <div className="flex items-center gap-4 mb-3">
                    <Link2 className="w-5 h-5 text-orange-400" />
                    <span className="text-orange-400 font-bold">Найденные ссылки:</span>
                  </div>
                  <div className="space-y-2">
                    {analysis.suspicious_urls.map((url, i) => (
                      <div key={i} className="font-mono text-xs bg-orange-500/10 border border-orange-500/20 rounded-xl px-4 py-2 text-orange-300 break-all">
                        {url}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div>
              <h4 className="text-sm font-black text-slate-400 uppercase tracking-widest mb-3">
                {showSimulator ? 'Визуальный симулятор' : 'Текст письма'}
              </h4>

              {showSimulator ? (
                <div className="h-[600px]">
                  <EmailSimulator
                    subject={analysis.subject || '(Без темы)'}
                    from={analysis.sender_email}
                    body={analysis.body_text || analysis.body_preview || ''}
                    attachments={analysis.has_attachments ? [{ filename: 'attachment.ext', size: 'unknown' }] : []}
                    riskHighlights={analysis.suspicious_urls?.map(url => ({
                      word: url,
                      reason: 'Suspicious URL detected',
                      severity: 'high'
                    }))}
                  />
                </div>
              ) : (
                <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6 max-h-[400px] overflow-auto custom-scrollbar text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                  {analysis.body_text || analysis.body_preview || 'Текст письма недоступен'}
                </div>
              )}
            </div>
          </div>

          {/* Related Alerts */}
          <div className="glass-card rounded-3xl p-8">
            <div className="flex items-center gap-4 mb-6">
              <div className="p-3 bg-red-500/10 rounded-2xl">
                <AlertCircle className="w-6 h-6 text-red-400" />
              </div>
              <h3 className="text-xl font-black text-white">Связанные алерты</h3>
            </div>
            {relatedAlerts.length === 0 ? (
              <div className="text-center py-10">
                <CheckCircle className="w-12 h-12 text-green-500/30 mx-auto mb-3" />
                <p className="text-slate-500 font-medium">Нет связанных алертов</p>
              </div>
            ) : (
              <div className="space-y-3">
                {relatedAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="p-4 bg-white/[0.02] border border-white/5 rounded-2xl hover:bg-white/[0.04] transition-all"
                  >
                    <p className="text-white font-bold text-sm">{alert.title}</p>
                    {alert.description && (
                      <p className="text-slate-500 text-xs mt-1 line-clamp-2">{alert.description}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Forensic Investigation */}
          {analysis && (
            <div className="glass-card rounded-3xl p-8">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-cyan-500/10 rounded-2xl">
                    <Shield className="w-6 h-6 text-cyan-400" />
                  </div>
                  <h3 className="text-xl font-black text-white">Форензика</h3>
                </div>
                <button
                  onClick={() => {
                    console.log('Analysis:', analysis);
                    console.log('Sender email:', analysis.sender_email);
                    setShowForensicPanel(!showForensicPanel);
                  }}
                  className="px-4 py-2 bg-cyan-500/20 text-cyan-400 rounded-xl border border-cyan-500/30 hover:bg-cyan-500/30 transition-colors text-sm font-medium"
                >
                  {showForensicPanel ? 'Скрыть' : 'Расследовать'}
                </button>
              </div>

              {showForensicPanel && (analysis.sender_email || analysis.from_address) && (
                <div className="space-y-6">
                  {/* Tabs */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => setActiveForensicTab('timeline')}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        activeForensicTab === 'timeline'
                          ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                          : 'bg-slate-800/50 text-gray-400 border border-slate-700 hover:bg-slate-700'
                      }`}
                    >
                      Timeline отправителя
                    </button>
                    <button
                      onClick={() => setActiveForensicTab('network')}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        activeForensicTab === 'network'
                          ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                          : 'bg-slate-800/50 text-gray-400 border border-slate-700 hover:bg-slate-700'
                      }`}
                    >
                      Сеть получателей
                    </button>
                  </div>

                  {/* Tab Content */}
                  <div className="mt-6">
                    {activeForensicTab === 'timeline' ? (
                      <ForensicTimelineComponent 
                        senderEmail={analysis.sender_email || (analysis as any).from_address || 'unknown@example.com'} 
                        onSelectEmail={async (emailId) => {
                          try {
                            const details = await forensicApi.getEmailDetails(emailId);
                            setForensicDetails(details);
                          } catch (err) {
                            console.error('Failed to load forensic details:', err);
                          }
                        }}
                      />
                    ) : (
                      <ConnectionGraph 
                        senderEmail={analysis.sender_email || (analysis as any).from_address || 'unknown@example.com'}
                        onSelectRecipient={(email) => console.log('Selected:', email)}
                      />
                    )}
                  </div>

                  {/* Forensic Details Modal */}
                  {forensicDetails && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                      <div className="bg-slate-900 rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-auto border border-slate-700">
                        <div className="flex items-center justify-between mb-4">
                          <h4 className="text-lg font-bold text-white">Детали письма</h4>
                          <button 
                            onClick={() => setForensicDetails(null)}
                            className="text-gray-400 hover:text-white"
                          >
                            ✕
                          </button>
                        </div>
                        
                        <div className="space-y-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <div className="text-xs text-gray-500">Риск</div>
                              <div className="text-xl font-bold text-white">{forensicDetails.email.risk_score}%</div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-500">В реестре</div>
                              <div className="text-white">
                                {forensicDetails.registry_info.is_registered 
                                  ? `✓ ${forensicDetails.registry_info.organization_name}`
                                  : '✗ Неизвестный'}
                              </div>
                            </div>
                          </div>
                          
                          <div className="text-sm text-gray-400">
                            {forensicDetails.email.body_text?.substring(0, 500)}...
                          </div>
                          
                          {forensicDetails.alerts.length > 0 && (
                            <div>
                              <div className="text-sm font-medium text-gray-400 mb-2">Алерты:</div>
                              {forensicDetails.alerts.map(alert => (
                                <div key={alert.id} className="p-2 bg-red-500/10 rounded text-sm">
                                  <span className="text-red-400">{alert.title}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Layout >
  );
};
