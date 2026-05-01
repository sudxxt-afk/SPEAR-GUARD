import type {
  Profile,
  TrustedRegistry,
  EmailAnalysis,
  Alert,
  Anomaly,
  SenderProfile,
  DashboardStats,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'spear_guard_token';
const REFRESH_TOKEN_KEY = 'spear_guard_refresh';
const PROFILE_KEY = 'spear_guard_profile';

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function saveToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

function saveRefreshToken(token: string | null) {
  if (!token) {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  } else {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  }
}

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_URL}${path}`;
  const headers = new Headers(options.headers || {});

  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const contentType = headers.get('Content-Type');
  if (options.body && !contentType) {
    headers.set('Content-Type', 'application/json');
  }

  let response = await fetch(url, { ...options, headers });

  // Try silent refresh once on 401
  if (response.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      headers.set('Authorization', `Bearer ${getToken() ?? ''}`);
      response = await fetch(url, { ...options, headers });
    }
  }

  if (!response.ok) {
    let message = `API request failed: ${response.status}`;
    try {
      const data = await response.json();
      message = data.detail || data.error || message;
    } catch {
      const text = await response.text();
      message = text || message;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return (await response.json()) as T;
}

export const profileApi = {
  async getProfile(): Promise<Profile | null> {
    const stored = localStorage.getItem(PROFILE_KEY);
    return stored ? (JSON.parse(stored) as Profile) : null;
  },

  async saveProfile(profile: Profile): Promise<void> {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
  },

  async updateProfile(userId: string, updates: Partial<Profile>): Promise<Profile> {
    const existing = await this.getProfile();
    if (!existing || existing.user_id !== userId) {
      throw new Error('Profile not found');
    }
    const updated: Profile = { ...existing, ...updates, updated_at: new Date().toISOString() };
    localStorage.setItem(PROFILE_KEY, JSON.stringify(updated));
    return updated;
  },
};

export const authApi = {
  async login(email: string, password: string): Promise<{ token: string; user: Profile }> {
    const body = new URLSearchParams();
    body.append('username', email);
    body.append('password', password);

    const res = await apiRequest<any>('/api/v1/auth/login', {
      method: 'POST',
      body,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    saveRefreshToken(res.refresh_token ?? null);
    return {
      token: res.access_token as string,
      user: {
        id: String(res.user.id),
        user_id: String(res.user.id),
        email: res.user.email,
        full_name: res.user.full_name || res.user.email,
        department: null,
        job_role: res.user.role || 'user',
        clearance_level: 1,
        avatar_url: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    };
  },

  async signup(email: string, fullName: string, password: string): Promise<{ token: string; user: Profile }> {
    const payload = { email, full_name: fullName, password };
    const res = await apiRequest<any>('/api/v1/auth/signup', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    saveRefreshToken(res.refresh_token ?? null);
    return {
      token: res.access_token as string,
      user: {
        id: String(res.user.id),
        user_id: String(res.user.id),
        email: res.user.email,
        full_name: res.user.full_name || res.user.email,
        department: null,
        job_role: res.user.role || 'user',
        clearance_level: 1,
        avatar_url: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    };
  },

  async me(): Promise<Profile | null> {
    try {
      const res = await apiRequest<any>('/api/v1/auth/me');
      return {
        id: String(res.id),
        user_id: String(res.id),
        email: res.email,
        full_name: res.full_name,
        department: res.department ?? null,
        job_role: res.role ?? null,
        clearance_level: 1,
        avatar_url: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    } catch {
      return null;
    }
  },

  async refresh(): Promise<string | null> {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return null;
    try {
      const res = await apiRequest<any>('/api/v1/auth/refresh', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      saveToken(res.access_token);
      saveRefreshToken(res.refresh_token ?? null);
      return res.access_token as string;
    } catch {
      clearAuthStorage();
      return null;
    }
  },

  async requestPasswordReset(email: string): Promise<string | null> {
    const res = await apiRequest<any>('/api/v1/auth/reset-password/request', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
    return res.reset_token ?? null;
  },

  async confirmPasswordReset(resetToken: string, newPassword: string): Promise<void> {
    await apiRequest('/api/v1/auth/reset-password/confirm', {
      method: 'POST',
      body: JSON.stringify({ reset_token: resetToken, new_password: newPassword }),
    });
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await apiRequest('/api/v1/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  },
};

export const registryApi = {
  async getRegistry(limit = 20, offset = 0): Promise<{ data: TrustedRegistry[]; count: number }> {
    const page = Math.floor(offset / limit) + 1;
    const url = new URL(`${API_URL}/api/v1/registry`);
    url.searchParams.set('page', page.toString());
    url.searchParams.set('per_page', limit.toString());

    const res = await apiRequest<{
      items: any[];
      total: number;
    }>(url.toString());

    const mapped = (res.items || []).map((item) => mapRegistry(item));
    return { data: mapped, count: res.total ?? mapped.length };
  },

  async searchRegistry(query: string): Promise<TrustedRegistry[]> {
    const url = new URL(`${API_URL}/api/v1/registry`);
    url.searchParams.set('search', query);
    url.searchParams.set('per_page', '50');
    const res = await apiRequest<{ items: any[] }>(url.toString());
    return (res.items || []).map((item) => mapRegistry(item));
  },

  async createEntry(entry: Partial<TrustedRegistry>): Promise<TrustedRegistry> {
    const payload = {
      email_address: entry.email_address,
      domain: entry.domain,
      organization_name: entry.organization,
      trust_level: entry.trust_level ?? 4,
    };
    const res = await apiRequest<any>('/api/v1/registry', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return mapRegistry(res);
  },

  async updateEntry(email: string, updates: Partial<TrustedRegistry>): Promise<TrustedRegistry> {
    const payload: Record<string, any> = {};
    if (updates.organization) {
      payload.organization_name = updates.organization;
    }
    if (updates.trust_level) {
      payload.trust_level = updates.trust_level;
    }
    if (typeof updates.is_active === 'boolean') {
      payload.is_active = updates.is_active;
    }

    const res = await apiRequest<any>(`/api/v1/registry/${encodeURIComponent(email)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    return mapRegistry(res);
  },

  async deleteEntry(email: string): Promise<void> {
    await apiRequest(`/api/v1/registry/${encodeURIComponent(email)}`, { method: 'DELETE' });
  },
};

function mapRegistry(raw: any): TrustedRegistry {
  return {
    id: String(raw.id),
    email_address: raw.email_address ?? '',
    domain: raw.domain ?? '',
    organization: raw.organization_name ?? '',
    trust_level: raw.trust_level ?? 4,
    spf_configured: raw.spf_configured ?? false,
    dkim_configured: raw.dkim_configured ?? false,
    dmarc_configured: raw.dmarc_configured ?? false,
    notes: raw.notes ?? '',
    created_at: raw.created_at ?? '',
    updated_at: raw.updated_at ?? '',
    created_by: raw.added_by ? String(raw.added_by) : '',
    is_verified: Boolean(raw.is_verified),
    is_active: raw.is_active ?? true,
    status: raw.status ?? 'pending',
  };
}

export const analysisApi = {
  async getAnalysis(limit = 20, offset = 0): Promise<{ data: EmailAnalysis[]; count: number }> {
    const url = new URL(`${API_URL}/api/v1/analysis/`);
    url.searchParams.set('limit', limit.toString());
    url.searchParams.set('offset', offset.toString());

    const res = await apiRequest<{ data: any[]; count: number }>(url.toString());
    return {
      data: (res.data || []).map(mapAnalysis),
      count: res.count ?? 0,
    };
  },

  async getAnalysisById(id: string): Promise<EmailAnalysis | null> {
    try {
      const res = await apiRequest<any>(`/api/v1/analysis/${id}`);
      return mapAnalysis(res);
    } catch (error) {
      console.error('Failed to load analysis', error);
      return null;
    }
  },

  async createAnalysis(_: Partial<EmailAnalysis>): Promise<EmailAnalysis> {
    throw new Error('Not implemented');
  },
};

export const alertsApi = {
  async getAlerts(limit = 20, offset = 0, status?: string): Promise<{ data: Alert[]; count: number }> {
    const url = new URL(`${API_URL}/api/v1/alerts/`);
    url.searchParams.set('limit', limit.toString());
    url.searchParams.set('offset', offset.toString());
    if (status) {
      url.searchParams.set('status_filter', status);
    }
    const res = await apiRequest<{ data: any[]; count: number }>(url.toString());
    return {
      data: (res.data || []).map(mapAlert),
      count: res.count ?? 0,
    };
  },

  async getOpenAlerts(): Promise<Alert[]> {
    const res = await apiRequest<any[]>('/api/v1/alerts/open');
    return (res || []).map(mapAlert);
  },

  async createAlert(alert: Partial<Alert>): Promise<Alert> {
    const payload = {
      email_analysis_id: alert.email_analysis_id,
      alert_type: alert.alert_type,
      severity: alert.severity,
      title: alert.title,
      description: alert.description,
      message: alert.message,
      recipient_email: alert.recipient_email,
      sender_email: alert.sender_email,
      action_taken: alert.action_taken,
      status: alert.status,
    };
    const res = await apiRequest<any>('/api/v1/alerts/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return mapAlert(res);
  },

  async updateAlert(id: string, updates: Partial<Alert>): Promise<Alert> {
    const res = await apiRequest<any>(`/api/v1/alerts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
    return mapAlert(res);
  },

  async acknowledgeAlert(id: string, userId: string): Promise<Alert> {
    const res = await apiRequest<any>(`/api/v1/alerts/${id}/ack`, {
      method: 'POST',
      body: JSON.stringify({ acknowledged_by: userId }),
    });
    return mapAlert(res);
  },
};

export const senderProfileApi = {
  async getSenderProfiles(): Promise<{ data: SenderProfile[]; count: number }> {
    return { data: [], count: 0 };
  },

  async getSuspiciousSenders(): Promise<SenderProfile[]> {
    return [];
  },
};

export const anomaliesApi = {
  async getAnomalies(): Promise<{ data: Anomaly[]; count: number }> {
    return { data: [], count: 0 };
  },

  async getRecentAnomalies(): Promise<Anomaly[]> {
    return [];
  },
};

export async function getDashboardStats(): Promise<DashboardStats> {
  try {
    return await apiRequest<DashboardStats>('/api/v1/dashboard/stats');
  } catch (error) {
    console.error('Failed to load dashboard stats from analytics API, falling back...', error);
    // Minimal fallback logic if analytics API fails
    const analysis = await apiRequest<{ count: number }>('/api/v1/analysis?limit=1');
    return {
      totalEmails: analysis.count || 0,
      suspiciousEmails: 0,
      alertsOpen: 0,
      registrySize: 0,
      lastAnalysis: new Date().toISOString(),
      riskTrend: [],
    };
  }
}

export function setAuthToken(token: string) {
  saveToken(token);
}

export function setRefreshToken(token: string | null) {
  saveRefreshToken(token);
}

export function clearAuthStorage() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(PROFILE_KEY);
}

async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      clearAuthStorage();
      return false;
    }
    const data = await res.json();
    saveToken(data.access_token);
    saveRefreshToken(data.refresh_token ?? null);
    return true;
  } catch {
    clearAuthStorage();
    return false;
  }
}

function mapAnalysis(raw: any): EmailAnalysis {
  return {
    id: String(raw.id),
    sender_email: raw.sender_email ?? raw.from_address ?? '',
    recipient_email: raw.recipient_email ?? raw.to_address ?? '',
    subject: raw.subject ?? null,
    body_preview: raw.body_preview ?? null,
    body_text: raw.body_text ?? raw.body_preview ?? null,
    technical_score: Number(raw.technical_score ?? 0),
    linguistic_score: Number(raw.linguistic_score ?? 0),
    behavioral_score: Number(raw.behavioral_score ?? 0),
    contextual_score: Number(raw.contextual_score ?? 0),
    risk_score: Number(raw.risk_score ?? 0),
    decision: (raw.decision ?? 'PENDING') as EmailAnalysis['decision'],
    explanation: raw.explanation ?? null,
    analysis_details: raw.analysis_details ?? null,
    has_attachments: Boolean(raw.has_attachments),
    attachment_count: Number(raw.attachment_count ?? 0),
    suspicious_urls: raw.suspicious_urls ?? [],
    created_at: raw.created_at ?? new Date().toISOString(),
    analyzed_at: raw.analyzed_at ?? null,
    analyzed_by: raw.analyzed_by ? String(raw.analyzed_by) : null,
  };
}

function mapAlert(raw: any): Alert {
  return {
    id: String(raw.id),
    email_analysis_id: raw.email_analysis_id ? String(raw.email_analysis_id) : null,
    alert_type: raw.alert_type ?? 'unknown',
    severity: (raw.severity ?? 'LOW').toUpperCase() as Alert['severity'],
    title: raw.title ?? '',
    description: raw.description ?? null,
    message: raw.message ?? null,
    recipient_email: raw.recipient_email ?? '',
    sender_email: raw.sender_email ?? '',
    action_taken: raw.action_taken ?? '',
    status: (raw.status ?? 'OPEN').toUpperCase() as Alert['status'],
    acknowledged_at: raw.acknowledged_at ?? null,
    acknowledged_by: raw.acknowledged_by ? String(raw.acknowledged_by) : null,
    created_at: raw.created_at ?? new Date().toISOString(),
  };
}

export interface ServiceStatus {
  service_name: string;
  status: string;
  last_seen: string;
  details: Record<string, any>;
  is_healthy: boolean;
}

export const systemApi = {
  async getSystemStatus(): Promise<ServiceStatus[]> {
    return apiRequest<ServiceStatus[]>('/api/v1/system/status');
  },
  async testImap(): Promise<{ success: boolean; message?: string; error?: string; details?: any }> {
    return apiRequest('/api/v1/system/test-imap', { method: 'POST' });
  },
  async testGemini(): Promise<{ success: boolean; message?: string; error?: string; details?: any }> {
    return apiRequest('/api/v1/system/test-gemini', { method: 'POST' });
  },
};

// Mail Accounts API for personal IMAP integrations
export interface MailAccount {
  id: number;
  name: string;
  email: string;
  provider: string;
  imap_server: string;
  imap_port: number;
  username: string;
  folder: string;
  sync_interval_minutes: number;
  is_active: boolean;
  status: 'pending' | 'connected' | 'syncing' | 'auth_error' | 'error';
  last_sync_at: string | null;
  last_error: string | null;
  total_emails_synced: number;
  created_at: string;
}

export interface MailProvider {
  provider: string;
  imap_server: string;
  imap_port: number;
  notes: string;
}

export interface MailAccountCreate {
  name: string;
  email: string;
  provider: string;
  imap_server?: string;
  imap_port?: number;
  imap_use_ssl?: boolean;
  username?: string;
  password: string;
  folder?: string;
  sync_interval_minutes?: number;
}

export interface MailAccountTestResult {
  success: boolean;
  message: string;
  folders: string[] | null;
}

export const mailAccountsApi = {
  async getProviders(): Promise<MailProvider[]> {
    return apiRequest<MailProvider[]>('/api/v1/mail-accounts/providers');
  },

  async getAccounts(): Promise<MailAccount[]> {
    return apiRequest<MailAccount[]>('/api/v1/mail-accounts/');
  },

  async getAccount(id: number): Promise<MailAccount> {
    return apiRequest<MailAccount>(`/api/v1/mail-accounts/${id}`);
  },

  async createAccount(data: MailAccountCreate): Promise<MailAccount> {
    return apiRequest<MailAccount>('/api/v1/mail-accounts/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateAccount(id: number, updates: Partial<{ name: string; folder: string; sync_interval_minutes: number; is_active: boolean }>): Promise<MailAccount> {
    return apiRequest<MailAccount>(`/api/v1/mail-accounts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  async deleteAccount(id: number): Promise<void> {
    await apiRequest(`/api/v1/mail-accounts/${id}`, { method: 'DELETE' });
  },

  async testConnection(data: MailAccountCreate): Promise<MailAccountTestResult> {
    return apiRequest<MailAccountTestResult>('/api/v1/mail-accounts/test', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async triggerSync(id: number): Promise<{ message: string; account_id: number }> {
    return apiRequest(`/api/v1/mail-accounts/${id}/sync`, { method: 'POST' });
  },
};

// ==================== Users API ====================
export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  organization_id: number | null;
  department: string | null;
  is_active: boolean;
}

export const usersApi = {
  async list(params?: { search?: string; limit?: number; offset?: number; exclude_org_members?: boolean }): Promise<User[]> {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.set('search', params.search);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    if (params?.exclude_org_members) searchParams.set('exclude_org_members', 'true');

    const query = searchParams.toString();
    return apiRequest<User[]>(`/api/v1/users/?${query}`);
  },
};

// ==================== Organizations API ====================
export interface Organization {
  id: number;
  name: string;
  domain: string | null;
  description: string | null;
  is_active: boolean;
  user_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface OrganizationCreate {
  name: string;
  domain?: string;
  description?: string;
}

export interface OrganizationUpdate {
  name?: string;
  domain?: string;
  description?: string;
  is_active?: boolean;
}

export interface OrganizationUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  department: string | null;
  is_active: boolean;
  created_at: string | null;
}

export const organizationsApi = {
  async list(params?: { limit?: number; offset?: number; include_inactive?: boolean }): Promise<{ data: Organization[]; total: number }> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    if (params?.include_inactive) searchParams.set('include_inactive', 'true');
    const query = searchParams.toString();
    return apiRequest(`/api/v1/organizations/${query ? '?' + query : ''}`);
  },

  async get(id: number): Promise<Organization> {
    return apiRequest(`/api/v1/organizations/${id}`);
  },

  async create(data: OrganizationCreate): Promise<Organization> {
    return apiRequest('/api/v1/organizations/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async update(id: number, data: OrganizationUpdate): Promise<Organization> {
    return apiRequest(`/api/v1/organizations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async delete(id: number): Promise<void> {
    await apiRequest(`/api/v1/organizations/${id}`, { method: 'DELETE' });
  },

  async listUsers(orgId: number, params?: { limit?: number; offset?: number }): Promise<{ data: OrganizationUser[]; total: number }> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    const query = searchParams.toString();
    return apiRequest(`/api/v1/organizations/${orgId}/users${query ? '?' + query : ''}`);
  },

  async addUser(orgId: number, userId: number): Promise<{ message: string }> {
    return apiRequest(`/api/v1/organizations/${orgId}/users/${userId}`, { method: 'POST' });
  },

  async removeUser(orgId: number, userId: number): Promise<{ message: string }> {
    return apiRequest(`/api/v1/organizations/${orgId}/users/${userId}`, { method: 'DELETE' });
  },
};

// ==================== Employees API ====================
export interface EmployeeStats {
  user_info: {
    full_name: string;
    email: string;
    role: string;
    department: string | null;
    is_online: boolean;
    last_active: string | null;
  };
  stats: {
    total_emails: number;
    high_risk: number;
    medium_risk: number;
    trust_score: number;
    phishing_reports: number;
    internal_emails: number;
    external_emails: number;
  };
  top_senders: Array<{
    email: string;
    count: number;
    high_risk: number;
  }>;
  recent_activity: Array<{
    id: number;
    subject: string;
    from_address: string;
    risk_score: number;
    analyzed_at: string | null;
  }>;
  activity_by_hour: number[];
  mail_accounts: Array<{
    email: string;
    provider: string;
    is_active: boolean;
  }>;
}

export const employeesApi = {
  async getStats(userId: number): Promise<EmployeeStats> {
    return apiRequest<EmployeeStats>(`/api/v1/employees/${userId}/stats`);
  },
};
