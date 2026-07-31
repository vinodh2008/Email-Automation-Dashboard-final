import { useState, useEffect } from 'react';
import { Shield, Search, Bell, Lock, Eye, ChevronDown } from 'lucide-react';
import { api } from '../../api/client';

const ENTITY_TYPES = [
  { value: '', label: 'All Activity' },
  { value: 'ai_provider', label: 'AI Providers' },
  { value: 'company_settings', label: 'Company Settings' },
  { value: 'ai_defaults', label: 'AI Defaults' },
  { value: 'feature_flags', label: 'Feature Flags' },
  { value: 'feature_flag', label: 'Feature Flag Toggle' },
  { value: 'notification_settings', label: 'Notifications' },
];

const ACTION_COLORS = {
  create: 'bg-green-100 text-green-700',
  update: 'bg-blue-100 text-blue-700',
  delete: 'bg-red-100 text-red-700',
  toggle: 'bg-orange-100 text-orange-700',
};

export default function SecurityAudit({ setFeedback }) {
  const [activeSection, setActiveSection] = useState('audit');
  const [auditLogs, setAuditLogs] = useState({ items: [], total: 0 });
  const [entityFilter, setEntityFilter] = useState('');
  const [auditPage, setAuditPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [notifications, setNotifications] = useState(null);
  const [saving, setSaving] = useState(false);
  const PAGE_SIZE = 20;

  useEffect(() => {
    loadAuditLogs();
  }, [entityFilter, auditPage]);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const data = await api.getNotificationSettings();
        if (!controller.signal.aborted) setNotifications(data);
      } catch { if (!controller.signal.aborted) setNotifications(null); }
    })();
    return () => controller.abort();
  }, []);

  const loadAuditLogs = async () => {
    try {
      setLoading(true);
      const params = { limit: PAGE_SIZE, offset: auditPage * PAGE_SIZE };
      if (entityFilter) params.entity_type = entityFilter;
      const data = await api.getAuditLogs(params);
      setAuditLogs(data);
    } catch { setAuditLogs({ items: [], total: 0 }); }
    finally { setLoading(false); }
  };

  const handleSaveNotifications = async () => {
    try {
      setSaving(true);
      await api.updateNotificationSettings(notifications);
      setFeedback({ type: 'success', message: 'Notification settings saved' });
    } catch (e) {
      setFeedback({ type: 'error', message: 'Failed to save notification settings' });
    } finally { setSaving(false); }
  };

  const sections = [
    { id: 'audit', label: 'Audit Log', icon: <Eye className="w-4 h-4" /> },
    { id: 'notifications', label: 'Alert Preferences', icon: <Bell className="w-4 h-4" /> },
    { id: 'security', label: 'Security Info', icon: <Lock className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Shield className="w-5 h-5 text-emerald-600" />
          Security & Audit
        </h2>
        <p className="text-xs text-gray-500 mt-1">Configuration audit trail, alert preferences, and security information.</p>
      </div>

      <div className="flex gap-2">
        {sections.map(s => (
          <button key={s.id} onClick={() => setActiveSection(s.id)} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${activeSection === s.id ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>
            {s.icon} {s.label}
          </button>
        ))}
      </div>

      {activeSection === 'audit' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-xs">
              <select value={entityFilter} onChange={e => setEntityFilter(e.target.value)} className="w-full p-2 pl-8 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-xs appearance-none">
                {ENTITY_TYPES.map(et => <option key={et.value} value={et.value}>{et.label}</option>)}
              </select>
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            </div>
            <span className="text-xs text-gray-400">{auditLogs.total} entries</span>
          </div>

          <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            {loading ? (
              <div className="py-8 text-center text-gray-400 text-xs">Loading audit logs...</div>
            ) : auditLogs.items.length === 0 ? (
              <div className="py-8 text-center text-gray-400 text-xs">No audit entries found</div>
            ) : (
              <div className="divide-y divide-gray-100 dark:divide-gray-800">
                {auditLogs.items.map(log => (
                  <div key={log.id} className="px-4 py-3 flex items-start gap-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${ACTION_COLORS[log.action] || 'bg-gray-100 text-gray-600'}`}>
                      {log.action}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-semibold text-gray-800 dark:text-gray-200">{log.entity_type.replace(/_/g, ' ')}</div>
                      {log.entity_id && <div className="text-[10px] text-gray-400 font-mono">{log.entity_id}</div>}
                      <div className="text-[10px] text-gray-400 mt-0.5">
                        by {log.user_email || 'system'} {log.ip_address && `from ${log.ip_address}`}
                      </div>
                      {log.old_value && log.new_value && (
                        <div className="text-[10px] text-gray-500 mt-1 bg-white dark:bg-gray-800 rounded p-1.5 font-mono overflow-x-auto">
                          {JSON.stringify(log.new_value, null, 1).slice(0, 200)}
                        </div>
                      )}
                    </div>
                    <span className="text-[10px] text-gray-400 shrink-0">
                      {log.created_at ? new Date(log.created_at).toLocaleString() : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {auditLogs.total > PAGE_SIZE && (
            <div className="flex items-center justify-between pt-3">
              <span className="text-xs text-gray-400">
                Showing {auditPage * PAGE_SIZE + 1}-{Math.min((auditPage + 1) * PAGE_SIZE, auditLogs.total)} of {auditLogs.total}
              </span>
              <div className="flex gap-2">
                <button onClick={() => setAuditPage(p => Math.max(0, p - 1))} disabled={auditPage === 0} className="px-3 py-1 rounded-lg text-xs font-semibold bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed">Prev</button>
                <button onClick={() => setAuditPage(p => p + 1)} disabled={(auditPage + 1) * PAGE_SIZE >= auditLogs.total} className="px-3 py-1 rounded-lg text-xs font-semibold bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed">Next</button>
              </div>
            </div>
          )}
        </div>
      )}

      {activeSection === 'notifications' && notifications && (
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-700 space-y-4">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Alert Preferences</h3>
          {[
            { key: 'provider_failure_alerts', label: 'AI Provider Failure Alerts', desc: 'Get notified when an AI provider fails' },
            { key: 'sync_error_alerts', label: 'Sync Error Alerts', desc: 'Get notified on Gmail sync errors' },
            { key: 'approval_reminders', label: 'Approval Reminders', desc: 'Reminders for pending AI approvals' },
            { key: 'daily_digest', label: 'Daily Digest', desc: 'Receive a daily summary email' },
          ].map(item => (
            <div key={item.key} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800 last:border-0">
              <div>
                <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">{item.label}</span>
                <p className="text-[11px] text-gray-400">{item.desc}</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked={!!notifications[item.key]} onChange={e => setNotifications(prev => ({ ...prev, [item.key]: e.target.checked }))} className="sr-only peer" />
                <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-emerald-300 dark:peer-focus:ring-emerald-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
              </label>
            </div>
          ))}
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Digest Email</label>
            <input type="email" value={notifications.digest_email || ''} onChange={e => setNotifications(prev => ({ ...prev, digest_email: e.target.value }))} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm" placeholder="admin@company.com" />
          </div>
          <button onClick={handleSaveNotifications} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50">
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      )}

      {activeSection === 'security' && (
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-700 space-y-4">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Security Configuration</h3>
          <div className="space-y-3">
            {[
              { label: 'API Key Encryption', status: 'active', desc: 'Fernet symmetric encryption for all API keys at rest' },
              { label: 'OAuth Token Encryption', status: 'active', desc: 'Gmail OAuth tokens encrypted before storage' },
              { label: 'JWT Authentication', status: 'active', desc: 'HS256 JWT tokens with 24h expiry' },
              { label: 'Rate Limiting', status: 'active', desc: '60 req/min general, 5 req/min for login' },
              { label: 'CORS Protection', status: 'active', desc: 'Configured allowed origins only' },
              { label: 'RBAC Permissions', status: 'active', desc: '27 granular permissions across 6 groups' },
            ].map(item => (
              <div key={item.label} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800 last:border-0">
                <div>
                  <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">{item.label}</span>
                  <p className="text-[11px] text-gray-400">{item.desc}</p>
                </div>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-100 text-green-700">Active</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
