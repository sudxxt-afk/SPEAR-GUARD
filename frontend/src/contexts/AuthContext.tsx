import React, { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { authApi, profileApi, setAuthToken, clearAuthStorage } from '../services/api';
import type { AuthContextType, Profile, User } from '../types';

const USER_KEY = 'spear_guard_user';

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const init = async () => {
      const storedUser = localStorage.getItem(USER_KEY);
      if (storedUser) {
        const parsed = JSON.parse(storedUser) as User;
        setUser(parsed);
        const remote = await authApi.me();
        if (remote) {
          setProfile(remote);
          await profileApi.saveProfile(remote);
        } else {
          clearAuthStorage();
          localStorage.removeItem(USER_KEY);
          setUser(null);
          setProfile(null);
        }
      }
      setLoading(false);
    };
    init();
  }, []);

  const signIn = async (email: string, password: string) => {
    setLoading(true);
    try {
      const { token, user: profileData } = await authApi.login(email, password);
      setAuthToken(token);
      // refresh token already saved inside authApi.login
      const authenticated: User = {
        id: profileData.user_id,
        email: profileData.email,
        full_name: profileData.full_name,
        role: profileData.job_role || 'user',
      };
      localStorage.setItem(USER_KEY, JSON.stringify(authenticated));
      await profileApi.saveProfile(profileData);
      setUser(authenticated);
      setProfile(profileData);
    } finally {
      setLoading(false);
    }
  };

  const signUp = async (email: string, password: string) => {
    setLoading(true);
    try {
      const { token, user: profileData } = await authApi.signup(email, email.split('@')[0], password);
      setAuthToken(token);
      // refresh token already saved inside authApi.signup
      const authenticated: User = {
        id: profileData.user_id,
        email: profileData.email,
        full_name: profileData.full_name,
        role: profileData.job_role || 'user',
      };
      localStorage.setItem(USER_KEY, JSON.stringify(authenticated));
      await profileApi.saveProfile(profileData);
      setUser(authenticated);
      setProfile(profileData);
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    localStorage.removeItem(USER_KEY);
    clearAuthStorage();
    setUser(null);
    setProfile(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        loading,
        signIn,
        signUp,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
