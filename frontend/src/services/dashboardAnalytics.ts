import axios, { InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add auth token to requests
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('spear_guard_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Add error handling
api.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error: AxiosError) => {
        if (error.response?.status === 401) {
            // Token expired or invalid
            localStorage.removeItem('spear_guard_token');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export interface ThreatTrendData {
    date: string;
    full_date: string;
    threats: number;
    blocked: number;
    quarantined: number;
}

export interface AttackPoint {
    id: number;
    lat: number;
    lng: number;
    city: string;
    country: string;
    severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    count: number;
    timestamp: string;
}

export interface ActivityData {
    hour: string;
    count: number;
}

export interface RiskTimelineData {
    timestamp: string;
    score: number;
    average: number;
}

export interface ThreatDetail {
    id: number;
    from_address: string;
    to_address: string;
    subject: string;
    risk_score: number;
    status: string;
    decision: string;
    analyzed_at: string;
    analysis_details?: {
        technical: string[];
        linguistic: string[];
        contextual: string[];
        behavioral: string[];
    };
}

export const dashboardAnalyticsApi = {
    /**
     * Get threat trend data
     */
    getThreatTrend: async (days: number = 7): Promise<ThreatTrendData[]> => {
        const response = await api.get(`/api/v1/dashboard/threat-trend?days=${days}`);
        return response.data.data;
    },

    /**
     * Get attack map data
     */
    getAttackMap: async (hours: number = 24): Promise<AttackPoint[]> => {
        const response = await api.get(`/api/v1/dashboard/attack-map?hours=${hours}`);
        return response.data.attacks;
    },

    /**
     * Get activity heatmap data
     */
    getActivityHeatmap: async (days: number = 7): Promise<ActivityData[]> => {
        const response = await api.get(`/api/v1/dashboard/activity-heatmap?days=${days}`);
        return response.data.data;
    },

    /**
     * Get risk timeline data
     */
    getRiskTimeline: async (days: number = 14): Promise<RiskTimelineData[]> => {
        const response = await api.get(`/api/v1/dashboard/risk-timeline?days=${days}`);
        return response.data.data;
    },

    /**
     * Get threat details for a specific date (drill-down)
     */
    getThreatDetails: async (date: string): Promise<{ date: string; total_threats: number; threats: ThreatDetail[] }> => {
        const response = await api.get(`/api/v1/dashboard/threat-details/${date}`);
        return response.data;
    },
};
