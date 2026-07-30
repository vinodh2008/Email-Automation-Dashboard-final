import { useState, useEffect, Fragment } from 'react';
import { Settings as SettingsIcon, Shield, Server, Bell, Key, Mail, RefreshCw, CheckCircle2, AlertTriangle, Power, Link2, Activity, Clock, Plus, Trash2, Save, TestTube, Eye, EyeOff, Copy, RotateCcw, Zap, ChevronDown, X, AlertCircle, CopyCheck, Building2, Brain, Flag, BarChart3, TrendingUp, TrendingDown } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useMailbox } from '../../context/MailboxContext';
import { api } from '../../api/client';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import CompanySettings from './CompanySettings';
import AIDefaults from './AIDefaults';
import FeatureFlags from './FeatureFlags';
import SecurityAudit from './SecurityAudit';

const PROVIDER_MODELS = {
  openai: ['gpt-4.1', 'gpt-4.1-mini', 'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'o3-mini'],
  gemini: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro'],
  claude: ['claude-sonnet-4-20250514', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'],
  ollama: ['llama3.1', 'mistral', 'codellama', 'phi3'],
  openai_compatible: [],
};

const PROVIDER_DEFAULTS = {
  openai: { base_url: 'https://api.openai.com/v1', model: 'gpt-4.1' },
  gemini: { base_url: '', model: 'gemini-2.5-pro' },
  claude: { base_url: '', model: 'claude-sonnet-4-20250514' },
  ollama: { base_url: 'http://localhost:11434', model: 'llama3.1' },
  openai_compatible: { base_url: '', model: '' },
};

const SystemConfig = () => {
  const { user } = useAuth();
  const { mailboxes, activeMailbox, isConnected, isSyncing, connectMailbox, disconnectMailbox, reconnectMailbox, syncMailbox } = useMailbox();
  const [activeTab, setActiveTab] = useState('gmail');
  const [systemStatus, setSystemStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const [aiProviders, setAiProviders] = useState([]);
  const [providerHealth, setProviderHealth] = useState([]);
  const [showProviderForm, setShowProviderForm] = useState(false);
  const [editingProvider, setEditingProvider] = useState(null);
  const [providerForm, setProviderForm] = useState(getDefaultProviderForm());
  const [showApiKey, setShowApiKey] = useState(false);
  const [testResults, setTestResults] = useState({});
  const [showDisconnectModal, setShowDisconnectModal] = useState(false);
  const [disconnectDeleteData, setDisconnectDeleteData] = useState(false);

  function getDefaultProviderForm() {
    return {
      name: '', provider_type: 'openai', model: 'gpt-4.1', api_key: '',
      base_url: 'https://api.openai.com/v1', is_primary: false, priority: 0,
      max_tokens: 4000, temperature: 0.7, timeout: 30, retry_count: 3, is_enabled: true,
    };
  }

  useEffect(() => {
    fetchSystemStatus();
    fetchAIProviders();
    fetchProviderHealth();
    const interval = setInterval(fetchSystemStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchSystemStatus = async () => {
    try {
      const sysData = await api.getSystemStatus().catch(() => null);
      if (sysData) setSystemStatus(sysData);
    } catch (e) { console.error('Failed to load system status:', e); }
    finally { setLoading(false); }
  };

  const fetchAIProviders = async () => {
    try {
      const data = await api.getAIProviders();
      setAiProviders(Array.isArray(data) ? data : []);
    } catch (e) { console.error('Failed to load AI providers:', e); }
  };

  const fetchProviderHealth = async () => {
    try {
      const data = await api.getAIProvidersHealth();
      setProviderHealth(Array.isArray(data) ? data : []);
    } catch (e) { console.error('Failed to load provider health:', e); }
  };

  const handleConnect = async () => {
    try {
      setActionLoading(true); setFeedback(null);
      const res = await connectMailbox();
      setFeedback(res.success ? { type: 'success', message: 'Gmail Account Connected Successfully!' } : { type: 'error', message: res.error || 'Failed to connect' });
    } catch (e) { setFeedback({ type: 'error', message: e.message || 'Failed to connect' }); }
    finally { setActionLoading(false); }
  };

  const handleDisconnect = async () => {
    try {
      setActionLoading(true); setFeedback(null); setShowDisconnectModal(false);
      const res = await disconnectMailbox(null, disconnectDeleteData);
      setFeedback(res.success ? { type: 'success', message: disconnectDeleteData ? 'Mailbox disconnected and data deleted' : 'Mailbox disconnected' } : { type: 'error', message: res.error || 'Failed to disconnect' });
    } catch (e) { setFeedback({ type: 'error', message: 'Failed to disconnect' }); }
    finally { setActionLoading(false); setDisconnectDeleteData(false); }
  };

  const handleReconnect = async () => {
    try {
      setActionLoading(true); setFeedback(null);
      const res = await reconnectMailbox();
      setFeedback(res.success ? { type: 'success', message: 'Mailbox re-connected' } : { type: 'error', message: res.error || 'Failed to reconnect' });
    } catch (e) { setFeedback({ type: 'error', message: 'Failed to reconnect' }); }
    finally { setActionLoading(false); }
  };

  const handleManualSync = async () => {
    if (!activeMailbox) return;
    try {
      setActionLoading(true); setFeedback(null);
      const res = await syncMailbox(activeMailbox.id);
      setFeedback(res.success ? { type: 'success', message: 'Sync completed!' } : { type: 'error', message: res.error || 'Sync failed' });
    } catch (e) { setFeedback({ type: 'error', message: e.response?.data?.detail || 'Sync failed' }); }
    finally { setActionLoading(false); }
  };

  const handleProviderTypeChange = (type) => {
    const defaults = PROVIDER_DEFAULTS[type] || {};
    setProviderForm(prev => ({ ...prev, provider_type: type, model: defaults.model || '', base_url: defaults.base_url || '' }));
  };

  const handleSaveProvider = async () => {
    try {
      setActionLoading(true);
      if (editingProvider) {
        await api.updateAIProvider(editingProvider.id, providerForm);
        setFeedback({ type: 'success', message: 'Provider updated successfully' });
      } else {
        await api.createAIProvider(providerForm);
        setFeedback({ type: 'success', message: 'Provider created successfully' });
      }
      setShowProviderForm(false); setEditingProvider(null); setProviderForm(getDefaultProviderForm());
      await fetchAIProviders(); await fetchProviderHealth();
    } catch (e) {
      setFeedback({ type: 'error', message: e?.response?.data?.detail || e?.message || 'Failed to save provider' });
    } finally { setActionLoading(false); }
  };

  const handleTestProvider = async (providerId) => {
    try {
      setTestResults(prev => ({ ...prev, [providerId]: { loading: true } }));
      const response = await api.testAIProvider(providerId);
      const result = response?.data || response || {};
      setTestResults(prev => ({
        ...prev, [providerId]: {
          loading: false, success: !!result.success,
          message: result.success ? (result.message || 'OK') : (result.error || 'Test failed'),
          latency: result.latency_ms || null, model: result.model || null,
        }
      }));
      await fetchAIProviders(); await fetchProviderHealth();
    } catch (e) {
      setTestResults(prev => ({ ...prev, [providerId]: { loading: false, success: false, message: 'Test failed: ' + (e?.message || 'Unknown') } }));
    }
  };

  const handleTestAllProviders = async () => {
    try {
      setActionLoading(true);
      const results = await api.testAllAIProviders();
      const newTestResults = {};
      (Array.isArray(results) ? results : []).forEach(r => {
        newTestResults[r.id] = { loading: false, success: !!r.success, message: r.success ? (r.message || 'OK') : (r.error || 'Failed'), latency: r.latency_ms };
      });
      setTestResults(prev => ({ ...prev, ...newTestResults }));
      await fetchAIProviders(); await fetchProviderHealth();
      setFeedback({ type: 'success', message: 'All providers tested' });
    } catch (e) { setFeedback({ type: 'error', message: 'Failed to test all providers' }); }
    finally { setActionLoading(false); }
  };

  const handleDeleteProvider = async (providerId) => {
    try {
      await api.deleteAIProvider(providerId);
      setFeedback({ type: 'success', message: 'Provider deleted' });
      await fetchAIProviders(); await fetchProviderHealth();
    } catch (e) { setFeedback({ type: 'error', message: e?.response?.data?.detail || 'Failed to delete' }); }
  };

  const copyApiKey = (key) => { navigator.clipboard.writeText(key || ''); setFeedback({ type: 'success', message: 'API key copied' }); };

  if (user?.role !== 'Admin' && user?.role !== 'Editor') {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <Shield className="w-16 h-16 text-red-500 mb-4" />
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Access Denied</h2>
        <p className="text-gray-500 mt-2">You don't have permission to view System Settings.</p>
      </div>
    );
  }

  const sections = [
    { id: 'gmail', title: 'Gmail Connection', icon: <Mail className="w-5 h-5" />, desc: 'Connect, switch account & manage background sync.' },
    { id: 'ai_provider', title: 'AI Providers', icon: <Key className="w-5 h-5 text-indigo-600" />, desc: 'Configure LLM providers, test connections, manage failover.' },
    { id: 'company', title: 'Company Settings', icon: <Building2 className="w-5 h-5 text-blue-600" />, desc: 'Company profile, branding, and business hours.' },
    { id: 'ai_defaults', title: 'AI Defaults', icon: <Brain className="w-5 h-5 text-purple-600" />, desc: 'Global AI behavior defaults for all workflows.' },
    { id: 'features', title: 'Feature Flags', icon: <Flag className="w-5 h-5 text-orange-600" />, desc: 'Enable or disable platform features.' },
    { id: 'security', title: 'Security & Audit', icon: <Shield className="w-5 h-5 text-emerald-600" />, desc: 'Audit trail, alerts, and security info.' },
  ];

  const sortedProviders = [...aiProviders].sort((a, b) => a.priority - b.priority);
  const totalRequests = providerHealth.reduce((sum, p) => sum + (p.total_requests || 0), 0);
  const totalSuccess = providerHealth.reduce((sum, p) => sum + (p.successful_requests || 0), 0);
  const avgHealth = providerHealth.length > 0 ? Math.round(providerHealth.reduce((sum, p) => sum + (p.health_score || 0), 0) / providerHealth.length) : 100;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <SettingsIcon className="w-6 h-6 text-gray-600 dark:text-gray-400" />
          Settings & Integrations
        </h1>
        <p className="text-sm text-gray-500 mt-1">Central control panel for Gmail integration, AI providers, and workspace settings.</p>
      </div>

      {feedback && (
        <div className={`p-4 rounded-xl flex items-center gap-3 text-sm ${feedback.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : feedback.type === 'info' ? 'bg-blue-50 text-blue-800 border border-blue-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
          {feedback.type === 'success' ? <CheckCircle2 className="w-5 h-5 text-green-600" /> : feedback.type === 'info' ? <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" /> : <AlertTriangle className="w-5 h-5 text-red-600" />}
          <span>{feedback.message}</span>
          <button onClick={() => setFeedback(null)} className="ml-auto"><X className="w-4 h-4" /></button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-2">
          {sections.map((sec) => (
            <div key={sec.id} onClick={() => setActiveTab(sec.id)} className={`p-4 rounded-xl cursor-pointer flex items-start gap-3 transition-colors ${activeTab === sec.id ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-400' : 'hover:bg-gray-50 dark:hover:bg-gray-800 border border-transparent text-gray-700 dark:text-gray-300'}`}>
              <div className="mt-0.5">{sec.icon}</div>
              <div>
                <h3 className="text-sm font-bold">{sec.title}</h3>
                <p className="text-xs text-gray-500 mt-1">{sec.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          {activeTab === 'gmail' && (
            <GmailTab activeMailbox={activeMailbox} isConnected={isConnected} isSyncing={isSyncing} systemStatus={systemStatus} actionLoading={actionLoading} onConnect={handleConnect} onDisconnect={() => setShowDisconnectModal(true)} onReconnect={handleReconnect} onManualSync={handleManualSync} />
          )}

          {activeTab === 'ai_provider' && (
            <AITab providers={sortedProviders} providerHealth={providerHealth} showProviderForm={showProviderForm} setShowProviderForm={setShowProviderForm} editingProvider={editingProvider} setEditingProvider={setEditingProvider} providerForm={providerForm} setProviderForm={setProviderForm} showApiKey={showApiKey} setShowApiKey={setShowApiKey} testResults={testResults} actionLoading={actionLoading} onSave={handleSaveProvider} onTest={handleTestProvider} onTestAll={handleTestAllProviders} onDelete={handleDeleteProvider} onCopyKey={copyApiKey} onProviderTypeChange={handleProviderTypeChange} getDefaultForm={getDefaultProviderForm} feedback={feedback} setFeedback={setFeedback} totalRequests={totalRequests} totalSuccess={totalSuccess} avgHealth={avgHealth} />
          )}

          {activeTab === 'company' && <CompanySettings setFeedback={setFeedback} />}
          {activeTab === 'ai_defaults' && <AIDefaults setFeedback={setFeedback} />}
          {activeTab === 'features' && <FeatureFlags setFeedback={setFeedback} />}
          {activeTab === 'security' && <SecurityAudit setFeedback={setFeedback} />}
        </div>
      </div>

      {showDisconnectModal && (
        <DisconnectModal email={activeMailbox?.account_identifier} deleteData={disconnectDeleteData} setDeleteData={setDisconnectDeleteData} onConfirm={handleDisconnect} onCancel={() => { setShowDisconnectModal(false); setDisconnectDeleteData(false); }} loading={actionLoading} />
      )}
    </div>
  );
};

const GmailTab = ({ activeMailbox, isConnected, isSyncing, systemStatus, actionLoading, onConnect, onDisconnect, onReconnect, onManualSync }) => {
  const [healthStatus, setHealthStatus] = useState(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const [dbRes, sysRes] = await Promise.allSettled([api.getSystemStatus(), api.getDatabaseHealth()]);
        setHealthStatus({
          gmail: isConnected ? 'ok' : 'warning',
          scheduler: sysRes.status === 'fulfilled' && sysRes.value?.scheduler?.is_running ? 'ok' : 'warning',
          database: dbRes.status === 'fulfilled' ? 'ok' : 'error',
          storage: 'ok', ai_provider: 'ok',
        });
      } catch { setHealthStatus({ gmail: isConnected ? 'ok' : 'warning', scheduler: 'unknown', database: 'unknown', storage: 'unknown', ai_provider: 'unknown' }); }
    };
    checkHealth();
    const timer = setInterval(checkHealth, 30000);
    return () => clearInterval(timer);
  }, [isConnected]);

  const healthItems = [
    { key: 'gmail', label: 'Gmail Connected', icon: <Mail className="w-4 h-4" /> },
    { key: 'scheduler', label: 'Scheduler Running', icon: <Activity className="w-4 h-4" /> },
    { key: 'database', label: 'Database Connected', icon: <Server className="w-4 h-4" /> },
    { key: 'storage', label: 'Storage Available', icon: <CheckCircle2 className="w-4 h-4" /> },
    { key: 'ai_provider', label: 'AI Provider', icon: <Key className="w-4 h-4" /> },
  ];

  const statusColor = { ok: 'bg-green-100 text-green-700 border-green-200', warning: 'bg-amber-100 text-amber-700 border-amber-200', error: 'bg-red-100 text-red-700 border-red-200', unknown: 'bg-gray-100 text-gray-500 border-gray-200' };
  const statusLabel = { ok: 'Healthy', warning: 'Attention', error: 'Error', unknown: 'Unknown' };

  return (
    <div className="space-y-6">
      <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 text-xs font-bold text-gray-800 dark:text-gray-200 mb-3"><Activity className="w-4 h-4 text-blue-600" /> System Health</div>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {healthItems.map((item) => {
            const status = healthStatus?.[item.key] || 'unknown';
            return (<div key={item.key} className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-semibold ${statusColor[status]}`}>{item.icon}<div className="flex flex-col"><span>{item.label}</span><span className="text-[10px] font-normal opacity-70">{statusLabel[status]}</span></div></div>);
          })}
        </div>
      </div>

      <div className="flex justify-between items-center border-b border-gray-200 dark:border-gray-700 pb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2"><Mail className="w-5 h-5 text-blue-600" /> Gmail Connection Lifecycle</h2>
          <p className="text-xs text-gray-500 mt-1">Connect, switch account & manage background sync.</p>
        </div>
        {isConnected && <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800"><CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Connected</span>}
        {isSyncing && <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800"><RefreshCw className="w-3.5 h-3.5 mr-1 animate-spin" /> Syncing</span>}
      </div>

      {activeMailbox ? (
        <div className="space-y-6">
          <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-700 space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
              <div><div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Current Gmail Address</div><div className="text-lg font-bold text-gray-900 dark:text-white mt-0.5">{activeMailbox.account_identifier}</div></div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-gray-200 dark:border-gray-700 text-xs">
              <div><span className="text-gray-500">Sync Status: </span><span className={`font-semibold capitalize ${isConnected ? 'text-green-600' : 'text-amber-600'}`}>{activeMailbox.sync_status}</span></div>
              <div><span className="text-gray-500">Last Synced: </span><span className="font-medium text-gray-900 dark:text-white">{activeMailbox.last_sync_at ? new Date(activeMailbox.last_sync_at).toLocaleString() : 'Never'}</span></div>
            </div>
          </div>

          {systemStatus?.scheduler && (
            <div className="bg-blue-50/60 dark:bg-blue-950/20 rounded-xl p-5 border border-blue-200 dark:border-blue-800 space-y-3">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2 font-bold text-sm text-gray-900 dark:text-white"><Activity className="w-4 h-4 text-blue-600" /> APScheduler Status</div>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${systemStatus.scheduler.is_running ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>{systemStatus.scheduler.is_running ? 'RUNNING' : 'STOPPED'}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
                <div className="bg-white dark:bg-gray-800 p-2.5 rounded-lg border border-gray-200 dark:border-gray-700"><div className="text-gray-400 text-[10px] uppercase font-semibold">Health</div><div className="font-bold text-green-600 text-sm mt-0.5">{systemStatus.health_score}%</div></div>
                <div className="bg-white dark:bg-gray-800 p-2.5 rounded-lg border border-gray-200 dark:border-gray-700"><div className="text-gray-400 text-[10px] uppercase font-semibold">Interval</div><div className="font-bold text-gray-800 dark:text-white text-sm mt-0.5">{systemStatus.scheduler.interval_minutes}m</div></div>
                <div className="bg-white dark:bg-gray-800 p-2.5 rounded-lg border border-gray-200 dark:border-gray-700"><div className="text-gray-400 text-[10px] uppercase font-semibold">Runs</div><div className="font-bold text-gray-800 dark:text-white text-sm mt-0.5">{systemStatus.scheduler.execution_count}</div></div>
                <div className="bg-white dark:bg-gray-800 p-2.5 rounded-lg border border-gray-200 dark:border-gray-700"><div className="text-gray-400 text-[10px] uppercase font-semibold">Failures</div><div className="font-bold text-red-600 text-sm mt-0.5">{systemStatus.scheduler.failure_count}</div></div>
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button onClick={onManualSync} disabled={actionLoading || !isConnected} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50"><RefreshCw className={`w-4 h-4 ${actionLoading ? 'animate-spin' : ''}`} /> Manual Sync</button>
            <button onClick={onReconnect} disabled={actionLoading} className="bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50"><Link2 className="w-4 h-4 text-blue-500" /> Reconnect</button>
            {isConnected && <button onClick={onDisconnect} disabled={actionLoading} className="bg-red-50 hover:bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ml-auto disabled:opacity-50"><Power className="w-4 h-4" /> Disconnect</button>}
          </div>
        </div>
      ) : (
        <div className="text-center py-12 space-y-4">
          <div className="w-16 h-16 bg-blue-50 dark:bg-blue-900/20 text-blue-600 rounded-full flex items-center justify-center mx-auto"><Mail className="w-8 h-8" /></div>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">No Gmail Account Connected</h3>
          <p className="text-sm text-gray-500 max-w-md mx-auto">Connect your Gmail account to enable automated sync, attachment storage, and AI workflows.</p>
          <button onClick={onConnect} disabled={actionLoading} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-medium shadow-sm transition-colors disabled:opacity-50">{actionLoading ? 'Connecting...' : 'Connect Gmail Account'}</button>
        </div>
      )}
    </div>
  );
};

const AITab = ({
  providers, providerHealth, showProviderForm, setShowProviderForm, editingProvider, setEditingProvider,
  providerForm, setProviderForm, showApiKey, setShowApiKey, testResults, actionLoading,
  onSave, onTest, onTestAll, onDelete, onCopyKey, onProviderTypeChange, getDefaultForm,
  feedback, setFeedback, totalRequests, totalSuccess, avgHealth
}) => {
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const availableModels = PROVIDER_MODELS[providerForm.provider_type] || [];

  const healthMap = {};
  (providerHealth || []).forEach(h => { healthMap[h.id] = h; });

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center border-b border-gray-200 dark:border-gray-700 pb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2"><Key className="w-5 h-5 text-indigo-600" /> AI Provider Configuration</h2>
          <p className="text-xs text-gray-500 mt-1">Configure LLM providers, test connections, manage failover pipeline.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onTestAll} disabled={actionLoading || providers.length === 0} className="bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-white px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5 disabled:opacity-50"><TestTube className="w-3.5 h-3.5" /> Test All</button>
          <button onClick={() => { setShowProviderForm(true); setEditingProvider(null); setProviderForm(getDefaultForm()); }} className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2"><Plus className="w-4 h-4" /> Add Provider</button>
        </div>
      </div>

      {providers.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-3 border border-gray-200 dark:border-gray-700 text-center">
            <div className="text-[10px] text-gray-400 uppercase font-semibold">Total Requests</div>
            <div className="text-lg font-bold text-gray-900 dark:text-white">{totalRequests}</div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-3 border border-gray-200 dark:border-gray-700 text-center">
            <div className="text-[10px] text-gray-400 uppercase font-semibold">Success Rate</div>
            <div className="text-lg font-bold text-green-600">{totalRequests > 0 ? Math.round((totalSuccess / totalRequests) * 100) : 100}%</div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-3 border border-gray-200 dark:border-gray-700 text-center">
            <div className="text-[10px] text-gray-400 uppercase font-semibold">Avg Health</div>
            <div className={`text-lg font-bold ${avgHealth >= 80 ? 'text-green-600' : avgHealth >= 50 ? 'text-amber-600' : 'text-red-600'}`}>{avgHealth}%</div>
          </div>
        </div>
      )}

      {showProviderForm && (
        <ProviderForm form={providerForm} setForm={setProviderForm} editing={editingProvider} showApiKey={showApiKey} setShowApiKey={setShowApiKey} availableModels={availableModels} onTypeChange={onProviderTypeChange} onSave={onSave} onCancel={() => { setShowProviderForm(false); setEditingProvider(null); setProviderForm(getDefaultForm()); }} loading={actionLoading} />
      )}

      <div className="space-y-3">
        {providers.length === 0 ? (
          <div className="text-center py-8 text-gray-500"><Key className="w-12 h-12 mx-auto mb-3 text-gray-400" /><p className="font-medium">No AI providers configured</p><p className="text-xs mt-1">Add a provider to enable AI-powered workflows.</p></div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-3 py-3 text-left font-semibold text-gray-500">#</th>
                  <th className="px-3 py-3 text-left font-semibold text-gray-500">Provider</th>
                  <th className="px-3 py-3 text-left font-semibold text-gray-500">Model</th>
                  <th className="px-3 py-3 text-left font-semibold text-gray-500">Status</th>
                  <th className="px-3 py-3 text-left font-semibold text-gray-500">Health</th>
                  <th className="px-3 py-3 text-left font-semibold text-gray-500">Requests</th>
                  <th className="px-3 py-3 text-left font-semibold text-gray-500">Latency</th>
                  <th className="px-3 py-3 text-left font-semibold text-gray-500">Primary</th>
                  <th className="px-3 py-3 text-right font-semibold text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {providers.map((p) => {
                  const tr = testResults[p.id];
                  const h = healthMap[p.id];
                  return (
                    <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                      <td className="px-3 py-3"><span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 font-bold text-xs">{p.priority}</span></td>
                      <td className="px-3 py-3"><div className="font-semibold text-gray-900 dark:text-white">{p.name}</div><div className="text-[10px] text-gray-400 capitalize">{p.provider_type}</div></td>
                      <td className="px-3 py-3 font-mono text-gray-700 dark:text-gray-300">{p.model}</td>
                      <td className="px-3 py-3">
                        <span className={`inline-flex items-center gap-1 font-semibold ${p.status === 'active' ? 'text-green-600' : p.status === 'error' ? 'text-red-600' : 'text-gray-400'}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${p.status === 'active' ? 'bg-green-500' : p.status === 'error' ? 'bg-red-500' : 'bg-gray-300'}`} />
                          {p.status === 'active' ? 'Connected' : p.status === 'error' ? 'Error' : 'Not Tested'}
                        </span>
                        {tr && !tr.loading && <div className={`text-[10px] mt-0.5 ${tr.success ? 'text-green-500' : 'text-red-500'}`}>{tr.message} {tr.latency && `(${tr.latency}ms)`}</div>}
                      </td>
                      <td className="px-3 py-3">
                        {h ? (
                          <div className="flex items-center gap-1">
                            <div className={`w-8 h-1.5 rounded-full ${h.health_score >= 80 ? 'bg-green-400' : h.health_score >= 50 ? 'bg-amber-400' : 'bg-red-400'}`} />
                            <span className="text-[10px] font-bold text-gray-600">{h.health_score}%</span>
                          </div>
                        ) : <span className="text-[10px] text-gray-400">--</span>}
                      </td>
                      <td className="px-3 py-3">
                        {h ? (
                          <div className="text-[10px]"><span className="text-green-600 font-bold">{h.successful_requests}</span>/<span className="text-gray-500">{h.total_requests}</span></div>
                        ) : <span className="text-[10px] text-gray-400">0</span>}
                      </td>
                      <td className="px-3 py-3">
                        {h?.avg_latency_ms ? <span className="text-[10px] font-mono text-gray-600">{h.avg_latency_ms}ms</span> : p.latency_ms ? <span className="text-[10px] font-mono text-gray-600">{p.latency_ms}ms</span> : <span className="text-[10px] text-gray-400">--</span>}
                      </td>
                      <td className="px-3 py-3">
                        {p.is_primary ? <span className="inline-flex items-center gap-1 text-indigo-600 font-semibold text-xs"><Zap className="w-3 h-3" /> Primary</span> : <span className="text-gray-400 text-xs">Fallback #{p.priority}</span>}
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button onClick={() => onTest(p.id)} disabled={tr?.loading} className="bg-indigo-100 hover:bg-indigo-200 text-indigo-700 px-2 py-1 rounded-lg text-[10px] font-semibold flex items-center gap-1 transition-colors">{tr?.loading ? <RefreshCw className="w-3 h-3 animate-spin" /> : <TestTube className="w-3 h-3" />} Test</button>
                          <button onClick={() => { setEditingProvider(p); setProviderForm({ name: p.name, provider_type: p.provider_type, model: p.model, api_key: '', base_url: p.base_url || '', is_primary: p.is_primary, priority: p.priority, max_tokens: p.max_tokens || 4000, temperature: p.temperature || 0.7, timeout: p.timeout || 30, retry_count: p.retry_count || 3, is_enabled: p.is_enabled }); setShowProviderForm(true); }} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-[10px] font-semibold">Edit</button>
                          <button onClick={() => setDeleteConfirmId(p.id)} className="text-red-400 hover:text-red-600 px-2 py-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20"><Trash2 className="w-3.5 h-3.5" /></button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {providers.length > 1 && (
          <div className="bg-blue-50/60 dark:bg-blue-950/20 rounded-xl p-4 border border-blue-200 dark:border-blue-800">
            <div className="flex items-center gap-2 text-xs font-bold text-blue-800 dark:text-blue-300 mb-2"><Zap className="w-4 h-4" /> Automatic Failover Pipeline</div>
            <div className="flex items-center gap-2 text-xs text-blue-700 dark:text-blue-400 flex-wrap">
              {providers.map((p, i) => (<Fragment key={p.id}><span className="bg-white dark:bg-gray-800 px-2 py-1 rounded border border-blue-200 dark:border-blue-700 font-semibold">{p.name}</span>{i < providers.length - 1 && <span className="text-blue-400">→</span>}</Fragment>))}
              <span className="text-blue-400">→</span>
              <span className="bg-white dark:bg-gray-800 px-2 py-1 rounded border border-blue-200 dark:border-blue-700 font-semibold text-gray-500">Static Fallback</span>
            </div>
            <p className="text-[10px] text-blue-600 dark:text-blue-500 mt-2">If Priority 1 fails, the system automatically tries Priority 2, then 3. No administrator intervention needed.</p>
          </div>
        )}
      </div>

      <ConfirmDialog isOpen={deleteConfirmId !== null} onClose={() => setDeleteConfirmId(null)} onConfirm={() => { onDelete(deleteConfirmId); setDeleteConfirmId(null); }} title="Delete AI Provider" message="Are you sure you want to delete this AI provider? This action cannot be undone." confirmText="Delete" cancelText="Cancel" isDestructive={true} />
    </div>
  );
};

const ProviderForm = ({ form, setForm, editing, showApiKey, setShowApiKey, availableModels, onTypeChange, onSave, onCancel, loading }) => (
  <div className="bg-gray-50 dark:bg-gray-900 rounded-xl p-5 border border-gray-200 dark:border-gray-700 space-y-5">
    <h3 className="font-bold text-sm text-gray-900 dark:text-white">{editing ? 'Edit Provider' : 'Add New Provider'}</h3>
    <div className="grid grid-cols-2 gap-4 text-xs">
      <div><label className="block text-gray-400 font-semibold mb-1">Provider Name</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white" placeholder="OpenAI Production" /></div>
      <div><label className="block text-gray-400 font-semibold mb-1">Provider Type</label><div className="relative"><select value={form.provider_type} onChange={(e) => onTypeChange(e.target.value)} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white appearance-none"><option value="openai">OpenAI</option><option value="gemini">Google Gemini</option><option value="claude">Anthropic Claude</option><option value="ollama">Ollama (Local)</option><option value="openai_compatible">OpenAI Compatible</option></select><ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" /></div></div>
      <div><label className="block text-gray-400 font-semibold mb-1">Model</label>{availableModels.length > 0 ? (<div className="relative"><select value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white appearance-none">{availableModels.map(m => <option key={m} value={m}>{m}</option>)}</select><ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" /></div>) : (<input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono" placeholder="model-name" />)}</div>
      <div><label className="block text-gray-400 font-semibold mb-1">Priority</label><input type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: parseInt(e.target.value) || 0 })} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white" min="0" /><p className="text-[10px] text-gray-400 mt-1">Lowest number wins. 1 = Primary</p></div>
    </div>
    <div className="space-y-3"><h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Connection</h4><div className="grid grid-cols-2 gap-4 text-xs">
      <div><label className="block text-gray-400 font-semibold mb-1">API Key</label><div className="relative"><input type={showApiKey ? 'text' : 'password'} value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} className="w-full p-2.5 pr-20 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono" placeholder={editing ? 'Leave blank to keep existing' : 'sk-...'} /><div className="absolute right-1 top-1/2 -translate-y-1/2 flex items-center gap-0.5"><button type="button" onClick={() => setShowApiKey(!showApiKey)} className="p-1.5 text-gray-400 hover:text-gray-600 rounded">{showApiKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}</button><button type="button" onClick={() => navigator.clipboard.writeText(form.api_key)} className="p-1.5 text-gray-400 hover:text-gray-600 rounded"><Copy className="w-3.5 h-3.5" /></button></div></div></div>
      {(form.provider_type === 'openai_compatible' || form.provider_type === 'ollama') && (<div><label className="block text-gray-400 font-semibold mb-1">Base URL</label><input value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono text-[11px]" placeholder="https://api.openai.com/v1" /></div>)}
    </div></div>
    <div className="space-y-3"><h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Parameters</h4><div className="grid grid-cols-4 gap-4 text-xs">
      <div><label className="block text-gray-400 font-semibold mb-1">Temperature</label><input type="number" step="0.1" min="0" max="2" value={form.temperature} onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) || 0.7 })} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white" /></div>
      <div><label className="block text-gray-400 font-semibold mb-1">Max Tokens</label><input type="number" value={form.max_tokens} onChange={(e) => setForm({ ...form, max_tokens: parseInt(e.target.value) || 4000 })} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white" /></div>
      <div><label className="block text-gray-400 font-semibold mb-1">Timeout (sec)</label><input type="number" value={form.timeout} onChange={(e) => setForm({ ...form, timeout: parseInt(e.target.value) || 30 })} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white" /></div>
      <div><label className="block text-gray-400 font-semibold mb-1">Retry Count</label><input type="number" value={form.retry_count} onChange={(e) => setForm({ ...form, retry_count: parseInt(e.target.value) || 3 })} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white" /></div>
    </div></div>
    <div className="space-y-3"><h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Status</h4><div className="flex items-center gap-6"><label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={form.is_enabled} onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })} className="rounded" /> Provider Enabled</label><label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={form.is_primary} onChange={(e) => setForm({ ...form, is_primary: e.target.checked })} className="rounded" /> Primary Provider</label></div></div>
    <div className="flex justify-end gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
      <button onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200">Cancel</button>
      <button onClick={onSave} disabled={loading || !form.name} className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 flex items-center gap-2"><Save className="w-4 h-4" />{editing ? 'Update Provider' : 'Create Provider'}</button>
    </div>
  </div>
);

const DisconnectModal = ({ email, deleteData, setDeleteData, onConfirm, onCancel, loading }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onCancel}>
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-lg w-full mx-4 p-6 space-y-5" onClick={(e) => e.stopPropagation()}>
      <div className="flex items-center gap-3"><div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center"><AlertCircle className="w-5 h-5 text-red-600" /></div><div><h3 className="text-lg font-bold text-gray-900 dark:text-white">Disconnect Gmail?</h3><p className="text-xs text-gray-500">This will affect {email || 'your connected account'}</p></div></div>
      <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-4 space-y-2 text-xs text-gray-600 dark:text-gray-400">
        <p className="font-semibold text-gray-800 dark:text-gray-200 mb-2">When you disconnect:</p>
        <div className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" /> Stop Scheduler polling</div>
        <div className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" /> Pause AI processing</div>
        <div className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" /> Pause all Workflows</div>
        <div className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" /> Stop Email Monitoring</div>
        <div className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" /> Clear active mailbox session</div>
      </div>
      <div className="bg-amber-50 dark:bg-amber-900/10 rounded-xl p-4 border border-amber-200 dark:border-amber-800">
        <label className="flex items-start gap-3 cursor-pointer"><input type="checkbox" checked={deleteData} onChange={(e) => setDeleteData(e.target.checked)} className="mt-0.5 rounded" /><div><span className="text-xs font-semibold text-amber-800 dark:text-amber-300">Also delete all synced emails and attachments</span><p className="text-[10px] text-amber-600 dark:text-amber-400 mt-1">Normally leave unchecked. Only check for a completely fresh start.</p></div></label>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <button onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 border border-gray-200 dark:border-gray-700 rounded-lg">Cancel</button>
        <button onClick={onConfirm} disabled={loading} className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 flex items-center gap-2"><Power className="w-4 h-4" />{loading ? 'Disconnecting...' : 'Disconnect'}</button>
      </div>
    </div>
  </div>
);

export default SystemConfig;
