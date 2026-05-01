export interface Profile {
  id: string;
  user_id: string;
  full_name: string | null;
  email: string;
  department: string | null;
  job_role: string | null;
  clearance_level: number;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface TrustedRegistry {
  id: string;
  email_address: string | null;
  domain: string | null;
  organization: string | null;
  trust_level: number;
  spf_configured?: boolean;
  dkim_configured?: boolean;
  dmarc_configured?: boolean;
  notes?: string | null;
  created_at?: string;
  updated_at?: string;
  created_by?: string;
  is_verified?: boolean;
  is_active?: boolean;
  status?: string;
}

export interface SenderProfile {
  id: string;
  email_address: string;
  organization: string | null;
  domain: string | null;
  last_seen_at: string | null;
  email_count: number;
  verified: boolean;
  risk_score: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmailAnalysis {
  id: string;
  sender_email: string;
  recipient_email: string;
  subject: string | null;
  body_preview: string | null;
  body_text?: string | null;
  technical_score: number;
  linguistic_score: number;
  behavioral_score: number;
  contextual_score: number;
  risk_score: number;
  decision: 'DELIVER' | 'WARN' | 'BLOCK' | 'QUARANTINE' | 'PENDING';
  explanation?: string;
  analysis_details?: {
    technical: string[];
    linguistic: string[];
    contextual: string[];
    behavioral: string[];
  } | null;
  raw_headers?: any;
  has_attachments: boolean;
  attachment_count: number;
  suspicious_urls: string[] | null;
  created_at: string;
  analyzed_at: string | null;
  analyzed_by: string | null;
}

export interface Alert {
  id: string;
  email_analysis_id: string | null;
  alert_type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  title: string;
  description: string | null;
  message: string | null;
  recipient_email: string;
  sender_email: string;
  action_taken: string;
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  created_at: string;
}

export interface Anomaly {
  id: string;
  sender_email: string;
  anomaly_type: 'GEOGRAPHIC' | 'TIMING' | 'FREQUENCY' | 'BEHAVIORAL';
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string | null;
  metadata: Record<string, any> | null;
  detected_at: string;
  related_analysis_id: string | null;
}

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  role?: string;
}

export interface AuthContextType {
  user: User | null;
  profile: Profile | null;
  loading: boolean;
  signUp: (email: string, password: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export interface DashboardStats {
  totalEmails: number;
  suspiciousEmails: number;
  alertsOpen: number;
  registrySize: number;
  lastAnalysis: string | null;
  riskTrend: number[];
}
