import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Shield, AlertCircle, CheckCircle, Mail, Lock, Eye, EyeOff, UserPlus, Sparkles } from 'lucide-react';

export const Signup: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const validatePassword = () => {
    if (password.length < 6) {
      setError('Пароль должен быть не короче 6 символов');
      return false;
    }
    if (password !== confirmPassword) {
      setError('Пароли не совпадают');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!validatePassword()) return;

    setLoading(true);

    try {
      await signUp(email, password);
      setSuccess('Аккаунт создан! Проверьте почту для подтверждения.');
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка создания аккаунта');
    } finally {
      setLoading(false);
    }
  };

  // Password strength indicator
  const getPasswordStrength = () => {
    if (password.length === 0) return { level: 0, text: '', color: '' };
    if (password.length < 6) return { level: 1, text: 'Слабый', color: 'bg-red-500' };
    if (password.length < 8) return { level: 2, text: 'Средний', color: 'bg-yellow-500' };
    if (password.length >= 8 && /[A-Z]/.test(password) && /[0-9]/.test(password)) {
      return { level: 4, text: 'Сильный', color: 'bg-green-500' };
    }
    return { level: 3, text: 'Хороший', color: 'bg-blue-500' };
  };

  const strength = getPasswordStrength();

  return (
    <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Ambient Background */}
      <div className="absolute top-[-20%] right-[-10%] w-[50%] h-[60%] bg-emerald-600/10 rounded-full blur-[150px] animate-pulse-slow" />
      <div className="absolute bottom-[-20%] left-[-10%] w-[50%] h-[60%] bg-blue-600/10 rounded-full blur-[150px] animate-pulse-slow" />
      <div className="absolute top-[40%] left-[30%] w-[30%] h-[30%] bg-purple-600/5 rounded-full blur-[100px]" />

      {/* Grid Pattern */}
      <div className="absolute inset-0 opacity-[0.02]" style={{ backgroundImage: 'radial-gradient(#fff 1px, transparent 1px)', backgroundSize: '40px 40px' }} />

      <div className="w-full max-w-md relative z-10 animate-fadeIn">
        {/* Logo Section */}
        <div className="flex flex-col items-center mb-10">
          <div className="relative group mb-6">
            <div className="absolute -inset-3 bg-gradient-to-br from-emerald-500 to-blue-600 rounded-2xl blur-lg opacity-50 group-hover:opacity-80 transition duration-500" />
            <div className="relative w-20 h-20 bg-gradient-to-br from-emerald-500 to-blue-600 rounded-2xl flex items-center justify-center shadow-2xl">
              <Shield className="w-10 h-10 text-white" />
            </div>
          </div>
          <h1 className="text-3xl font-black text-white tracking-tighter">SPEAR-GUARD</h1>
          <p className="text-slate-500 text-sm font-medium mt-1 uppercase tracking-[0.3em]">Security Platform</p>
        </div>

        {/* Main Card */}
        <div className="glass-card rounded-3xl p-8 shadow-2xl">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Sparkles className="w-5 h-5 text-emerald-400" />
            <h2 className="text-2xl font-black text-white tracking-tight">Регистрация</h2>
          </div>
          <p className="text-slate-500 text-center text-sm mb-8">Создайте аккаунт для начала работы</p>

          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-start gap-3 animate-fadeIn">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-300 text-sm font-medium">{error}</p>
            </div>
          )}

          {success && (
            <div className="mb-6 p-4 bg-green-500/10 border border-green-500/20 rounded-2xl flex items-start gap-3 animate-fadeIn">
              <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
              <p className="text-green-300 text-sm font-medium">{success}</p>
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
                  className="w-full px-4 py-4 pl-12 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500/50 focus:bg-white/10 transition-all disabled:opacity-50"
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
                  className="w-full px-4 py-4 pl-12 pr-12 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500/50 focus:bg-white/10 transition-all disabled:opacity-50"
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
              {/* Password Strength */}
              {password.length > 0 && (
                <div className="mt-3 space-y-2">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4].map((i) => (
                      <div
                        key={i}
                        className={`h-1 flex-1 rounded-full transition-all ${i <= strength.level ? strength.color : 'bg-white/10'}`}
                      />
                    ))}
                  </div>
                  <p className={`text-[10px] font-bold uppercase tracking-widest ${strength.level >= 3 ? 'text-green-400' : strength.level >= 2 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {strength.text}
                  </p>
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 mb-2 uppercase tracking-widest">Подтверждение</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={loading}
                  className={`w-full px-4 py-4 pl-12 bg-white/5 border rounded-2xl text-white placeholder-slate-600 focus:outline-none transition-all disabled:opacity-50 ${confirmPassword && confirmPassword === password
                      ? 'border-green-500/50 focus:border-green-500/50'
                      : confirmPassword && confirmPassword !== password
                        ? 'border-red-500/50 focus:border-red-500/50'
                        : 'border-white/10 focus:border-emerald-500/50'
                    }`}
                  placeholder="••••••••"
                />
                <Lock className="absolute left-4 top-4 w-5 h-5 text-slate-600" />
                {confirmPassword && (
                  <div className="absolute right-4 top-4">
                    {confirmPassword === password ? (
                      <CheckCircle className="w-5 h-5 text-green-400" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-red-400" />
                    )}
                  </div>
                )}
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full relative group mt-8"
            >
              <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500 to-blue-600 rounded-2xl blur opacity-50 group-hover:opacity-80 transition duration-300" />
              <div className="relative bg-gradient-to-r from-emerald-500 to-blue-600 text-white font-black py-4 px-4 rounded-2xl transition-all text-sm uppercase tracking-widest disabled:opacity-50 flex items-center justify-center gap-3">
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                    Создание...
                  </>
                ) : (
                  <>
                    <UserPlus className="w-5 h-5" />
                    Создать аккаунт
                  </>
                )}
              </div>
            </button>
          </form>

          <div className="mt-8 pt-8 border-t border-white/5">
            <p className="text-center text-sm text-slate-500">
              Уже есть аккаунт?{' '}
              <button
                onClick={() => navigate('/login')}
                className="text-blue-400 hover:text-blue-300 font-bold transition-colors"
              >
                Войти
              </button>
            </p>
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
