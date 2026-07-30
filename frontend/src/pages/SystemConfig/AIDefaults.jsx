import { useState, useEffect } from 'react';
import { Brain, Save, ChevronDown } from 'lucide-react';
import { api } from '../../api/client';

const TONES = ['professional', 'friendly', 'formal', 'casual', 'empathetic', 'direct', 'technical'];
const LENGTHS = ['concise', 'medium', 'detailed', 'comprehensive'];

export default function AIDefaults({ setFeedback }) {
  const [defaults, setDefaults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.getAIDefaults();
        setDefaults(data);
      } catch { setDefaults(null); }
      finally { setLoading(false); }
    })();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      await api.updateAIDefaults(defaults);
      setFeedback({ type: 'success', message: 'AI defaults saved successfully' });
    } catch (e) {
      setFeedback({ type: 'error', message: e?.response?.data?.detail || 'Failed to save' });
    } finally { setSaving(false); }
  };

  const update = (key, val) => setDefaults(prev => ({ ...prev, [key]: val }));

  if (loading) return <div className="py-12 text-center text-gray-400 text-sm">Loading AI defaults...</div>;
  if (!defaults) return <div className="py-12 text-center text-red-400 text-sm">Failed to load AI defaults</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center border-b border-gray-200 dark:border-gray-700 pb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-600" />
            AI Default Settings
          </h2>
          <p className="text-xs text-gray-500 mt-1">Global AI behavior defaults for all workflows. Individual workflows can override these.</p>
        </div>
        <button onClick={handleSave} disabled={saving} className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 disabled:opacity-50">
          <Save className="w-4 h-4" /> {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Response Behavior</h3>
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Default Tone</label>
            <div className="relative">
              <select value={defaults.default_tone || 'professional'} onChange={e => update('default_tone', e.target.value)} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm appearance-none">
                {TONES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Response Length</label>
            <div className="relative">
              <select value={defaults.response_length || 'medium'} onChange={e => update('response_length', e.target.value)} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm appearance-none">
                {LENGTHS.map(l => <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">
              Creativity Level: <span className="text-purple-600 font-bold">{defaults.creativity_level || 0.7}</span>
            </label>
            <input type="range" min="0" max="1" step="0.1" value={defaults.creativity_level || 0.7} onChange={e => update('creativity_level', parseFloat(e.target.value))} className="w-full" />
            <div className="flex justify-between text-[10px] text-gray-400 mt-1"><span>Precise</span><span>Creative</span></div>
          </div>
        </div>

        <div className="space-y-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Processing Rules</h3>
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Default Language</label>
            <select value={defaults.default_language || 'en'} onChange={e => update('default_language', e.target.value)} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm">
              <option value="en">English</option><option value="es">Spanish</option><option value="fr">French</option>
              <option value="de">German</option><option value="pt">Portuguese</option><option value="ja">Japanese</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Max Tokens per Response</label>
            <input type="number" value={defaults.max_tokens || 4000} onChange={e => update('max_tokens', parseInt(e.target.value) || 4000)} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm" min="100" max="128000" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Max Retry Count</label>
            <input type="number" value={defaults.max_retry_count || 3} onChange={e => update('max_retry_count', parseInt(e.target.value) || 3)} className="w-full p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm" min="0" max="10" />
          </div>
          <div className="flex items-center justify-between pt-2 border-t border-gray-200 dark:border-gray-700">
            <div>
              <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">Require Human Approval</span>
              <p className="text-[10px] text-gray-400">All AI drafts go to approval queue before sending</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={defaults.require_human_approval !== false} onChange={e => update('require_human_approval', e.target.checked)} className="sr-only peer" />
              <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
            </label>
          </div>
          <div className="flex items-center justify-between pt-2 border-t border-gray-200 dark:border-gray-700">
            <div>
              <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">Fallback Enabled</span>
              <p className="text-[10px] text-gray-400">Auto-fallback to next provider on failure</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={defaults.fallback_enabled !== false} onChange={e => update('fallback_enabled', e.target.checked)} className="sr-only peer" />
              <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
