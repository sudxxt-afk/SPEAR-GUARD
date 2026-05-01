import React, { useState, useEffect } from 'react';
import {
    Building2,
    Plus,
    Pencil,
    Trash2,
    Users,
    Globe,
    CheckCircle,
    XCircle,
    ChevronDown,
    ChevronRight,
    Loader2,
    AlertCircle,
    UserMinus,
    UserPlus,
    Search
} from 'lucide-react';
import {
    organizationsApi,
    usersApi,
    Organization,
    OrganizationCreate,
    OrganizationUser,
    User
} from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { EmployeeProfileModal } from '../components/EmployeeProfileModal';

const Organizations: React.FC = () => {
    const { user } = useAuth();
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Modal states
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [editingOrg, setEditingOrg] = useState<Organization | null>(null);

    // Expanded org for user list
    const [expandedOrgId, setExpandedOrgId] = useState<number | null>(null);
    const [orgUsers, setOrgUsers] = useState<OrganizationUser[]>([]);
    const [loadingUsers, setLoadingUsers] = useState(false);

    // Add user states
    const [showAddUserModal, setShowAddUserModal] = useState(false);
    const [availableUsers, setAvailableUsers] = useState<User[]>([]);
    const [searchUserQuery, setSearchUserQuery] = useState('');
    const [selectedUserId, setSelectedUserId] = useState<number | null>(null);

    // Profile Modal state
    const [showProfileModal, setShowProfileModal] = useState(false);
    const [profileUserId, setProfileUserId] = useState<number | null>(null);

    // Form state
    const [formData, setFormData] = useState<OrganizationCreate>({
        name: '',
        domain: '',
        description: ''
    });

    // Check if user is admin
    const isAdmin = user?.role === 'admin';

    useEffect(() => {
        if (isAdmin) {
            loadOrganizations();
        }
    }, [isAdmin]);

    const loadOrganizations = async () => {
        try {
            setLoading(true);
            const result = await organizationsApi.list({ include_inactive: true });
            setOrganizations(result.data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load organizations');
        } finally {
            setLoading(false);
        }
    };

    const loadOrgUsers = async (orgId: number) => {
        try {
            setLoadingUsers(true);
            const result = await organizationsApi.listUsers(orgId);
            setOrgUsers(result.data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load users');
        } finally {
            setLoadingUsers(false);
        }
    };

    const handleToggleExpand = async (orgId: number) => {
        if (expandedOrgId === orgId) {
            setExpandedOrgId(null);
            setOrgUsers([]);
        } else {
            setExpandedOrgId(orgId);
            await loadOrgUsers(orgId);
        }
    };

    const handleCreateOrg = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await organizationsApi.create(formData);
            setSuccess('Организация успешно создана');
            setShowCreateModal(false);
            setFormData({ name: '', domain: '', description: '' });
            loadOrganizations();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create organization');
        }
    };

    const handleUpdateOrg = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingOrg) return;

        try {
            await organizationsApi.update(editingOrg.id, formData);
            setSuccess('Организация успешно обновлена');
            setShowEditModal(false);
            setEditingOrg(null);
            setFormData({ name: '', domain: '', description: '' });
            loadOrganizations();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to update organization');
        }
    };

    const handleDeleteOrg = async (orgId: number) => {
        if (!confirm('Вы уверены, что хотите удалить эту организацию?')) return;

        try {
            await organizationsApi.delete(orgId);
            setSuccess('Организация удалена');
            loadOrganizations();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to delete organization');
        }
    };



    const loadAvailableUsers = async () => {
        try {
            const users = await usersApi.list({ exclude_org_members: true });
            setAvailableUsers(users);
        } catch (err) {
            console.error('Failed to load users', err);
        }
    };

    const handleAddUserClick = (orgId: number) => {
        setExpandedOrgId(orgId);
        setShowAddUserModal(true);
        loadAvailableUsers();
    };

    const handleConfirmAddUser = async () => {
        if (!expandedOrgId || !selectedUserId) return;

        try {
            await organizationsApi.addUser(expandedOrgId, selectedUserId);
            setSuccess('Пользователь добавлен в организацию');
            setShowAddUserModal(false);
            setSelectedUserId(null);
            loadOrgUsers(expandedOrgId);
            loadOrganizations(); // Refresh counts
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to add user');
        }
    };

    const filteredUsers = availableUsers.filter(u =>
        u.email.toLowerCase().includes(searchUserQuery.toLowerCase()) ||
        u.full_name.toLowerCase().includes(searchUserQuery.toLowerCase())
    );

    const handleRemoveUser = async (orgId: number, userId: number) => {
        if (!confirm('Удалить пользователя из организации?')) return;

        try {
            await organizationsApi.removeUser(orgId, userId);
            setSuccess('Пользователь удалён из организации');
            loadOrgUsers(orgId);
            loadOrganizations();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to remove user');
        }
    };

    const openEditModal = (org: Organization) => {
        setEditingOrg(org);
        setFormData({
            name: org.name,
            domain: org.domain || '',
            description: org.description || ''
        });
        setShowEditModal(true);
    };

    // Clear messages after 5 seconds
    useEffect(() => {
        if (error || success) {
            const timer = setTimeout(() => {
                setError(null);
                setSuccess(null);
            }, 5000);
            return () => clearTimeout(timer);
        }
    }, [error, success]);

    if (!isAdmin) {
        return (
            <div className="p-6 text-center">
                <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-white mb-2">Доступ запрещён</h2>
                <p className="text-slate-400">Эта страница доступна только администраторам</p>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-8 pb-10">
            {/* Header */}
            <div className="flex items-end justify-between animate-fadeIn">
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <span className="h-1 w-8 bg-blue-500 rounded-full" />
                        <p className="text-blue-400 text-xs font-black uppercase tracking-[0.2em]">Администрирование</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <Building2 className="w-8 h-8 text-white/80" />
                        <h1 className="text-4xl font-black text-white tracking-tighter">Организации</h1>
                    </div>
                </div>
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="btn-primary flex items-center gap-2"
                >
                    <Plus className="w-5 h-5" />
                    Создать организацию
                </button>
            </div>

            {/* Messages */}
            {error && (
                <div className="card-danger p-4 flex items-center gap-3 text-red-200 animate-slide-up">
                    <AlertCircle className="w-5 h-5 text-red-500" />
                    {error}
                </div>
            )}
            {success && (
                <div className="card-success p-4 flex items-center gap-3 text-green-200 animate-slide-up">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    {success}
                </div>
            )}

            {/* Loading */}
            {loading ? (
                <div className="flex flex-col items-center justify-center py-20 gap-4">
                    <Loader2 className="w-10 h-10 animate-spin text-blue-500" />
                    <p className="text-slate-500 font-bold uppercase tracking-widest text-xs animate-pulse">Загрузка данных...</p>
                </div>
            ) : (
                /* Organizations List */
                <div className="glass-card rounded-3xl border border-white/10 overflow-hidden">
                    {organizations.length === 0 ? (
                        <div className="p-12 text-center text-slate-500">
                            <Building2 className="w-16 h-16 mx-auto mb-4 opacity-20" />
                            <p className="font-medium text-lg">Организации не найдены</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-white/10">
                            {organizations.map((org) => (
                                <div key={org.id} className="hover:bg-white/[0.02] transition-colors group">
                                    {/* Organization Row */}
                                    <div className="p-6 flex items-center justify-between">
                                        <div className="flex items-center gap-6">
                                            <button
                                                onClick={() => handleToggleExpand(org.id)}
                                                className="p-2 hover:bg-white/10 rounded-lg transition-colors text-slate-400 hover:text-white"
                                            >
                                                {expandedOrgId === org.id ? (
                                                    <ChevronDown className="w-5 h-5" />
                                                ) : (
                                                    <ChevronRight className="w-5 h-5" />
                                                )}
                                            </button>

                                            <div className="w-12 h-12 bg-blue-500/10 rounded-2xl flex items-center justify-center border border-blue-500/20 group-hover:border-blue-500/40 transition-colors">
                                                <Building2 className="w-6 h-6 text-blue-400" />
                                            </div>

                                            <div>
                                                <div className="flex items-center gap-3">
                                                    <h3 className="text-xl font-bold text-white tracking-tight">{org.name}</h3>
                                                    {org.is_active ? (
                                                        <span className="badge-green">
                                                            Активна
                                                        </span>
                                                    ) : (
                                                        <span className="badge-red">
                                                            Неактивна
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-6 text-sm text-slate-400 mt-1">
                                                    {org.domain && (
                                                        <span className="flex items-center gap-1.5">
                                                            <Globe className="w-4 h-4 text-slate-500" />
                                                            {org.domain}
                                                        </span>
                                                    )}
                                                    <span className="flex items-center gap-1.5">
                                                        <Users className="w-4 h-4 text-slate-500" />
                                                        {org.user_count} пользователей
                                                    </span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button
                                                onClick={() => openEditModal(org)}
                                                className="p-2 hover:bg-blue-500/10 rounded-lg transition-colors text-blue-400 border border-transparent hover:border-blue-500/20"
                                                title="Редактировать"
                                            >
                                                <Pencil className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => handleDeleteOrg(org.id)}
                                                className="p-2 hover:bg-red-500/10 rounded-lg transition-colors text-red-400 border border-transparent hover:border-red-500/20"
                                                title="Удалить"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>

                                    {/* Expanded Users List */}
                                    {expandedOrgId === org.id && (
                                        <div className="bg-black/20 border-t border-white/5 p-6 animate-slide-in">
                                            <div className="flex items-center justify-between mb-4">
                                                <h4 className="font-bold text-slate-300 flex items-center gap-2 uppercase text-xs tracking-wider">
                                                    <Users className="w-4 h-4" />
                                                    Пользователи организации
                                                </h4>
                                                <button
                                                    onClick={() => handleAddUserClick(org.id)}
                                                    className="text-xs font-bold text-blue-400 hover:text-blue-300 uppercase tracking-wider flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-blue-500/10 transition-colors"
                                                >
                                                    <UserPlus className="w-3.5 h-3.5" />
                                                    Добавить
                                                </button>
                                            </div>

                                            {loadingUsers ? (
                                                <div className="flex items-center justify-center py-6">
                                                    <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                                                </div>
                                            ) : orgUsers.length === 0 ? (
                                                <div className="text-center py-6 border border-dashed border-white/10 rounded-xl">
                                                    <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">
                                                        Нет пользователей
                                                    </p>
                                                </div>
                                            ) : (
                                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                                    {orgUsers.map((u) => (
                                                        <div
                                                            key={u.id}
                                                            onClick={() => {
                                                                setProfileUserId(u.id);
                                                                setShowProfileModal(true);
                                                            }}
                                                            className="flex items-center justify-between bg-white/5 p-4 rounded-xl border border-white/5 hover:border-blue-500/30 hover:bg-white/10 transition-all cursor-pointer group/user"
                                                        >
                                                            <div className="min-w-0 pr-4">
                                                                <div className="flex items-center gap-2 mb-1">
                                                                    <span className="font-bold text-slate-200 truncate group-hover/user:text-blue-300 transition-colors">{u.full_name}</span>
                                                                    <span className={
                                                                        u.role === 'admin' ? 'badge-purple' :
                                                                            u.role === 'security_officer' ? 'badge-blue' :
                                                                                'badge text-slate-400 border-slate-700'
                                                                    }>
                                                                        {u.role === 'admin' ? 'ADMIN' :
                                                                            u.role === 'security_officer' ? 'OFFICER' : 'USER'}
                                                                    </span>
                                                                </div>
                                                                <span className="text-xs font-medium text-slate-500 truncate block">{u.email}</span>
                                                            </div>
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    handleRemoveUser(org.id, u.id);
                                                                }}
                                                                className="p-1.5 hover:bg-red-500/10 rounded-lg text-slate-600 hover:text-red-400 transition-colors opacity-0 group-hover/user:opacity-100"
                                                                title="Удалить из организации"
                                                            >
                                                                <UserMinus className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Profile Modal */}
            {showProfileModal && profileUserId && (
                <EmployeeProfileModal
                    userId={profileUserId}
                    onClose={() => setShowProfileModal(false)}
                />
            )}

            {/* Create Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 animate-fadeIn">
                    <div className="glass-card rounded-3xl shadow-2xl max-w-md w-full mx-4 p-8 border border-white/10">
                        <div className="flex items-center justify-between mb-8">
                            <h2 className="text-2xl font-black text-white tracking-tight">Новая организация</h2>
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="text-slate-500 hover:text-white transition-colors"
                            >
                                <XCircle className="w-6 h-6" />
                            </button>
                        </div>

                        <form onSubmit={handleCreateOrg} className="space-y-6">
                            <div>
                                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                                    Название *
                                </label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="input-dark"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                                    Домен
                                </label>
                                <input
                                    type="text"
                                    value={formData.domain}
                                    onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                                    placeholder="example.com"
                                    className="input-dark"
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                                    Описание
                                </label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    rows={3}
                                    className="input-dark resize-none"
                                />
                            </div>

                            <div className="flex justify-end gap-3 pt-4">
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    className="btn-ghost"
                                >
                                    Отмена
                                </button>
                                <button
                                    type="submit"
                                    className="btn-primary"
                                >
                                    Создать
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Edit Modal */}
            {showEditModal && editingOrg && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 animate-fadeIn">
                    <div className="glass-card rounded-3xl shadow-2xl max-w-md w-full mx-4 p-8 border border-white/10">
                        <div className="flex items-center justify-between mb-8">
                            <h2 className="text-2xl font-black text-white tracking-tight">Редактирование</h2>
                            <button
                                onClick={() => {
                                    setShowEditModal(false);
                                    setEditingOrg(null);
                                }}
                                className="text-slate-500 hover:text-white transition-colors"
                            >
                                <XCircle className="w-6 h-6" />
                            </button>
                        </div>

                        <form onSubmit={handleUpdateOrg} className="space-y-6">
                            <div>
                                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                                    Название *
                                </label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="input-dark"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                                    Домен
                                </label>
                                <input
                                    type="text"
                                    value={formData.domain}
                                    onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                                    placeholder="example.com"
                                    className="input-dark"
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                                    Описание
                                </label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    rows={3}
                                    className="input-dark resize-none"
                                />
                            </div>

                            <div className="flex justify-end gap-3 pt-4">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowEditModal(false);
                                        setEditingOrg(null);
                                    }}
                                    className="btn-ghost"
                                >
                                    Отмена
                                </button>
                                <button
                                    type="submit"
                                    className="btn-primary"
                                >
                                    Сохранить
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Add User Modal */}
            {showAddUserModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 animate-fadeIn">
                    <div className="glass-card rounded-3xl shadow-2xl max-w-md w-full mx-4 p-8 border border-white/10 h-[600px] flex flex-col">
                        <div className="flex items-center justify-between mb-6 flex-shrink-0">
                            <h2 className="text-2xl font-black text-white tracking-tight">Добавить пользователя</h2>
                            <button
                                onClick={() => setShowAddUserModal(false)}
                                className="text-slate-500 hover:text-white transition-colors"
                            >
                                <XCircle className="w-6 h-6" />
                            </button>
                        </div>

                        <div className="relative mb-4 flex-shrink-0">
                            <Search className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                            <input
                                type="text"
                                placeholder="Поиск пользователя..."
                                value={searchUserQuery}
                                onChange={(e) => setSearchUserQuery(e.target.value)}
                                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 pl-10 text-sm focus:outline-none focus:border-blue-500/50 text-white"
                            />
                        </div>

                        <div className="flex-1 overflow-y-auto custom-scrollbar space-y-2 pr-2">
                            {filteredUsers.length === 0 ? (
                                <div className="text-center py-8 text-slate-500">
                                    <p className="text-sm">Пользователи не найдены</p>
                                    <p className="text-xs mt-1">Возможно, все пользователи уже состоят в организациях</p>
                                </div>
                            ) : (
                                filteredUsers.map(user => (
                                    <div
                                        key={user.id}
                                        onClick={() => setSelectedUserId(user.id)}
                                        className={`p-3 rounded-xl border cursor-pointer transition-all ${selectedUserId === user.id
                                            ? 'bg-blue-500/20 border-blue-500/50'
                                            : 'bg-white/5 border-white/5 hover:bg-white/10'
                                            }`}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <p className="font-bold text-white text-sm">{user.full_name}</p>
                                                <p className="text-xs text-slate-400">{user.email}</p>
                                            </div>
                                            {selectedUserId === user.id && (
                                                <CheckCircle className="w-5 h-5 text-blue-400" />
                                            )}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>

                        <div className="flex justify-end gap-3 pt-6 flex-shrink-0 border-t border-white/10 mt-2">
                            <button
                                onClick={() => setShowAddUserModal(false)}
                                className="btn-ghost"
                            >
                                Отмена
                            </button>
                            <button
                                onClick={handleConfirmAddUser}
                                disabled={!selectedUserId}
                                className={`btn-primary ${!selectedUserId ? 'opacity-50 cursor-not-allowed' : ''}`}
                            >
                                Добавить
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Organizations;
