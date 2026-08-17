import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import * as authApi from "@/features/auth/api";
import { tokenStorage } from "@/lib/token-storage";
import type { LoginPayload, MeResponse, RegisterPayload } from "@/types/auth";

interface AuthContextValue {
  me: MeResponse | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      if (!tokenStorage.getAccessToken()) {
        setIsLoading(false);
        return;
      }
      try {
        const identity = await authApi.getMe();
        if (!cancelled) setMe(identity);
      } catch {
        tokenStorage.clear();
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    await authApi.login(payload);
    setMe(await authApi.getMe());
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    await authApi.register(payload);
    setMe(await authApi.getMe());
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setMe(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ me, isLoading, isAuthenticated: me !== null, login, register, logout }),
    [me, isLoading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
