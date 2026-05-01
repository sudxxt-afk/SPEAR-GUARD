import React, { useEffect, useState } from 'react';
import { Layout } from '../components/Layout';
import { registryApi } from '../services/api';
import { Plus, Search, Edit2, Trash2, CheckCircle, Shield, Globe, Building2, X, ChevronLeft, ChevronRight } from 'lucide-react';
import type { TrustedRegistry } from '../types';

export const Registry: React.FC = () => {
  const [entries, setEntries] = useState<TrustedRegistry[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    email_address: '',
    domain: '',
    organization: '',
    trust_level: 2,
    notes: '',
  });
  const [page, setPage] = useState(0);
  const [totalCount, setTotalCount] = useState(0);

  const pageSize = 20;

  useEffect(() => {
    loadEntries();
  }, [page]);

  useEffect(() => {
    if (searchQuery) {
      searchEntries();
    } else {
      loadEntries();
    }
  }, [searchQuery]);

  const loadEntries = async () => {
    setLoading(true);
    try {
      const { data, count } = await registryApi.getRegistry(pageSize, page * pageSize);
      setEntries(data);
      setTotalCount(count);
    } catch (error) {
      console.error('Error loading registry:', error);
    } finally {
      setLoading(false);
    }
  };

  const searchEntries = async () => {
    setLoading(true);
    try {
      const results = await registryApi.searchRegistry(searchQuery);
      setEntries(results);
      setTotalCount(results.length);
    } catch (error) {
      console.error('Error searching registry:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddEntry = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const newEntry = await registryApi.createEntry(formData);
      setEntries([newEntry, ...entries.slice(0, pageSize - 1)]);
      setFormData({
        email_address: '',
        domain: '',
        organization: '',
        trust_level: 2,
        notes: '',
      });
      setShowForm(false);
    } catch (error) {
      console.error('Error creating entry:', error);
    }
  };

  const handleDeleteEntry = async (email: string) => {
    try {
      await registryApi.deleteEntry(email);
      setEntries(entries.filter((e) => e.email_address !== email));
    } catch (error) {
      console.error('Error deleting entry:', error);
    }
  };

  const getTrustLevelConfig = (level: number) => {
    switch (level) {
      case 1:
        return { label: 'Максимум', color: 'bg-green-500/10 text-green-400 border-green-500/20', glow: 'glow-green' };
      case 2:
        return { label: 'Высокий', color: 'bg-blue-500/10 text-blue-400 border-blue-500/20', glow: 'glow-blue' };
      case 3:
        return { label: 'Средний', color: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20', glow: '' };
      case 4:
        return { label: 'Наблюдать', color: 'bg-red-500/10 text-red-400 border-red-500/20', glow: '' };
      default:
        return { label: `Уровень ${level}`, color: 'bg-slate-500/10 text-slate-400 border-slate-500/20', glow: '' };
    }
  };

  return (
    <Layout>
      <div className="space-y-8 pb-10">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 animate-fadeIn">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="h-1 w-8 bg-green-500 rounded-full" />
              <p className="text-green-400 text-xs font-black uppercase tracking-[0.2em]">База знаний</p>
            </div>
            <h1 className="text-5xl font-black text-white tracking-tighter">Реестр</h1>
            <p className="text-slate-500 mt-2 font-medium">Управление доверенными отправителями и доменами</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 px-6 py-4 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-400 hover:to-emerald-500 rounded-2xl text-white font-black text-sm uppercase tracking-widest transition-all shadow-lg shadow-green-500/20 hover:shadow-green-500/40"
          >
            {showForm ? <X className="w-5 h-5" /> : <Plus className="w-5 h-5" />}
            {showForm ? 'Закрыть' : 'Добавить'}
          </button>
        </div>

        {/* Add Form */}
        {showForm && (
          <form
            onSubmit={handleAddEntry}
            className="glass-card rounded-3xl p-8 space-y-6 animate-fadeIn border border-green-500/20"
          >
            <div className="flex items-center gap-3 mb-2">
              <div className="p-3 bg-green-500/10 rounded-xl">
                <Plus className="w-6 h-6 text-green-400" />
              </div>
              <h2 className="text-2xl font-black text-white tracking-tight">Новая запись</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Email адрес</label>
                <input
                  type="email"
                  value={formData.email_address}
                  onChange={(e) => setFormData({ ...formData, email_address: e.target.value })}
                  className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-2xl text-white focus:outline-none focus:border-green-500/50 focus:bg-white/10 transition-all"
                  placeholder="user@example.com"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Домен</label>
                <div className="relative">
                  <Globe className="absolute left-4 top-4 w-5 h-5 text-slate-600" />
                  <input
                    type="text"
                    value={formData.domain}
                    onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                    className="w-full px-4 py-4 pl-12 bg-white/5 border border-white/10 rounded-2xl text-white focus:outline-none focus:border-green-500/50 focus:bg-white/10 transition-all"
                    placeholder="example.com"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Организация</label>
                <div className="relative">
                  <Building2 className="absolute left-4 top-4 w-5 h-5 text-slate-600" />
                  <input
                    type="text"
                    value={formData.organization}
                    onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                    className="w-full px-4 py-4 pl-12 bg-white/5 border border-white/10 rounded-2xl text-white focus:outline-none focus:border-green-500/50 focus:bg-white/10 transition-all"
                    placeholder="Название компании"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Уровень доверия</label>
                <div className="grid grid-cols-4 gap-2">
                  {[1, 2, 3, 4].map((level) => {
                    const config = getTrustLevelConfig(level);
                    return (
                      <button
                        key={level}
                        type="button"
                        onClick={() => setFormData({ ...formData, trust_level: level })}
                        className={`py-3 rounded-xl border text-xs font-bold uppercase tracking-wider transition-all ${formData.trust_level === level
                            ? `${config.color} ${config.glow}`
                            : 'bg-white/5 border-white/10 text-slate-500 hover:bg-white/10'
                          }`}
                      >
                        {level}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-500 mb-2 uppercase tracking-widest">Заметки</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-2xl text-white focus:outline-none focus:border-green-500/50 focus:bg-white/10 transition-all resize-none"
                placeholder="Дополнительная информация..."
                rows={3}
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                className="px-8 py-4 bg-gradient-to-r from-green-500 to-emerald-600 rounded-2xl text-white font-black text-sm uppercase tracking-widest transition-all shadow-lg shadow-green-500/20 hover:shadow-green-500/40"
              >
                Сохранить
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-8 py-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-2xl text-slate-400 font-bold text-sm uppercase tracking-widest transition-all"
              >
                Отмена
              </button>
            </div>
          </form>
        )}

        {/* Search */}
        <div className="relative animate-fadeIn" style={{ animationDelay: '0.1s' }}>
          <input
            type="text"
            placeholder="Поиск по email, домену или организации..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-6 py-5 pl-14 bg-white/[0.03] border border-white/5 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/30 focus:bg-white/[0.06] transition-all text-sm"
          />
          <Search className="absolute left-5 top-5 w-5 h-5 text-slate-600" />
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="w-16 h-16 border-4 border-green-500/20 border-t-green-500 rounded-full animate-spin shadow-lg shadow-green-500/20" />
            <p className="text-slate-500 font-bold uppercase tracking-widest text-xs animate-pulse">Загрузка реестра...</p>
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-20 glass-card rounded-3xl border border-dashed border-white/10 animate-fadeIn">
            <Shield className="w-16 h-16 text-slate-600/30 mx-auto mb-4" />
            <p className="text-slate-400 font-bold uppercase tracking-widest text-sm">Реестр пуст</p>
            <p className="text-slate-600 text-xs mt-2">Добавьте первую доверенную запись</p>
          </div>
        ) : (
          <div className="glass-card rounded-3xl overflow-hidden animate-fadeIn" style={{ animationDelay: '0.2s' }}>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="px-6 py-5 text-left text-[10px] font-black text-slate-500 uppercase tracking-widest">Email / Домен</th>
                    <th className="px-6 py-5 text-left text-[10px] font-black text-slate-500 uppercase tracking-widest">Организация</th>
                    <th className="px-6 py-5 text-left text-[10px] font-black text-slate-500 uppercase tracking-widest">Доверие</th>
                    <th className="px-6 py-5 text-left text-[10px] font-black text-slate-500 uppercase tracking-widest">Статус</th>
                    <th className="px-6 py-5 text-right text-[10px] font-black text-slate-500 uppercase tracking-widest">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry, index) => {
                    const trustConfig = getTrustLevelConfig(entry.trust_level);
                    return (
                      <tr
                        key={entry.id}
                        className="border-b border-white/5 hover:bg-white/[0.02] transition-colors group"
                        style={{ animationDelay: `${index * 0.03}s` }}
                      >
                        <td className="px-6 py-5">
                          <div className="space-y-1">
                            {entry.email_address && (
                              <p className="font-mono text-sm text-white font-bold">{entry.email_address}</p>
                            )}
                            {entry.domain && (
                              <p className="font-mono text-xs text-slate-500">{entry.domain}</p>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-5">
                          <span className="text-sm text-slate-400 font-medium">{entry.organization || '—'}</span>
                        </td>
                        <td className="px-6 py-5">
                          <span className={`inline-flex items-center gap-2 text-[10px] font-black px-3 py-1.5 rounded-lg border uppercase tracking-widest ${trustConfig.color}`}>
                            {trustConfig.label}
                          </span>
                        </td>
                        <td className="px-6 py-5">
                          <div className="flex items-center gap-2">
                            {entry.is_verified && (
                              <span className="flex items-center gap-1.5 text-[10px] font-bold text-green-400 uppercase tracking-widest">
                                <CheckCircle className="w-4 h-4" />
                                Верифицирован
                              </span>
                            )}
                            {entry.status && (
                              <span className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                                {entry.status}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-5">
                          <div className="flex gap-2 justify-end opacity-30 group-hover:opacity-100 transition-opacity">
                            <button className="p-2.5 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-xl transition-all">
                              <Edit2 className="w-4 h-4 text-blue-400" />
                            </button>
                            <button
                              onClick={() => entry.email_address && handleDeleteEntry(entry.email_address)}
                              className="p-2.5 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-xl transition-all"
                            >
                              <Trash2 className="w-4 h-4 text-red-400" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Pagination */}
        {totalCount > pageSize && !searchQuery && (
          <div className="flex items-center justify-center gap-4 mt-10 animate-fadeIn">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="p-4 glass border border-white/5 hover:border-white/10 rounded-2xl transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <div className="px-6 py-4 glass border border-white/5 rounded-2xl text-sm font-bold">
              <span className="text-white">{page + 1}</span>
              <span className="text-slate-600"> / {Math.ceil(totalCount / pageSize)}</span>
            </div>
            <button
              onClick={() => setPage(Math.min(Math.ceil(totalCount / pageSize) - 1, page + 1))}
              disabled={page >= Math.ceil(totalCount / pageSize) - 1}
              className="p-4 glass border border-white/5 hover:border-white/10 rounded-2xl transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
};
