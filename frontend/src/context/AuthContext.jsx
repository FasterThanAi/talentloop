import React, { createContext, useContext, useEffect, useState } from "react";
import api from "../lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("talentloop_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("talentloop_token");
    if (token) {
      api
        .get("/auth/me")
        .then((userData) => {
          setUser(userData);
          localStorage.setItem("talentloop_user", JSON.stringify(userData));
        })
        .catch(() => {
          logout();
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    localStorage.setItem("talentloop_token", res.access_token);
    localStorage.setItem("talentloop_user", JSON.stringify(res.user));
    setUser(res.user);
    return res.user;
  };

  const register = async (orgName, email, password, role = "recruiter") => {
    const res = await api.post("/auth/register", {
      org_name: orgName,
      email,
      password,
      role,
    });
    localStorage.setItem("talentloop_token", res.access_token);
    localStorage.setItem("talentloop_user", JSON.stringify(res.user));
    setUser(res.user);
    return res.user;
  };

  const logout = () => {
    localStorage.removeItem("talentloop_token");
    localStorage.removeItem("talentloop_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
