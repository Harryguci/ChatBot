import React, { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  picture_url?: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (googleToken: string) => Promise<void>;
  logout: () => void;
  isAdmin: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem("auth_token");
    const storedUser = localStorage.getItem("auth_user");

    if (storedToken && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        setToken(storedToken);
        setUser(parsedUser);

        // Set axios default header
        axios.defaults.headers.common[
          "Authorization"
        ] = `Bearer ${storedToken}`;
      } catch (error) {
        console.error("Failed to parse stored user:", error);
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
      }
    }

    setIsLoading(false);
  }, []);

  const login = async (googleToken: string) => {
    try {
      const response = await axios.post("/api/auth/google", {
        token: googleToken,
      });

      const { access_token, user: userData } = response.data;

      // Store in state
      setToken(access_token);
      setUser(userData);

      // Store in localStorage
      localStorage.setItem("auth_token", access_token);
      localStorage.setItem("auth_user", JSON.stringify(userData));

      // Set axios default header
      axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;

      console.log("Login successful:", userData);
    } catch (error: any) {
      console.error("Login failed:", error);
      throw new Error(
        error.response?.data?.detail || "Authentication failed"
      );
    }
  };

  const logout = () => {
    // Clear state
    setToken(null);
    setUser(null);

    // Clear localStorage
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");

    // Clear axios default header
    delete axios.defaults.headers.common["Authorization"];

    console.log("Logout successful");
  };

  const isAdmin = () => {
    return user?.role === "admin";
  };

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    logout,
    isAdmin,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
