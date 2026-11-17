import { createContext, useContext } from "react";
import { DemoUser } from "../lib/api";

const AuthUserContext = createContext<DemoUser | null>(null);

export const AuthUserProvider = AuthUserContext.Provider;

export function useAuthUser(): DemoUser {
  const user = useContext(AuthUserContext);
  if (!user) throw new Error("useAuthUser must be used inside AuthUserProvider");
  return user;
}
