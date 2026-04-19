import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: string;
  nome: string;
  email: string;
  perfil: "ADMIN" | "USER";
  tenant_id?: string;
  onboarding_step?: number;
  subscription_status?: string | null;
  trial_ends_at?: string | null;
}

interface AuthStore {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
  isAdmin: () => boolean;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      setAuth: (user, token) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("tribus_token", token);
        }
        set({ user, token, isAuthenticated: true });
      },

      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("tribus_token");
        }
        set({ user: null, token: null, isAuthenticated: false });
      },

      isAdmin: () => get().user?.perfil === "ADMIN",
    }),
    { name: "tribus-auth" } // persiste em localStorage (padrão do zustand/persist)
  )
);
