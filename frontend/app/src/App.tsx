import { App as AntApp } from "antd";
import { useEffect } from "react";
import {
  Navigate,
  Outlet,
  Route,
  BrowserRouter as Router,
  Routes,
  useLocation,
} from "react-router-dom";
import "./App.css";
import { AuthProvider } from "./contexts/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import AdminLayout from "./layouts/AdminLayout";
import ChatBotPage from "./pages/ChatBotPage";
import DashboardPage from "./pages/admin/DashboardPage";
import DocumentManagementPage from "./pages/admin/DocumentManagementPage";

const routeTitles: Record<string, string> = {
  "/": "Chat Bot",
  "/chat": "Chat Bot",
  "/login": "Login",
  "/admin/dashboard": "Admin Dashboard",
  "/admin/documents": "Document Management",
};

function DocumentTitle() {
  const location = useLocation();

  useEffect(() => {
    const title = routeTitles[location.pathname] || "Chat Bot";
    document.title = title;
  }, [location.pathname]);

  return null;
}

function App() {
  return (
    <AntApp>
      <AuthProvider>
        <Router>
          <DocumentTitle />
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected Chat Bot Page (User) */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <ChatBotPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <ProtectedRoute>
                  <ChatBotPage />
                </ProtectedRoute>
              }
            />

            {/* Protected Admin Pages */}
            <Route
              path="/admin"
              element={
                <ProtectedRoute requireAdmin={true}>
                  <AdminLayout>
                    <Outlet />
                  </AdminLayout>
                </ProtectedRoute>
              }
            >
              <Route
                index
                element={<Navigate to="/admin/dashboard" replace />}
              />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="documents" element={<DocumentManagementPage />} />
            </Route>

            {/* 404 - Redirect to chat */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </AntApp>
  );
}

export default App;
