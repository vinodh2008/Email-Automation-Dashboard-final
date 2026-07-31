import { useState, useEffect } from 'react';
import { Building2, Save, CheckCircle2, Globe, Clock, Mail, Palette } from 'lucide-react';
import { api } from '../../api/client';

const TIMEZONES = [
  'UTC', 'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
  'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Asia/Tokyo', 'Asia/Shanghai',
  'Asia/Kolkata', 'Australia/Sydney', 'Pacific/Auckland',
];

const LANGUAGES = [
  { code: 'en', label: 'English' }, { code: 'es', label: 'Spanish' },
  { code: 'fr', label: 'French' }, { code: 'de', label: 'German' },
  { code: 'pt', label: 'Portuguese' }, { code: 'ja', label: 'Japanese' },
  { code: 'zh', label: 'Chinese' }, { code: 'hi', label: 'Hindi' },
];

const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];

export default function CompanySettings({ setFeedback }) {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const data = await api.getCompanySettings();
        if (!controller.signal.aborted) setSettings(data);
      } catch { if (!controller.signal.aborted) setSettings(null); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    })();
    return () => controller.abort();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      await api.updateCompanySettings(settings);
      setFeedback({ type: 'success', message: 'Company settings saved successfully' });
    } catch (e) {
      setFeedback({ type: 'error', message: e?.response?.data?.detail || 'Failed to save' });
    } finally { setSaving(false); }
  };

  const update = (key, val) => setSettings(prev => ({ ...prev, [key]: val }));
  const updateBranding = (key, val) => setSettings(prev => ({ ...prev, branding: { ...prev.branding, [key]: val } }));
  const updateHours = (day, key, val) => setSettings(prev => ({
    ...prev,
    business_hours: { ...prev.business_hours, [day]: { ...prev.business_hours[day], [key]: val } },
  }));

  if (loading) return <div className="py-12 text-center text-gray-400 text-sm">Loading company settings...</div>;
  if (!settings) return <div className="py-12 text-center text-red-400 text-sm">Failed to load settings</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center border-b border-gray-200 dark:border-gray-700 pb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Building2 className="w-5 h-5 text-blue-600" />
            Company Settings
          </h2>
          <p className="text-xs text-gray-500 mt-1">Company profile, branding, and business hours configuration.</p>
        </div>
        <button onClick={handleSave} disabled={saving} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 disabled:opacity-50">
          <Save className="w-4 h-4" /> {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Company Profile</h3>
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Company Name</label>
            <input value={settings.company_name || ''} onChange={e => update('company_name', e.target.value)} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Support Email</label>
            <input type="email" value={settings.support_email || ''} onChange={e => update('support_email', e.target.value)} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm" placeholder="support@company.com" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Default Email Signature</label>
            <textarea value={settings.default_signature || ''} onChange={e => update('default_signature', e.target.value)} rows={3} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm resize-none" placeholder="Best regards," />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1"><Globe className="w-3 h-3 inline mr-1" />Language</label>
              <select value={settings.default_language || 'en'} onChange={e => update('default_language', e.target.value)} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm">
                {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1"><Clock className="w-3 h-3 inline mr-1" />Timezone</label>
              <select value={settings.timezone || 'UTC'} onChange={e => update('timezone', e.target.value)} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm">
                {TIMEZONES.map(tz => <option key={tz} value={tz}>{tz}</option>)}
              </select>
            </div>
          </div>
        </div>

        <div className="space-y-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider"><Palette className="w-3 h-3 inline mr-1" />Branding</h3>
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Logo URL</label>
            <input value={settings.branding?.logo_url || ''} onChange={e => updateBranding('logo_url', e.target.value)} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm" placeholder="https://..." />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Primary Color</label>
            <div className="flex items-center gap-2">
              <input type="color" value={settings.branding?.primary_color || '#4F46E5'} onChange={e => updateBranding('primary_color', e.target.value)} className="w-10 h-10 rounded border border-gray-300 dark:border-gray-700 cursor-pointer" />
              <input value={settings.branding?.primary_color || '#4F46E5'} onChange={e => updateBranding('primary_color', e.target.value)} className="flex-1 p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm font-mono" />
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4"><Clock className="w-3 h-3 inline mr-1" />Business Hours</h3>
        <div className="space-y-2">
          {DAYS.map(day => (
            <div key={day} className="flex items-center gap-3 text-sm">
              <label className="flex items-center gap-2 w-28">
                <input type="checkbox" checked={settings.business_hours?.[day]?.enabled !== false} onChange={e => updateHours(day, 'enabled', e.target.checked)} className="rounded" />
                <span className="capitalize font-medium text-gray-700 dark:text-gray-300">{day}</span>
              </label>
              <input type="time" value={settings.business_hours?.[day]?.start || '09:00'} onChange={e => updateHours(day, 'start', e.target.value)} className="p-1.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-xs" disabled={settings.business_hours?.[day]?.enabled === false} />
              <span className="text-gray-400">to</span>
              <input type="time" value={settings.business_hours?.[day]?.end || '17:00'} onChange={e => updateHours(day, 'end', e.target.value)} className="p-1.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-xs" disabled={settings.business_hours?.[day]?.enabled === false} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
