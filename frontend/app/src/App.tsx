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
import AdminLayout from "./layouts/AdminLayout";
import ChatBotPage from "./pages/ChatBotPage";
import DashboardPage from "./pages/admin/DashboardPage";
import DocumentManagementPage from "./pages/admin/DocumentManagementPage";

const routeTitles: Record<string, string> = {
  "/": "Chat Bot",
  "/chat": "Chat Bot",
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
      <Router>
        <DocumentTitle />
        <Routes>
          {/* Chat Bot Page (User) */}
          <Route path="/" element={<ChatBotPage />} />
          <Route path="/chat" element={<ChatBotPage />} />

          {/* Admin Pages */}
          <Route
            path="/admin"
            element={
              <AdminLayout>
                <Outlet />
              </AdminLayout>
            }
          >
            <Route index element={<Navigate to="/admin/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="documents" element={<DocumentManagementPage />} />
          </Route>

          {/* 404 - Redirect to chat */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AntApp>
  );
}

export default App;
