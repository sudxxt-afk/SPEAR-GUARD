import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, AlertCircle, KeyRound, RefreshCw, Eye, EyeOff, Lock, Mail } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { authApi } from '../services/api';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const [showReset, setShowReset] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [resetPassword, setResetPassword] = useState('');
  const [resetMessage, setResetMessage] = useState('');
  const [resetLoading, setResetLoading] = useState(false);

  const { signIn } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await signIn(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Неверные учетные данные');
    } finally {
      setLoading(false);
    }
  };

  const handleResetRequest = async () => {
    setResetMessage('');
    setResetLoading(true);
    try {
      const token = await authApi.requestPasswordReset(resetEmail);
      if (token) {
        setResetToken(token);
        setResetMessage('Токен сброса получен (для теста показан ниже).');
      } else {
        setResetMessage('Если пользователь существует, письмо со ссылкой отправлено.');
      }
    } catch (err) {
      setResetMessage(err instanceof Error ? err.message : 'Ошибка запроса сброса');
    } finally {
      setResetLoading(false);
    }
  };

  const handleResetConfirm = async () => {
    setResetMessage('');
    setResetLoading(true);
    try {
      await authApi.confirmPasswordReset(resetToken, resetPassword);
      setResetMessage('Пароль сброшен. Войдите с новым паролем.');
    } catch (err) {
      setResetMessage(err instanceof Error ? err.message : 'Ошибка подтверждения сброса');
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Ambient Background */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[60%] bg-blue-600/10 rounded-full blur-[150px] animate-pulse-slow" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[60%] bg-indigo-600/10 rounded-full blur-[150px] animate-pulse-slow" />
      <div className="absolute top-[30%] right-[20%] w-[30%] h-[30%] bg-purple-600/5 rounded-full blur-[100px]" />

      {/* Grid Pattern */}
      <div className="absolute inset-0 opacity-[0.02]" style={{ backgroundImage: 'radial-gradient(#fff 1px, transparent 1px)', backgroundSize: '40px 40px' }} />

      <div className="w-full max-w-md relative z-10 animate-fadeIn">
        {/* Logo Section */}
        <div className="flex flex-col items-center mb-10">
          <div className="relative group mb-6">
            <div className="absolute -inset-3 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl blur-lg opacity-50 group-hover:opacity-80 transition duration-500" />
            <div className="relative w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center shadow-2xl">
              <Shield className="w-10 h-10 text-white" />
            </div>
          </div>
          <h1 className="text-3xl font-black text-white tracking-tighter">SPEAR-GUARD</h1>
          <p className="text-slate-500 text-sm font-medium mt-1 uppercase tracking-[0.3em]">Security Platform</p>
        </div>

        {/* Main Card */}
        <div className="glass-card rounded-3xl p-8 shadow-2xl">
          <h2 className="text-2xl font-black text-white text-center mb-2 tracking-tight">Добро пожаловать</h2>
          <p className="text-slate-500 text-center text-sm mb-8">Войдите в систему для продолжения</p>

          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-start gap-3 animate-fadeIn">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-300 text-sm font-medium">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-bold text-slate-400 mb-2 uppercase tracking-widest">Email</label>
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  className="w-full px-4 py-4 pl-12 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50 focus:bg-white/10 transition-all disabled:opacity-50"
                  placeholder="user@example.com"
                />
                <Mail className="absolute left-4 top-4 w-5 h-5 text-slate-600" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 mb-2 uppercase tracking-widest">Пароль</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  className="w-full px-4 py-4 pl-12 pr-12 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50 focus:bg-white/10 transition-all disabled:opacity-50"
                  placeholder="••••••••"
                />
                <Lock className="absolute left-4 top-4 w-5 h-5 text-slate-600" />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-4 text-slate-600 hover:text-slate-400 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full relative group mt-8"
            >
              <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-2xl blur opacity-50 group-hover:opacity-80 transition duration-300" />
              <div className="relative bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-black py-4 px-4 rounded-2xl transition-all text-sm uppercase tracking-widest disabled:opacity-50 flex items-center justify-center gap-3">
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                    Авторизация...
                  </>
                ) : (
                  'Войти в систему'
                )}
              </div>
            </button>
          </form>

          <div className="mt-8 pt-8 border-t border-white/5">
            <p className="text-center text-sm text-slate-500">
              Нет аккаунта?{' '}
              <button
                onClick={() => navigate('/signup')}
                className="text-blue-400 hover:text-blue-300 font-bold transition-colors"
              >
                Зарегистрироваться
              </button>
            </p>

            <button
              type="button"
              onClick={() => setShowReset((v) => !v)}
              className="mt-6 w-full flex items-center justify-center gap-2 text-sm text-slate-500 hover:text-slate-300 transition-colors py-2"
            >
              <KeyRound className="w-4 h-4" />
              <span className="font-medium">Забыли пароль?</span>
            </button>

            {showReset && (
              <div className="mt-6 bg-white/[0.03] border border-white/5 rounded-2xl p-5 space-y-4 animate-fadeIn">
                <div>
                  <label className="block text-[10px] uppercase tracking-widest font-bold text-slate-500 mb-2">
                    Email для сброса
                  </label>
                  <input
                    type="email"
                    value={resetEmail}
                    onChange={(e) => setResetEmail(e.target.value)}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500/50"
                    placeholder="user@example.com"
                  />
                </div>
                <button
                  type="button"
                  onClick={handleResetRequest}
                  disabled={resetLoading || !resetEmail}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-xl text-blue-400 font-bold text-sm transition-all disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${resetLoading ? 'animate-spin' : ''}`} />
                  Запросить сброс
                </button>

                {resetToken && (
                  <div className="pt-4 border-t border-white/5 space-y-3">
                    <div>
                      <label className="block text-[10px] uppercase tracking-widest font-bold text-slate-500 mb-2">
                        Токен (из email)
                      </label>
                      <textarea
                        value={resetToken}
                        onChange={(e) => setResetToken(e.target.value)}
                        rows={2}
                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white text-sm font-mono focus:outline-none focus:border-blue-500/50"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] uppercase tracking-widest font-bold text-slate-500 mb-2">
                        Новый пароль
                      </label>
                      <input
                        type="password"
                        value={resetPassword}
                        onChange={(e) => setResetPassword(e.target.value)}
                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500/50"
                        placeholder="••••••••"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleResetConfirm}
                      disabled={resetLoading || !resetToken || !resetPassword}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 rounded-xl text-green-400 font-bold text-sm transition-all disabled:opacity-50"
                    >
                      Подтвердить сброс
                    </button>
                  </div>
                )}

                {resetMessage && (
                  <div className="text-xs text-slate-300 bg-white/5 border border-white/10 rounded-xl p-3 font-medium">
                    {resetMessage}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-slate-600 text-xs mt-8 font-medium">
          © 2026 SPEAR-GUARD. Защита корпоративной почты.
        </p>
      </div>
    </div>
  );
};
