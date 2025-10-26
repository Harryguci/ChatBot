import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import ChatBotPage from './pages/ChatBotPage';
import AdminLayout from './layouts/AdminLayout';
import DashboardPage from './pages/admin/DashboardPage';
import DocumentManagementPage from './pages/admin/DocumentManagementPage';
import './App.css';

function App() {
  return (
    <Router>
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
  );
}

export default App;
