import { useAppContext } from "@/context/AppContext";

export function useRoleContext() {
  const { role, setRole } = useAppContext();
  return { role, setRole };
}
