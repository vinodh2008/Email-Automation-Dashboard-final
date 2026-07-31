import axios from 'axios';
import { normalizeEmail, normalizeWorkflowExecution } from './adapters';

const delay = (ms) => new Promise(res => setTimeout(res, ms));

const validateArray = (data, name) => {
  if (!Array.isArray(data)) throw new Error(`Unable to load data: Unexpected response format for ${name}`);
  return data;
};

const validateObject = (data, name) => {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error(`Unable to load data: Unexpected response format for ${name}`);
  return data;
};
// Create Axios client using environment variable or default to localhost
const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const axiosClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Intercept requests to attach auth token
axiosClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercept responses to unwrap the `APIResponse` generic structure
axiosClient.interceptors.response.use(
  (response) => {
    const resData = response.data;
    // Some endpoints return { success, data }, others return { success, message } or raw arrays/objects
    if (resData && resData.success !== undefined && resData.data !== undefined) {
       return resData.data;
    }
    // Return whatever we got — never undefined
    return resData;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    } else if (error.response?.status === 403) {
      console.warn('Permission denied:', error.config?.url);
    } else if (!error.response) {
      console.error("Network Failure: Backend is unreachable.", error);
    } else if (error.response?.status >= 500) {
      console.error("Server Error:", error.config?.url, error.response?.status);
    }
    return Promise.reject(error);
  }
);

export const api = {
  // ---------------------------------------------------------
  // Dashboard
  // ---------------------------------------------------------
  getDashboardSummary: async () => {
    const response = await axiosClient.get('/dashboard/summary');
    return validateObject(response, 'Dashboard Summary');
  },
  
  getRecentActivity: async () => {
    const response = await axiosClient.get('/dashboard/recent-activity');
    return validateArray(response.data || response, 'Recent Activity');
  },

  // ---------------------------------------------------------
  // Workflows
  // ---------------------------------------------------------
  getCategories: async () => {
    const response = await axiosClient.get('/workflows/categories');
    const data = validateArray(response.data || response, 'Categories');
    return { data }; // Wrap array for UI dropdowns
  },

  getWorkflows: async ({ status = 'all', search = '', page = 1, pageSize = 10 }) => {
    try {
      const response = await axiosClient.get('/workflows', {
        params: { search, page, page_size: pageSize }
      });
      
      const rawData = Array.isArray(response.data) ? response.data : (Array.isArray(response) ? response : []);
      
      // Map backend response -> UI Expected Format
      const mappedData = rawData.map(w => {
        let category = "";
        if (w.trigger_conditions_json?.rules?.length > 0) {
           category = w.trigger_conditions_json.rules[0].value;
           if (category === 'any') category = '';
        }
        let team = "";
        if (w.description && w.description.startsWith("Target Team: ")) {
           team = w.description.replace("Target Team: ", "");
        }
        return {
          ...w,
          status: w.is_active ? 'active' : 'disabled',
          trigger_type: 'webhook', // Fallback for UI visualization
          last_run: w.updated_at,
          category_filter: category,
          destination_team: team
        };
      });
      
      return {
        data: mappedData,
        total: response.meta?.total_items || mappedData.length,
        page: response.meta?.current_page || page,
        page_size: response.meta?.page_size || pageSize
      };
    } catch (e) {
      console.error('Failed to fetch workflows:', e);
      return { data: [], total: 0, page, page_size: pageSize };
    }
  },
  
  createWorkflow: async (workflow) => {
    let mailboxId = workflow.mailbox_account_id;
    if (!mailboxId) {
      const mailboxes = await api.getMailboxes();
      if (mailboxes && mailboxes.length > 0) {
        mailboxId = mailboxes[0].id;
      }
    }
    if (!mailboxId) {
      throw new Error("No connected Gmail account found. Please connect your Gmail account in Settings before creating workflows.");
    }
    
    // Map UI form fields -> Backend schema fields
    const payload = {
      name: workflow.name || "Untitled Workflow",
      description: workflow.description || "No description",
      mailbox_account_id: mailboxId,
      trigger_conditions_json: workflow.trigger_conditions_json || { operator: "AND", rules: [] },
      actions_json: workflow.actions_json || { actions: [] },
      is_active: false
    };

    return await axiosClient.post('/workflows', payload);
  },
  
  updateWorkflow: async (id, workflow) => {
    const payload = {
      name: workflow.name,
      description: workflow.description,
      trigger_conditions_json: workflow.trigger_conditions_json,
      actions_json: workflow.actions_json
    };
    return await axiosClient.put(`/workflows/${id}`, payload);
  },
  
  deleteWorkflow: async (id) => {
    await axiosClient.delete(`/workflows/${id}`);
    return { success: true };
  },
  
  getWorkflowExecutions: async (id) => {
    const response = await axiosClient.get(`/workflows/${id}/executions`);
    return response || [];
  },
  
  toggleWorkflowState: async (id, action) => {
    let apiAction = action;
    if (action === 'start') apiAction = 'enable';
    if (action === 'stop') apiAction = 'disable';
    
    const updated = await axiosClient.patch(`/workflows/${id}/state`, { action: apiAction });
    return {
      ...updated,
      status: updated.is_active ? 'active' : 'disabled',
      trigger_type: 'webhook',
      last_run: updated.updated_at
    };
  },

  // ---------------------------------------------------------
  // Emails
  // TODO [BACKEND STANDARDIZATION]: This endpoint uses the Sprint 2 legacy route /emails/
  // and does NOT follow the /api/v1/ convention used by the rest of the API (workflows, dashboard).
  // The real call goes to the axiosClient baseURL's HOST:PORT + /emails/ directly (not /api/v1/emails).
  // Ask the backend team to either:
  //   (a) add a /api/v1/emails route that wraps/replaces this one, OR
  //   (b) keep it at /emails/ and document it as a deliberate exception.
  // Until then, this call uses a separate Axios instance without the /api/v1 prefix.
  // ---------------------------------------------------------
  getEmails: async ({ status = 'all', search = '', page = 1, pageSize = 10 }) => {
    try {
      const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
      const response = await axios.get(`${baseHost}/emails/`, { 
        params: { status, search, skip: (page - 1) * pageSize, limit: pageSize },
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      const responseData = response.data || response;
      const rawData = Array.isArray(responseData.data) ? responseData.data : (Array.isArray(responseData) ? responseData : []);
      const normalizedData = rawData.map(normalizeEmail);
      return { data: normalizedData, total: responseData.total || rawData.length, page, page_size: pageSize };
    } catch (e) {
      console.error('Failed to fetch emails:', e);
      return { data: [], total: 0, page, page_size: pageSize };
    }
  },

  getEmailDetail: async (id) => {
    const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
    const response = await axios.get(`${baseHost}/emails/${id}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    const responseData = response.data || response;
    return normalizeEmail(responseData.data || responseData);
  },
  
  retryEmail: async (id) => {
    const response = await axiosClient.post(`/emails/${id}/retry`);
    return normalizeEmail(validateObject(response.data || response, 'Email Retry Response'));
  },

  getEmailStats: async () => {
    const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
    const response = await axios.get(`${baseHost}/emails/stats`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    return response.data || response;
  },

  exportEmails: async (status = 'all', search = '') => {
    const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
    const response = await axios.get(`${baseHost}/emails/export`, {
      params: { status, search },
      responseType: 'blob',
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    
    // Extract filename from headers or default
    const contentDisposition = response.headers['content-disposition'];
    let filename = `email-monitoring-export-${new Date().toISOString().split('T')[0]}.xlsx`;
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) filename = match[1];
    }
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.parentNode.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  // ---------------------------------------------------------
  // Automation Activity / Operations Dashboard
  // ---------------------------------------------------------
  getOperationsSummary: async () => {
    const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
    const response = await axios.get(`${baseHost}/dashboard/summary`);
    return response.data || {};
  },
  
  getRecentSyncs: async () => {
    const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
    const response = await axios.get(`${baseHost}/dashboard/recent-syncs?limit=5`);
    return response.data;
  },

  getMailboxes: async () => {
    const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
    const response = await axios.get(`${baseHost}/mailboxes/`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    return response.data || response;
  },

  getMailboxStatus: async () => {
    const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
    const response = await axios.get(`${baseHost}/mailboxes/status`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    return response.data;
  },

  connectMailbox: async () => {
    const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
    const response = await axios.post(`${baseHost}/mailboxes/connect`, {}, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    return response.data;
  },

  syncMailbox: async (mailboxId) => {
    const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
    const response = await axios.post(`${baseHost}/mailboxes/${mailboxId}/sync`, {}, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    return response.data;
  },

  disconnectMailbox: async (mailboxId, deleteData = false) => {
    const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
    const response = await axios.post(`${baseHost}/mailboxes/${mailboxId}/disconnect?delete_data=${deleteData}`, {}, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    return response.data;
  },

  reconnectMailbox: async (mailboxId) => {
    const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
    const response = await axios.post(`${baseHost}/mailboxes/${mailboxId}/reconnect`, {}, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    return response.data;
  },

  switchMailboxAccount: async () => {
    const baseHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');
    const response = await axios.post(`${baseHost}/mailboxes/switch-account`, {}, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    return response.data;
  },

  getSystemStatus: async () => {
    const response = await axiosClient.get('/system/status');
    return response || {};
  },

  getDatabaseHealth: async () => {
    const response = await axiosClient.get('/health/database');
    return response || {};
  },

  getCurrentTask: async () => {
    try {
      // Axios interceptor unwraps APIResponse -> data = CurrentTaskResponse { current_task: {...} | null }
      const response = await axiosClient.get('/automation/current-task');
      return response?.current_task || null;
    } catch (e) {
      console.error('Failed to fetch current task:', e);
      throw e;
    }
  },
  
  getAutomationQueue: async () => { 
    try {
      // Axios interceptor unwraps APIResponse -> data = QueueResponse { data: [...], total: n }
      const response = await axiosClient.get('/automation/queue');
      const rawData = validateArray(response?.data || [], 'Automation Queue');
      return { data: rawData, total: response?.total || rawData.length };
    } catch (e) {
      console.error('Failed to fetch automation queue:', e);
      throw e;
    }
  },
  
  getAutomationHistory: async () => { 
    try {
      // Axios interceptor unwraps APIResponse -> data = HistoryResponse { data: [...], total, page, page_size }
      const response = await axiosClient.get('/automation/history');
      const rawData = validateArray(response?.data || [], 'Automation History');
      return { data: rawData.map(normalizeWorkflowExecution), total: response?.total || 0 };
    } catch (e) {
      console.error('Failed to fetch automation history:', e);
      throw e;
    }
  },

  // ---------------------------------------------------------
  // Notifications
  // ---------------------------------------------------------
  getNotifications: async () => {
    const response = await axiosClient.get('/notifications');
    return response || [];
  },

  // ---------------------------------------------------------
  // Sprint 5: Prompt Templates & AI Approvals
  // ---------------------------------------------------------
  getPromptTemplates: async () => {
    try {
      const response = await axiosClient.get('/prompt-templates');
      return response || [];
    } catch (e) {
      console.error('Failed to fetch prompt templates:', e);
      return [];
    }
  },

  createPromptTemplate: async (payload) => {
    try {
      const response = await axiosClient.post('/prompt-templates', payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  deletePromptTemplate: async (id) => {
    try {
      const response = await axiosClient.delete(`/prompt-templates/${id}`);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  updatePromptTemplate: async (id, payload) => {
    try {
      const response = await axiosClient.put(`/prompt-templates/${id}`, payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  testPromptTemplate: async (id, sampleInputs) => {
    try {
      const response = await axiosClient.post(`/prompt-templates/${id}/test`, { sample_inputs: sampleInputs });
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  validatePromptTemplate: async (id) => {
    try {
      const response = await axiosClient.get(`/prompt-templates/${id}/validate`);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  clonePromptTemplate: async (id) => {
    try {
      const response = await axiosClient.post(`/prompt-templates/${id}/clone`);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  getApprovalStats: async () => {
    try {
      const response = await axiosClient.get('/ai-approvals/stats');
      return response || {};
    } catch (e) {
      return {};
    }
  },

  // ---------------------------------------------------------
  // AI Providers
  // ---------------------------------------------------------
  getAIProviders: async () => {
    try {
      const response = await axiosClient.get('/ai-providers');
      return response || [];
    } catch (e) {
      console.error('Failed to fetch AI providers:', e);
      return [];
    }
  },

  createAIProvider: async (payload) => {
    try {
      const response = await axiosClient.post('/ai-providers', payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  updateAIProvider: async (id, payload) => {
    try {
      const response = await axiosClient.put(`/ai-providers/${id}`, payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  deleteAIProvider: async (id) => {
    try {
      const response = await axiosClient.delete(`/ai-providers/${id}`);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  testAIProvider: async (id) => {
    try {
      const response = await axiosClient.post(`/ai-providers/${id}/test`);
      return response || { success: false, error: 'No response from server' };
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || 'Test failed';
      return { success: false, error: msg };
    }
  },

  // ---------------------------------------------------------
  // Email Templates
  // ---------------------------------------------------------
  getEmailTemplates: async () => {
    try {
      const response = await axiosClient.get('/email-templates');
      return response || [];
    } catch (e) {
      console.error('Failed to fetch email templates:', e);
      return [];
    }
  },

  createEmailTemplate: async (payload) => {
    try {
      const response = await axiosClient.post('/email-templates', payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  updateEmailTemplate: async (id, payload) => {
    try {
      const response = await axiosClient.put(`/email-templates/${id}`, payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  deleteEmailTemplate: async (id) => {
    try {
      const response = await axiosClient.delete(`/email-templates/${id}`);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  // ---------------------------------------------------------
  // System Logs
  // ---------------------------------------------------------
  getSystemLogs: async (params = {}) => {
    try {
      const queryParams = new URLSearchParams();
      if (params.level) queryParams.append('level', params.level);
      if (params.category) queryParams.append('category', params.category);
      if (params.page) queryParams.append('page', params.page);
      if (params.page_size) queryParams.append('page_size', params.page_size);
      const response = await axiosClient.get(`/logs?${queryParams.toString()}`);
      return response || [];
    } catch (e) {
      console.error('Failed to fetch system logs:', e);
      return [];
    }
  },

  getPendingApprovals: async () => {
    try {
      const response = await axiosClient.get('/ai-approvals');
      return response || [];
    } catch (e) {
      console.error('Failed to fetch AI pending approvals:', e);
      return [];
    }
  },

  approveAIDraft: async (id, editedText) => {
    try {
      const response = await axiosClient.post(`/ai-approvals/${id}/approve`, null, { params: { edited_text: editedText } });
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  rejectAIDraft: async (id) => {
    try {
      const response = await axiosClient.post(`/ai-approvals/${id}/reject`);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  // --- Users Management ---
  getUsers: async (params = {}) => {
    try {
      const response = await axiosClient.get('/users', { params });
      return response || { data: [], meta: {} };
    } catch (e) {
      console.error('Failed to fetch users:', e);
      return { data: [], meta: {} };
    }
  },
  createUser: async (payload) => {
    try {
      const response = await axiosClient.post('/users', payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },
  updateUser: async (id, payload) => {
    try {
      const response = await axiosClient.put(`/users/${id}`, payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },
  deleteUser: async (id) => {
    try {
      const response = await axiosClient.delete(`/users/${id}`);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  // --- Roles Management ---
  getRoles: async (params = {}) => {
    try {
      const response = await axiosClient.get('/admin/roles/', { params });
      return response || [];
    } catch (e) {
      console.error('Failed to fetch roles:', e);
      return [];
    }
  },
  createRole: async (payload) => {
    try {
      const response = await axiosClient.post('/admin/roles', payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },
  updateRole: async (id, payload) => {
    try {
      const response = await axiosClient.put(`/admin/roles/${id}`, payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },
  deleteRole: async (id) => {
    try {
      const response = await axiosClient.delete(`/admin/roles/${id}`);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  // ---------------------------------------------------------
  // Enterprise Admin Console — Phase 1
  // ---------------------------------------------------------
  getCompanySettings: async () => {
    try {
      const response = await axiosClient.get('/company-settings');
      return response || {};
    } catch (e) {
      console.error('Failed to fetch company settings:', e);
      return {};
    }
  },

  updateCompanySettings: async (payload) => {
    try {
      const response = await axiosClient.put('/company-settings', payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  getAIDefaults: async () => {
    try {
      const response = await axiosClient.get('/ai-defaults');
      return response || {};
    } catch (e) {
      console.error('Failed to fetch AI defaults:', e);
      return {};
    }
  },

  updateAIDefaults: async (payload) => {
    try {
      const response = await axiosClient.put('/ai-defaults', payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  getFeatureFlags: async () => {
    try {
      const response = await axiosClient.get('/feature-flags');
      return response || {};
    } catch (e) {
      console.error('Failed to fetch feature flags:', e);
      return {};
    }
  },

  updateFeatureFlags: async (flags) => {
    try {
      const response = await axiosClient.put('/feature-flags', { flags });
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  toggleFeatureFlag: async (flagName, enabled) => {
    try {
      const response = await axiosClient.put('/feature-flags/toggle', { flag_name: flagName, enabled });
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  getAuditLogs: async (params = {}) => {
    try {
      const queryParams = new URLSearchParams();
      if (params.entity_type) queryParams.append('entity_type', params.entity_type);
      if (params.user_id) queryParams.append('user_id', params.user_id);
      if (params.limit) queryParams.append('limit', params.limit);
      if (params.offset) queryParams.append('offset', params.offset);
      const response = await axiosClient.get(`/audit-log?${queryParams.toString()}`);
      return response || { items: [], total: 0 };
    } catch (e) {
      console.error('Failed to fetch audit logs:', e);
      return { items: [], total: 0 };
    }
  },

  getNotificationSettings: async () => {
    try {
      const response = await axiosClient.get('/notification-settings');
      return response || {};
    } catch (e) {
      console.error('Failed to fetch notification settings:', e);
      return {};
    }
  },

  updateNotificationSettings: async (payload) => {
    try {
      const response = await axiosClient.put('/notification-settings', payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  getAIProvidersHealth: async () => {
    try {
      const response = await axiosClient.get('/ai-providers/health');
      return response || [];
    } catch (e) {
      console.error('Failed to fetch AI providers health:', e);
      return [];
    }
  },

  testAllAIProviders: async () => {
    try {
      const response = await axiosClient.post('/ai-providers/test-all');
      return response || [];
    } catch (e) {
      console.error('Failed to test all AI providers:', e);
      return [];
    }
  },

  getAIMetrics: async () => {
    try {
      const response = await axiosClient.get('/ai-providers/metrics');
      return response || { summary: {}, providers: [] };
    } catch (e) {
      console.error('Failed to fetch AI metrics:', e);
      return { summary: {}, providers: [] };
    }
  },

  // ─── Business Categories ────────────────────────────────────────────
  getBusinessCategories: async (params = {}) => {
    try {
      const queryParams = new URLSearchParams();
      if (params.status) queryParams.append('status', params.status);
      if (params.search) queryParams.append('search', params.search);
      const response = await axiosClient.get(`/business-categories?${queryParams.toString()}`);
      return response || [];
    } catch (e) {
      console.error('Failed to fetch business categories:', e);
      return [];
    }
  },

  getBusinessCategory: async (id) => {
    try {
      const response = await axiosClient.get(`/business-categories/${id}`);
      return response || null;
    } catch (e) {
      console.error('Failed to fetch business category:', e);
      return null;
    }
  },

  createBusinessCategory: async (payload) => {
    try {
      const response = await axiosClient.post('/business-categories', payload);
      return response;
    } catch (e) {
      throw e;
    }
  },

  updateBusinessCategory: async (id, payload) => {
    try {
      const response = await axiosClient.put(`/business-categories/${id}`, payload);
      return response;
    } catch (e) {
      throw e;
    }
  },

  deleteBusinessCategory: async (id) => {
    try {
      await axiosClient.delete(`/business-categories/${id}`);
      return true;
    } catch (e) {
      throw e;
    }
  },

  setDefaultBusinessCategory: async (id) => {
    try {
      const response = await axiosClient.put(`/business-categories/${id}/set-default`);
      return response;
    } catch (e) {
      throw e;
    }
  },

  getCategoryPrompts: async (id) => {
    try {
      const response = await axiosClient.get(`/business-categories/${id}/prompts`);
      return response || [];
    } catch (e) {
      console.error('Failed to fetch category prompts:', e);
      return [];
    }
  },

  getCategoryWorkflows: async (id) => {
    try {
      const response = await axiosClient.get(`/business-categories/${id}/workflows`);
      return response || [];
    } catch (e) {
      console.error('Failed to fetch category workflows:', e);
      return [];
    }
  },

  updateCategoryAIConfig: async (id, payload) => {
    try {
      const response = await axiosClient.put(`/business-categories/${id}/ai-config`, payload);
      return response;
    } catch (e) {
      throw e;
    }
  },

  getCategoryMetrics: async (id) => {
    try {
      const response = await axiosClient.get(`/business-categories/${id}/metrics`);
      return response || {};
    } catch (e) {
      console.error('Failed to fetch category metrics:', e);
      return {};
    }
  },

  // ─── Business Prompts ──────────────────────────────────────────────
  getBusinessPrompts: async (params = {}) => {
    try {
      const queryParams = new URLSearchParams();
      if (params.category_id) queryParams.append('category_id', params.category_id);
      if (params.status) queryParams.append('status', params.status);
      const response = await axiosClient.get(`/business-prompts?${queryParams.toString()}`);
      return response || [];
    } catch (e) {
      console.error('Failed to fetch business prompts:', e);
      return [];
    }
  },

  getBusinessPrompt: async (id) => {
    try {
      const response = await axiosClient.get(`/business-prompts/${id}`);
      return response || null;
    } catch (e) {
      console.error('Failed to fetch business prompt:', e);
      return null;
    }
  },

  createBusinessPrompt: async (payload) => {
    try {
      const response = await axiosClient.post('/business-prompts', payload);
      return response;
    } catch (e) {
      throw e;
    }
  },

  updateBusinessPrompt: async (id, payload) => {
    try {
      const response = await axiosClient.put(`/business-prompts/${id}`, payload);
      return response;
    } catch (e) {
      throw e;
    }
  },

  deleteBusinessPrompt: async (id) => {
    try {
      await axiosClient.delete(`/business-prompts/${id}`);
      return true;
    } catch (e) {
      throw e;
    }
  },

  publishBusinessPrompt: async (id) => {
    try {
      const response = await axiosClient.post(`/business-prompts/${id}/publish`);
      return response;
    } catch (e) {
      throw e;
    }
  },

  rollbackBusinessPrompt: async (id, payload) => {
    try {
      const response = await axiosClient.post(`/business-prompts/${id}/rollback`, payload);
      return response;
    } catch (e) {
      throw e;
    }
  },

  archiveBusinessPrompt: async (id) => {
    try {
      const response = await axiosClient.post(`/business-prompts/${id}/archive`);
      return response;
    } catch (e) {
      throw e;
    }
  },

  cloneBusinessPrompt: async (id, payload) => {
    try {
      const response = await axiosClient.post(`/business-prompts/${id}/clone`, payload);
      return response;
    } catch (e) {
      throw e;
    }
  },

  getPromptVersions: async (id) => {
    try {
      const response = await axiosClient.get(`/business-prompts/${id}/versions`);
      return response || [];
    } catch (e) {
      console.error('Failed to fetch prompt versions:', e);
      return [];
    }
  },

  getPromptVersion: async (promptId, versionNumber) => {
    try {
      const response = await axiosClient.get(`/business-prompts/${promptId}/versions/${versionNumber}`);
      return response || null;
    } catch (e) {
      console.error('Failed to fetch prompt version:', e);
      return null;
    }
  },

  // ─── Prompt Variables ──────────────────────────────────────────────
  getPromptVariables: async (params = {}) => {
    try {
      const queryParams = new URLSearchParams();
      if (params.scope) queryParams.append('scope', params.scope);
      if (params.adapter) queryParams.append('adapter', params.adapter);
      if (params.category) queryParams.append('category', params.category);
      const response = await axiosClient.get(`/prompt-variables?${queryParams.toString()}`);
      return response || [];
    } catch (e) {
      console.error('Failed to fetch prompt variables:', e);
      return [];
    }
  },

  getPromptVariableRegistry: async () => {
    try {
      const response = await axiosClient.get('/prompt-variables/registry');
      return response || [];
    } catch (e) {
      console.error('Failed to fetch variable registry:', e);
      return [];
    }
  },

  getVariableAdapters: async () => {
    try {
      const response = await axiosClient.get('/prompt-variables/adapters');
      return response || [];
    } catch (e) {
      console.error('Failed to fetch variable adapters:', e);
      return [];
    }
  },

  createPromptVariable: async (payload) => {
    try {
      const response = await axiosClient.post('/prompt-variables', payload);
      return response;
    } catch (e) {
      throw e;
    }
  },

  updatePromptVariable: async (id, payload) => {
    try {
      const response = await axiosClient.put(`/prompt-variables/${id}`, payload);
      return response;
    } catch (e) {
      throw e;
    }
  },

  deletePromptVariable: async (id) => {
    try {
      await axiosClient.delete(`/prompt-variables/${id}`);
      return true;
    } catch (e) {
      throw e;
    }
  },

  // ─── Category Workflow Mappings ────────────────────────────────────
  getCategoryWorkflowMappings: async (params = {}) => {
    try {
      const queryParams = new URLSearchParams();
      if (params.category_id) queryParams.append('category_id', params.category_id);
      if (params.workflow_id) queryParams.append('workflow_id', params.workflow_id);
      const response = await axiosClient.get(`/category-workflow-mappings?${queryParams.toString()}`);
      return response || [];
    } catch (e) {
      console.error('Failed to fetch category workflow mappings:', e);
      return [];
    }
  },

  createCategoryWorkflowMapping: async (payload) => {
    try {
      const response = await axiosClient.post('/category-workflow-mappings', payload);
      return response;
    } catch (e) {
      throw e;
    }
  },

  updateCategoryWorkflowMapping: async (id, payload) => {
    try {
      const response = await axiosClient.put(`/category-workflow-mappings/${id}`, payload);
      return response;
    } catch (e) {
      throw e;
    }
  },

  deleteCategoryWorkflowMapping: async (id) => {
    try {
      await axiosClient.delete(`/category-workflow-mappings/${id}`);
      return true;
    } catch (e) {
      throw e;
    }
  },

  // ─── Prompt Sandbox ────────────────────────────────────────────────
  runSandboxTest: async (payload) => {
    try {
      const response = await axiosClient.post('/prompt-sandbox/test', payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  validateSandbox: async (payload) => {
    try {
      const response = await axiosClient.post('/prompt-sandbox/validate', payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  getSandboxHistory: async () => {
    try {
      const response = await axiosClient.get('/prompt-sandbox/history');
      return response || [];
    } catch (e) {
      console.error('Failed to fetch sandbox history:', e);
      return [];
    }
  },

  getSandboxSession: async (sessionId) => {
    try {
      const response = await axiosClient.get(`/prompt-sandbox/history/${sessionId}`);
      return response || null;
    } catch (e) {
      console.error('Failed to fetch sandbox session:', e);
      return null;
    }
  },

  // ─── Prompt Builder ────────────────────────────────────────────────
  buildPrompt: async (payload) => {
    try {
      const response = await axiosClient.post('/prompt-builder/build', payload);
      return response || {};
    } catch (e) {
      throw e;
    }
  },

  detectVariables: async (promptContent) => {
    try {
      const response = await axiosClient.post('/prompt-builder/detect-variables', { prompt_content: promptContent });
      return response || { variables: [] };
    } catch (e) {
      console.error('Failed to detect variables:', e);
      return { variables: [] };
    }
  },
};
