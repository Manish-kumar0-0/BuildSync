import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { Role } from "@/app/types";

interface AppContextValue {
  role: Role | null;
  setRole: (role: Role | null) => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role | null>(null);
  const value = useMemo(() => ({ role, setRole }), [role]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useAppContext must be used within an AppProvider");
  }
  return context;
}
