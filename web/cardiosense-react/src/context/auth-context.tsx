import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";

interface User {
  email: string;
  fullName: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  login: (email: string, fullName: string, role: string, token: string) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  accessToken: null,
  login: () => {},
  logout: () => {},
  isLoading: true,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("cardiosense_user");
    const storedToken = localStorage.getItem("cardiosense_token");
    if (stored && storedToken) {
      try {
        setUser(JSON.parse(stored));
        setAccessToken(storedToken);
      } catch {}
    }
    setIsLoading(false);
  }, []);

  function login(email: string, fullName: string, role: string, token: string) {
    const u = { email, fullName, role };
    localStorage.setItem("cardiosense_user", JSON.stringify(u));
    localStorage.setItem("cardiosense_token", token);
    setUser(u);
    setAccessToken(token);
  }

  function logout() {
    localStorage.removeItem("cardiosense_user");
    localStorage.removeItem("cardiosense_token");
    setUser(null);
    setAccessToken(null);
  }

  return (
    <AuthContext.Provider
      value={{ user, accessToken, login, logout, isLoading }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
