import React, { useState, useEffect } from 'react';
import { Layout } from '../components/Layout';
import { useAuth } from '../hooks/useAuth';
import { profileApi, authApi, mailAccountsApi, systemApi, MailAccount, MailProvider, MailAccountCreate } from '../services/api';
import { Save, AlertCircle, Bell, KeyRound, User, Building2, Briefcase, Shield, CheckCircle, Lock, Mail, Inbox, Plus, Trash2, RefreshCw, X, Loader2, Eye, EyeOff, Cpu, Server, Zap } from 'lucide-react';

export const Settings: React.FC = () => {
  const { profile } = useAuth();
  const [formData, setFormData] = useState({
    full_name: '',
    department: '',
    job_role: '',
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  const [pwdForm, setPwdForm] = useState({ current: '', next: '', confirm: '' });
  const [pwdLoading, setPwdLoading] = useState(false);
  const [pwdMessage, setPwdMessage] = useState('');

  const [activeSection, setActiveSection] = useState<'profile' | 'security' | 'notifications' | 'mail' | 'integrations'>('profile');

  // Mail accounts state
  const [mailAccounts, setMailAccounts] = useState<MailAccount[]>([]);
  const [mailProviders, setMailProviders] = useState<MailProvider[]>([]);
  const [mailLoading, setMailLoading] = useState(false);
  const [mailMessage, setMailMessage] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [newAccount, setNewAccount] = useState<MailAccountCreate>({
    name: '',
    email: '',
    provider: 'gmail',
    password: '',
    folder: 'INBOX',
    sync_interval_minutes: 5,
  });

  useEffect(() => {
    if (profile) {
      setFormData({
        full_name: profile.full_name || '',
        department: profile.department || '',
        job_role: profile.job_role || '',
      });
    }
  }, [profile]);

  // Load mail accounts when section is active
  useEffect(() => {
    if (activeSection === 'mail') {
      loadMailAccounts();
      loadMailProviders();
    }
  }, [activeSection]);

  const loadMailAccounts = async () => {
    try {
      const accounts = await mailAccountsApi.getAccounts();
      setMailAccounts(accounts);
    } catch (error) {
      console.error('Failed to load mail accounts:', error);
    }
  };

  const loadMailProviders = async () => {
    try {
      const providers = await mailAccountsApi.getProviders();
      setMailProviders(providers);
    } catch (error) {
      console.error('Failed to load providers:', error);
    }
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setMailMessage('');
    try {
      const result = await mailAccountsApi.testConnection(newAccount);
      if (result.success) {
        setMailMessage(`✓ Подключение успешно! Папки: ${result.folders?.slice(0, 5).join(', ') || 'INBOX'}`);
      } else {
        setMailMessage(`✗ ${result.message}`);
      }
    } catch (error) {
      setMailMessage(error instanceof Error ? error.message : 'Ошибка подключения');
    } finally {
      setTestingConnection(false);
      setTimeout(() => setMailMessage(''), 5000);
    }
  };

  const handleAddAccount = async () => {
    setMailLoading(true);
    setMailMessage('');
    try {
      await mailAccountsApi.createAccount(newAccount);
      setMailMessage('Аккаунт успешно подключен!');
      setShowAddForm(false);
      setNewAccount({ name: '', email: '', provider: 'gmail', password: '', folder: 'INBOX', sync_interval_minutes: 5 });
      await loadMailAccounts();
    } catch (error) {
      setMailMessage(error instanceof Error ? error.message : 'Не удалось подключить аккаунт');
    } finally {
      setMailLoading(false);
      setTimeout(() => setMailMessage(''), 4000);
    }
  };

  const handleDeleteAccount = async (id: number) => {
    if (!confirm('Удалить этот почтовый аккаунт?')) return;
    try {
      await mailAccountsApi.deleteAccount(id);
      setMailAccounts((prev) => prev.filter((a) => a.id !== id));
      setMailMessage('Аккаунт удалён');
    } catch (error) {
      setMailMessage(error instanceof Error ? error.message : 'Не удалось удалить');
    }
    setTimeout(() => setMailMessage(''), 3000);
  };

  const handleSyncAccount = async (id: number) => {
    try {
      await mailAccountsApi.triggerSync(id);
      setMailMessage('Синхронизация запущена');
      await loadMailAccounts();
    } catch (error) {
      setMailMessage(error instanceof Error ? error.message : 'Ошибка синхронизации');
    }
    setTimeout(() => setMailMessage(''), 3000);
  };

  // Systems / Integrations State & Handlers
  const [sysImapLoading, setSysImapLoading] = useState(false);
  const [sysImapMessage, setSysImapMessage] = useState('');
  const [geminiLoading, setGeminiLoading] = useState(false);
  const [geminiMessage, setGeminiMessage] = useState('');
  const [geminiResult, setGeminiResult] = useState<any>(null);

  const handleTestSystemImap = async () => {
    setSysImapLoading(true);
    setSysImapMessage('');
    try {
      const res = await systemApi.testImap();
      if (res.success) {
        setSysImapMessage('✓ Подключение успешно установлено!');
      } else {
        setSysImapMessage(`✗ Ошибка: ${res.error || res.message}`);
      }
    } catch (error) {
      setSysImapMessage('Не удалось подключиться к серверу');
    } finally {
      setSysImapLoading(false);
    }
  };

  const handleTestGemini = async () => {
    setGeminiLoading(true);
    setGeminiMessage('');
    setGeminiResult(null);
    try {
      const res = await systemApi.testGemini();
      if (res.success) {
        setGeminiMessage('✓ Gemini AI успешно отвечает!');
        setGeminiResult(res.details);
      } else {
        setGeminiMessage(`✗ Ошибка: ${res.message}`);
        setGeminiResult(res.details); // Might contain fallback info
      }
    } catch (error) {
      setGeminiMessage('Ошибка соединения с AI модулем');
    } finally {
      setGeminiLoading(false);
    }
  };

  const handleSave = async () => {
    if (!profile) return;
    setSaving(true);
    setMessage('');
    try {
      await profileApi.updateProfile(profile.user_id, formData);
      setMessage('Профиль обновлён');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Не удалось сохранить профиль');
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(''), 3000);
    }
  };

  const handleChangePassword = async () => {
    if (!pwdForm.current || !pwdForm.next || pwdForm.next !== pwdForm.confirm) {
      setPwdMessage('Пароли не совпадают или не заполнены');
      return;
    }
    setPwdLoading(true);
    setPwdMessage('');
    try {
      await authApi.changePassword(pwdForm.current, pwdForm.next);
      setPwdMessage('Пароль обновлён');
      setPwdForm({ current: '', next: '', confirm: '' });
    } catch (error) {
      setPwdMessage(error instanceof Error ? error.message : 'Не удалось обновить пароль');
    } finally {
      setPwdLoading(false);
      setTimeout(() => setPwdMessage(''), 4000);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'text-green-400 bg-green-500/10 border-green-500/20';
      case 'syncing': return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
      case 'auth_error': return 'text-red-400 bg-red-500/10 border-red-500/20';
      case 'error': return 'text-orange-400 bg-orange-500/10 border-orange-500/20';
      default: return 'text-slate-400 bg-slate-500/10 border-slate-500/20';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'connected': return 'Подключён';
      case 'syncing': return 'Синхронизация...';
      case 'auth_error': return 'Ошибка авторизации';
      case 'error': return 'Ошибка';
      case 'pending': return 'Ожидание';
      default: return status;
    }
  };

  const sections = [
    { key: 'profile', label: 'Профиль', icon: User },
    { key: 'security', label: 'Безопасность', icon: Lock },
    { key: 'mail', label: 'Почта', icon: Inbox },
    { key: 'integrations', label: 'Интеграции', icon: Cpu },
    { key: 'notifications', label: 'Уведомления', icon: Bell },
  ] as const;

  return (
    <Layout>
      <div className="space-y-8 pb-10 max-w-4xl">
        {/* Header */}
        <div className="animate-fadeIn">
          <div className="flex items-center gap-2 mb-2">
            <span className="h-1 w-8 bg-purple-500 rounded-full" />
            <p className="text-purple-400 text-xs font-black uppercase tracking-[0.2em]">Конфигурация</p>
          </div>
          <h1 className="text-5xl font-black text-white tracking-tighter">Настройки</h1>
          <p className="text-slate-500 mt-2 font-medium">Управление профилем и параметрами безопасности</p>
        </div>

        {/* Section Tabs */}
        <div className="flex items-center gap-3 animate-fadeIn" style={{ animationDelay: '0.1s' }}>
          {sections.map((s) => {
            const Icon = s.icon;
            const isActive = activeSection === s.key;
            return (
              <button
                key={s.key}
                onClick={() => setActiveSection(s.key)}
                className={`flex items-center gap-2 px-5 py-3 rounded-2xl border font-bold text-sm uppercase tracking-wider transition-all duration-300 ${isActive
                  ? 'bg-purple-500/20 border-purple-500/30 text-purple-400 glow-purple'
                  : 'bg-white/[0.03] border-white/5 text-slate-500 hover:bg-white/[0.06] hover:text-white'
                  }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'scale-110' : ''} transition-transform`} />
                {s.label}
              </button>
            );
          })}
        </div>

        {/* Messages */}
        {message && (
          <div
            className={`p-4 rounded-2xl border flex items-center gap-3 animate-fadeIn ${message.toLowerCase().includes('не удалось')
              ? 'bg-red-500/10 border-red-500/20 text-red-300'
              : 'bg-green-500/10 border-green-500/20 text-green-300'
              }`}
          >
            {message.toLowerCase().includes('не удалось') ? (
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
            ) : (
              <CheckCircle className="w-5 h-5 flex-shrink-0" />
            )}
            <p className="font-medium text-sm">{message}</p>
          </div>
        )}

        {/* Profile Section */}
        {activeSection === 'profile' && (
          <div className="glass-card rounded-3xl p-8 space-y-8 animate-fadeIn">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-500/10 rounded-2xl">
                <User className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <h2 className="text-2xl font-black text-white tracking-tight">Профиль</h2>
                <p className="text-slate-500 text-sm">Персональная информация</p>
              </div>
            </div>

            <div className="space-y-6">
              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Email</label>
                <div className="relative">
                  <input
                    type="email"
                    value={profile?.email || ''}
                    disabled
                    className="w-full px-4 py-4 pl-12 bg-white/[0.02] border border-white/5 rounded-2xl text-slate-500 cursor-not-allowed"
                  />
                  <Mail className="absolute left-4 top-4 w-5 h-5 text-slate-700" />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">ФИО</label>
                <div className="relative">
                  <input
                    type="text"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    className="w-full px-4 py-4 pl-12 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-purple-500/50 focus:bg-white/10 transition-all"
                    placeholder="Введите имя"
                  />
                  <User className="absolute left-4 top-4 w-5 h-5 text-slate-600" />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Подразделение</label>
                  <div className="relative">
                    <input
                      type="text"
                      value={formData.department}
                      onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                      className="w-full px-4 py-4 pl-12 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-purple-500/50 focus:bg-white/10 transition-all"
                      placeholder="Отдел / Управление"
                    />
                    <Building2 className="absolute left-4 top-4 w-5 h-5 text-slate-600" />
                  </div>
                </div>

                <div>
                  <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Должность</label>
                  <div className="relative">
                    <input
                      type="text"
                      value={formData.job_role}
                      onChange={(e) => setFormData({ ...formData, job_role: e.target.value })}
                      className="w-full px-4 py-4 pl-12 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-purple-500/50 focus:bg-white/10 transition-all"
                      placeholder="Ваша должность"
                    />
                    <Briefcase className="absolute left-4 top-4 w-5 h-5 text-slate-600" />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Уровень доступа</label>
                <div className="flex items-center gap-3">
                  <div className="px-4 py-3 bg-purple-500/10 border border-purple-500/20 rounded-xl flex items-center gap-2">
                    <Shield className="w-5 h-5 text-purple-400" />
                    <span className="text-purple-400 font-black text-lg">{profile?.clearance_level || 1}</span>
                  </div>
                  <span className="text-slate-500 text-sm font-medium">Уровень допуска</span>
                </div>
              </div>
            </div>

            <div className="pt-6 border-t border-white/5">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-3 px-6 py-4 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-400 hover:to-purple-500 rounded-2xl text-white font-black text-sm uppercase tracking-widest transition-all shadow-lg shadow-purple-500/20 hover:shadow-purple-500/40 disabled:opacity-50"
              >
                {saving ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                    Сохранение...
                  </>
                ) : (
                  <>
                    <Save className="w-5 h-5" />
                    Сохранить изменения
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Security Section */}
        {activeSection === 'security' && (
          <div className="glass-card rounded-3xl p-8 space-y-8 animate-fadeIn">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-red-500/10 rounded-2xl">
                <KeyRound className="w-6 h-6 text-red-400" />
              </div>
              <div>
                <h2 className="text-2xl font-black text-white tracking-tight">Смена пароля</h2>
                <p className="text-slate-500 text-sm">Обновите пароль для входа в систему</p>
              </div>
            </div>

            {pwdMessage && (
              <div
                className={`p-4 rounded-2xl border flex items-center gap-3 ${pwdMessage.toLowerCase().includes('не удалось') || pwdMessage.toLowerCase().includes('совпадают')
                  ? 'bg-red-500/10 border-red-500/20 text-red-300'
                  : 'bg-green-500/10 border-green-500/20 text-green-300'
                  }`}
              >
                {pwdMessage.toLowerCase().includes('не удалось') || pwdMessage.toLowerCase().includes('совпадают') ? (
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                ) : (
                  <CheckCircle className="w-5 h-5 flex-shrink-0" />
                )}
                <p className="font-medium text-sm">{pwdMessage}</p>
              </div>
            )}

            <div className="space-y-5">
              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Текущий пароль</label>
                <div className="relative">
                  <input
                    type="password"
                    value={pwdForm.current}
                    onChange={(e) => setPwdForm({ ...pwdForm, current: e.target.value })}
                    className="w-full px-4 py-4 pl-12 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-red-500/50 focus:bg-white/10 transition-all"
                    placeholder="••••••••"
                  />
                  <Lock className="absolute left-4 top-4 w-5 h-5 text-slate-600" />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Новый пароль</label>
                <div className="relative">
                  <input
                    type="password"
                    value={pwdForm.next}
                    onChange={(e) => setPwdForm({ ...pwdForm, next: e.target.value })}
                    className="w-full px-4 py-4 pl-12 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-red-500/50 focus:bg-white/10 transition-all"
                    placeholder="••••••••"
                  />
                  <Lock className="absolute left-4 top-4 w-5 h-5 text-slate-600" />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Подтверждение</label>
                <div className="relative">
                  <input
                    type="password"
                    value={pwdForm.confirm}
                    onChange={(e) => setPwdForm({ ...pwdForm, confirm: e.target.value })}
                    className={`w-full px-4 py-4 pl-12 bg-white/5 border rounded-2xl text-white placeholder-slate-600 focus:outline-none transition-all ${pwdForm.confirm && pwdForm.confirm === pwdForm.next
                      ? 'border-green-500/50'
                      : pwdForm.confirm && pwdForm.confirm !== pwdForm.next
                        ? 'border-red-500/50'
                        : 'border-white/10 focus:border-red-500/50'
                      }`}
                    placeholder="••••••••"
                  />
                  <Lock className="absolute left-4 top-4 w-5 h-5 text-slate-600" />
                  {pwdForm.confirm && (
                    <div className="absolute right-4 top-4">
                      {pwdForm.confirm === pwdForm.next ? (
                        <CheckCircle className="w-5 h-5 text-green-400" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-red-400" />
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="pt-6 border-t border-white/5">
              <button
                type="button"
                onClick={handleChangePassword}
                disabled={pwdLoading}
                className="flex items-center gap-3 px-6 py-4 bg-gradient-to-r from-red-500 to-orange-600 hover:from-red-400 hover:to-orange-500 rounded-2xl text-white font-black text-sm uppercase tracking-widest transition-all shadow-lg shadow-red-500/20 hover:shadow-red-500/40 disabled:opacity-50"
              >
                {pwdLoading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                    Обновление...
                  </>
                ) : (
                  <>
                    <KeyRound className="w-5 h-5" />
                    Обновить пароль
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Notifications Section */}
        {activeSection === 'notifications' && (
          <div className="glass-card rounded-3xl p-8 space-y-8 animate-fadeIn">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-yellow-500/10 rounded-2xl">
                <Bell className="w-6 h-6 text-yellow-400" />
              </div>
              <div>
                <h2 className="text-2xl font-black text-white tracking-tight">Уведомления</h2>
                <p className="text-slate-500 text-sm">Настройте каналы оповещений</p>
              </div>
            </div>

            <div className="space-y-4">
              <label className="flex items-start gap-4 p-5 bg-white/[0.02] border border-white/5 rounded-2xl hover:bg-white/[0.04] transition-all cursor-pointer group">
                <input type="checkbox" defaultChecked className="mt-1 w-5 h-5 rounded-lg bg-white/10 border-white/20 text-yellow-500 focus:ring-yellow-500/50" />
                <div>
                  <p className="text-white font-bold group-hover:text-yellow-400 transition-colors">Email-уведомления</p>
                  <p className="text-slate-500 text-sm mt-1">Получать уведомления о новых инцидентах на почту</p>
                </div>
              </label>

              <label className="flex items-start gap-4 p-5 bg-white/[0.02] border border-white/5 rounded-2xl hover:bg-white/[0.04] transition-all cursor-pointer group">
                <input type="checkbox" defaultChecked className="mt-1 w-5 h-5 rounded-lg bg-white/10 border-white/20 text-yellow-500 focus:ring-yellow-500/50" />
                <div>
                  <p className="text-white font-bold group-hover:text-yellow-400 transition-colors">Push-уведомления</p>
                  <p className="text-slate-500 text-sm mt-1">Мгновенные оповещения о критичных алертах</p>
                </div>
              </label>

              <label className="flex items-start gap-4 p-5 bg-white/[0.02] border border-white/5 rounded-2xl hover:bg-white/[0.04] transition-all cursor-pointer group">
                <input type="checkbox" className="mt-1 w-5 h-5 rounded-lg bg-white/10 border-white/20 text-yellow-500 focus:ring-yellow-500/50" />
                <div>
                  <p className="text-white font-bold group-hover:text-yellow-400 transition-colors">Ежедневная сводка</p>
                  <p className="text-slate-500 text-sm mt-1">Сводный отчет по активности за сутки</p>
                </div>
              </label>

              <label className="flex items-start gap-4 p-5 bg-white/[0.02] border border-white/5 rounded-2xl hover:bg-white/[0.04] transition-all cursor-pointer group">
                <input type="checkbox" className="mt-1 w-5 h-5 rounded-lg bg-white/10 border-white/20 text-yellow-500 focus:ring-yellow-500/50" />
                <div>
                  <p className="text-white font-bold group-hover:text-yellow-400 transition-colors">Telegram-бот</p>
                  <p className="text-slate-500 text-sm mt-1">Получать уведомления через Telegram</p>
                </div>
              </label>
            </div>
          </div>
        )}

        {/* Mail Accounts Section */}
        {activeSection === 'mail' && (
          <div className="glass-card rounded-3xl p-8 space-y-8 animate-fadeIn">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-cyan-500/10 rounded-2xl">
                  <Inbox className="w-6 h-6 text-cyan-400" />
                </div>
                <div>
                  <h2 className="text-2xl font-black text-white tracking-tight">Почтовые аккаунты</h2>
                  <p className="text-slate-500 text-sm">Подключите ваши почтовые ящики для мониторинга</p>
                </div>
              </div>
              <button
                onClick={() => setShowAddForm(!showAddForm)}
                className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 rounded-2xl text-white font-bold text-sm uppercase tracking-widest transition-all shadow-lg shadow-cyan-500/20"
              >
                {showAddForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
                {showAddForm ? 'Отмена' : 'Добавить'}
              </button>
            </div>

            {/* Message */}
            {mailMessage && (
              <div className={`p-4 rounded-2xl border flex items-center gap-3 ${mailMessage.startsWith('✓') || mailMessage.includes('успешно') || mailMessage.includes('удалён') || mailMessage.includes('запущена')
                ? 'bg-green-500/10 border-green-500/20 text-green-300'
                : 'bg-red-500/10 border-red-500/20 text-red-300'
                }`}>
                {mailMessage.startsWith('✓') || mailMessage.includes('успешно') ? (
                  <CheckCircle className="w-5 h-5 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                )}
                <p className="font-medium text-sm">{mailMessage}</p>
              </div>
            )}

            {/* Add Account Form */}
            {showAddForm && (
              <div className="p-6 bg-white/[0.02] border border-white/10 rounded-2xl space-y-5">
                <h3 className="text-lg font-bold text-white">Новый почтовый аккаунт</h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Название</label>
                    <input
                      type="text"
                      value={newAccount.name}
                      onChange={(e) => setNewAccount({ ...newAccount, name: e.target.value })}
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50"
                      placeholder="Рабочая почта"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Провайдер</label>
                    <select
                      value={newAccount.provider}
                      onChange={(e) => setNewAccount({ ...newAccount, provider: e.target.value })}
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:border-cyan-500/50"
                    >
                      <option value="gmail">Gmail</option>
                      <option value="outlook">Outlook / Office 365</option>
                      <option value="yandex">Яндекс.Почта</option>
                      <option value="mailru">Mail.ru</option>
                      <option value="custom">Другой (IMAP)</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Email</label>
                    <div className="relative">
                      <input
                        type="email"
                        value={newAccount.email}
                        onChange={(e) => setNewAccount({ ...newAccount, email: e.target.value })}
                        className="w-full px-4 py-3 pl-11 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50"
                        placeholder="user@example.com"
                      />
                      <Mail className="absolute left-4 top-3.5 w-4 h-4 text-slate-600" />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Пароль / App Password</label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        value={newAccount.password}
                        onChange={(e) => setNewAccount({ ...newAccount, password: e.target.value })}
                        className="w-full px-4 py-3 pl-11 pr-11 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50"
                        placeholder="••••••••"
                      />
                      <Lock className="absolute left-4 top-3.5 w-4 h-4 text-slate-600" />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-4 top-3.5 text-slate-600 hover:text-slate-400"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                </div>

                {mailProviders.find(p => p.provider === newAccount.provider)?.notes && (
                  <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl text-blue-300 text-sm">
                    💡 {mailProviders.find(p => p.provider === newAccount.provider)?.notes}
                  </div>
                )}

                <div className="flex items-center gap-3 pt-4">
                  <button
                    onClick={handleTestConnection}
                    disabled={testingConnection || !newAccount.email || !newAccount.password}
                    className="flex items-center gap-2 px-5 py-3 bg-white/5 border border-white/10 hover:bg-white/10 rounded-xl text-white font-bold text-sm transition-all disabled:opacity-50"
                  >
                    {testingConnection ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4" />
                    )}
                    Проверить подключение
                  </button>

                  <button
                    onClick={handleAddAccount}
                    disabled={mailLoading || !newAccount.name || !newAccount.email || !newAccount.password}
                    className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 rounded-xl text-white font-bold text-sm transition-all shadow-lg shadow-cyan-500/20 disabled:opacity-50"
                  >
                    {mailLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Plus className="w-4 h-4" />
                    )}
                    Подключить
                  </button>
                </div>
              </div>
            )}

            {/* Accounts List */}
            <div className="space-y-4">
              {mailAccounts.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                  <Inbox className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p className="font-medium">Нет подключённых аккаунтов</p>
                  <p className="text-sm mt-1">Добавьте почтовый ящик для мониторинга угроз</p>
                </div>
              ) : (
                mailAccounts.map((account) => (
                  <div key={account.id} className="p-5 bg-white/[0.02] border border-white/5 rounded-2xl hover:bg-white/[0.04] transition-all">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="p-2 bg-cyan-500/10 rounded-xl">
                          <Mail className="w-5 h-5 text-cyan-400" />
                        </div>
                        <div>
                          <p className="text-white font-bold">{account.name}</p>
                          <p className="text-slate-500 text-sm">{account.email}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className={`px-3 py-1 rounded-lg border text-xs font-bold ${getStatusColor(account.status)}`}>
                          {getStatusLabel(account.status)}
                        </span>

                        <button
                          onClick={() => handleSyncAccount(account.id)}
                          disabled={account.status === 'syncing'}
                          className="p-2 hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
                          title="Синхронизировать"
                        >
                          <RefreshCw className={`w-4 h-4 text-slate-400 ${account.status === 'syncing' ? 'animate-spin' : ''}`} />
                        </button>

                        <button
                          onClick={() => handleDeleteAccount(account.id)}
                          className="p-2 hover:bg-red-500/10 rounded-lg transition-colors"
                          title="Удалить"
                        >
                          <Trash2 className="w-4 h-4 text-red-400" />
                        </button>
                      </div>
                    </div>

                    <div className="mt-3 pt-3 border-t border-white/5 flex items-center gap-6 text-xs text-slate-500">
                      <span>Папка: <strong className="text-slate-400">{account.folder}</strong></span>
                      <span>Провайдер: <strong className="text-slate-400">{account.provider}</strong></span>
                      <span>Писем: <strong className="text-slate-400">{account.total_emails_synced}</strong></span>
                      {account.last_sync_at && (
                        <span>Синхронизация: <strong className="text-slate-400">{new Date(account.last_sync_at).toLocaleString('ru-RU')}</strong></span>
                      )}
                    </div>

                    {account.last_error && (
                      <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300 text-xs">
                        {account.last_error}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}


        {/* Integrations Section */}
        {activeSection === 'integrations' && (
          <div className="glass-card rounded-3xl p-8 space-y-8 animate-fadeIn">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-indigo-500/10 rounded-2xl">
                <Cpu className="w-6 h-6 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-2xl font-black text-white tracking-tight">Системные интеграции</h2>
                <p className="text-slate-500 text-sm">Настройка подключений к внешним сервисам</p>
              </div>
            </div>

            {/* IMAP System Listener */}
            <div className="p-6 bg-white/[0.02] border border-white/10 rounded-2xl space-y-4">
              <div className="flex items-center gap-3 mb-2">
                <Server className="w-5 h-5 text-cyan-400" />
                <h3 className="text-lg font-bold text-white">IMAP Listener (Системный)</h3>
              </div>
              <p className="text-sm text-slate-500 mb-4">
                Основной канал приема писем для анализа. Настраивается через переменные окружения (.env).
              </p>

              <div className="flex items-center justify-between p-4 bg-black/20 rounded-xl border border-white/5">
                <div className="space-y-1">
                  <div className="text-xs font-bold text-slate-500 uppercase">Статус конфигурации</div>
                  <div className="text-sm font-mono text-cyan-300">ENV: IMAP_HOST, IMAP_USER настроены</div>
                </div>
                <button
                  onClick={handleTestSystemImap}
                  disabled={sysImapLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm font-bold transition-all disabled:opacity-50"
                >
                  {sysImapLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                  Проверить связь
                </button>
              </div>
              {sysImapMessage && (
                <div className={`p-3 rounded-xl border flex items-center gap-2 text-sm font-medium ${sysImapMessage.includes('✓') ? 'bg-green-500/10 border-green-500/20 text-green-300' : 'bg-red-500/10 border-red-500/20 text-red-300'
                  }`}>
                  {sysImapMessage}
                </div>
              )}
            </div>

            {/* Gemini AI */}
            <div className="p-6 bg-white/[0.02] border border-white/10 rounded-2xl space-y-4">
              <div className="flex items-center gap-3 mb-2">
                <Zap className="w-5 h-5 text-yellow-400" />
                <h3 className="text-lg font-bold text-white">Gemini AI (Linguistic Analyzer)</h3>
              </div>
              <p className="text-sm text-slate-500 mb-4">
                Модуль лингвистического анализа на базе Google Gemini 2.0 Flash Exp.
                Требуется валидный API Key.
              </p>

              <div className="flex items-center justify-between p-4 bg-black/20 rounded-xl border border-white/5">
                <div className="space-y-1">
                  <div className="text-xs font-bold text-slate-500 uppercase">Конфигурация</div>
                  <div className="text-sm font-mono text-yellow-300">API Key: ************</div>
                </div>
                <button
                  onClick={handleTestGemini}
                  disabled={geminiLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500/20 to-blue-500/20 hover:from-purple-500/30 hover:to-blue-500/30 border border-purple-500/30 rounded-lg text-sm font-bold text-purple-200 transition-all disabled:opacity-50"
                >
                  {geminiLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                  Тестовый запрос
                </button>
              </div>

              {geminiMessage && (
                <div className={`p-3 rounded-xl border flex items-center gap-2 text-sm font-medium ${geminiMessage.includes('✓') ? 'bg-green-500/10 border-green-500/20 text-green-300' : 'bg-red-500/10 border-red-500/20 text-red-300'
                  }`}>
                  {geminiMessage}
                </div>
              )}

              {geminiResult && (
                <div className="mt-4 p-4 bg-black/40 rounded-xl border border-white/5 font-mono text-xs text-slate-400 overflow-x-auto">
                  <pre>{JSON.stringify(geminiResult, null, 2)}</pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Layout >
  );
};
