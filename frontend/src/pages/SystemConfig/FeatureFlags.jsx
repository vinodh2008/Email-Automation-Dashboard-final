import { useState, useEffect } from 'react';
import { Flag, Save, CheckCircle2, XCircle } from 'lucide-react';
import { api } from '../../api/client';

const FLAGS = [
  { key: 'email_summarization', label: 'Email Summarization', desc: 'AI-powered email content summarization', category: 'AI Processing' },
  { key: 'draft_reply_generation', label: 'Draft Reply Generation', desc: 'Auto-generate email draft replies using AI', category: 'AI Processing' },
  { key: 'rag_enabled', label: 'RAG (Retrieval Augmented Generation)', desc: 'Context-aware responses using document retrieval', category: 'AI Processing' },
  { key: 'business_rules_engine', label: 'Business Rules Engine', desc: 'Advanced conditional logic for workflows', category: 'Workflows' },
  { key: 'email_sending', label: 'Email Sending', desc: 'Allow AI to send emails after approval', category: 'Workflows' },
  { key: 'auto_approval', label: 'Auto-Approval', desc: 'Skip human approval for low-risk responses', category: 'Workflows' },
  { key: 'advanced_analytics', label: 'Advanced Analytics', desc: 'Detailed performance and usage analytics', category: 'Platform' },
  { key: 'multi_language_support', label: 'Multi-Language Support', desc: 'Process emails in multiple languages', category: 'Platform' },
];

const CATEGORIES = [...new Set(FLAGS.map(f => f.category))];

export default function FeatureFlags({ setFeedback }) {
  const [flags, setFlags] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.getFeatureFlags();
        setFlags(data);
      } catch { setFlags(null); }
      finally { setLoading(false); }
    })();
  }, []);

  const handleToggle = async (key) => {
    const newVal = !flags[key];
    setFlags(prev => ({ ...prev, [key]: newVal }));
    try {
      await api.toggleFeatureFlag(key, newVal);
      setFeedback({ type: 'success', message: `${key} ${newVal ? 'enabled' : 'disabled'}` });
    } catch (e) {
      setFlags(prev => ({ ...prev, [key]: !newVal }));
      setFeedback({ type: 'error', message: 'Failed to toggle flag' });
    }
  };

  if (loading) return <div className="py-12 text-center text-gray-400 text-sm">Loading feature flags...</div>;
  if (!flags) return <div className="py-12 text-center text-red-400 text-sm">Failed to load feature flags</div>;

  const enabledCount = Object.values(flags).filter(Boolean).length;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center border-b border-gray-200 dark:border-gray-700 pb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Flag className="w-5 h-5 text-orange-600" />
            Feature Flags
          </h2>
          <p className="text-xs text-gray-500 mt-1">Enable or disable platform features. Changes take effect immediately.</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-gray-500">Enabled:</span>
          <span className="bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full font-bold">{enabledCount}/{FLAGS.length}</span>
        </div>
      </div>

      {CATEGORIES.map(cat => (
        <div key={cat} className="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">{cat}</h3>
          <div className="space-y-3">
            {FLAGS.filter(f => f.category === cat).map(flag => (
              <div key={flag.key} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800 last:border-0">
                <div>
                  <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">{flag.label}</span>
                  <p className="text-[11px] text-gray-400 mt-0.5">{flag.desc}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer shrink-0">
                  <input type="checkbox" checked={!!flags[flag.key]} onChange={() => handleToggle(flag.key)} className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-orange-300 dark:peer-focus:ring-orange-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange-600"></div>
                </label>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
