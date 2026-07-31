import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout';
import { DashboardOverview } from './pages/DashboardOverview';
import { WorkflowControl } from './pages/WorkflowControl';
import { EmailMonitoring } from './pages/EmailMonitoring';
import { AutomationActivity } from './pages/AutomationActivity';
import { Login } from './pages/Login';
import Users from './pages/Users';
import Roles from './pages/Roles';
import Templates from './pages/Templates';
import SystemConfig from './pages/SystemConfig';
import Monitoring from './pages/Monitoring';
import ApprovalQueue from './pages/ApprovalQueue';
import Logs from './pages/Logs';
import BusinessCategories from './pages/BusinessCategories';
import PromptManager from './pages/PromptManager';
import { AuthProvider } from './context/AuthContext';
import { RefreshProvider } from './context/RefreshContext';
import { MailboxProvider } from './context/MailboxContext';
import { ProtectedRoute } from './context/ProtectedRoute';
import { ErrorBoundary } from './components/ErrorBoundary';

function App() {
  return (
    <AuthProvider>
      <RefreshProvider>
        <MailboxProvider>
          <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={
              <ErrorBoundary>
                <ProtectedRoute>
                  <MainLayout />
                </ProtectedRoute>
              </ErrorBoundary>
            }>
              <Route index element={<ErrorBoundary><DashboardOverview /></ErrorBoundary>} />
              <Route path="workflows" element={<ErrorBoundary><WorkflowControl /></ErrorBoundary>} />
              <Route path="monitoring" element={<ErrorBoundary><EmailMonitoring /></ErrorBoundary>} />
              <Route path="automation" element={<ErrorBoundary><AutomationActivity /></ErrorBoundary>} />
              <Route path="approvals" element={<ErrorBoundary><ApprovalQueue /></ErrorBoundary>} />
              
              {/* Administration Routes */}
              <Route path="users" element={<ErrorBoundary><Users /></ErrorBoundary>} />
              <Route path="roles" element={<ErrorBoundary><Roles /></ErrorBoundary>} />
              <Route path="templates" element={<ErrorBoundary><Templates /></ErrorBoundary>} />
              <Route path="settings" element={<ErrorBoundary><SystemConfig /></ErrorBoundary>} />
              <Route path="business-categories" element={<ErrorBoundary><BusinessCategories /></ErrorBoundary>} />
              <Route path="prompt-manager" element={<ErrorBoundary><PromptManager /></ErrorBoundary>} />
              <Route path="system-monitoring" element={<ErrorBoundary><Monitoring /></ErrorBoundary>} />
              <Route path="logs" element={<ErrorBoundary><Logs /></ErrorBoundary>} />
              <Route path="automation/logs" element={<Navigate to="/logs" replace />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        </MailboxProvider>
      </RefreshProvider>
    </AuthProvider>
  );
}

export default App;
