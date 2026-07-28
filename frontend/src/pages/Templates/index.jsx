import { useState, useEffect } from 'react';
import { FileText, Plus, Shield, Sparkles, Trash2, Play, Check, Mail, Copy } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

const Templates = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('email');
  const [promptTemplates, setPromptTemplates] = useState([]);
  const [emailTemplates, setEmailTemplates] = useState([]);
  const [loading, setLoading] = useState(true);

  // Create Modal State
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState('');
  const [purpose, setPurpose] = useState('');
  const [content, setContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  // Testing Modal State
  const [testingTemplate, setTestingTemplate] = useState(null);
  const [sampleSender, setSampleSender] = useState('john.doe@acme.com');
  const [sampleSubject, setSampleSubject] = useState('Urgent Refund Request for Order #9910');
  const [sampleBody, setSampleBody] = useState('Hi, I requested a refund 3 days ago for order #9910. Please update me on the status.');
  const [sampleName, setSampleName] = useState('John Doe');
  const [testResult, setTestResult] = useState(null);
  const [isTesting, setIsTesting] = useState(false);

  const fetchPromptTemplates = async () => {
    try {
      setLoading(true);
      const data = await api.getPromptTemplates();
      setPromptTemplates(data || []);
      const emailData = await api.getEmailTemplates();
      setEmailTemplates(Array.isArray(emailData) ? emailData : []);
    } catch (err) {
      console.error('Failed to load templates:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPromptTemplates();
  }, []);

  const handleInsertVariable = (varName) => {
    setContent((prev) => `${prev} {{${varName}}}`);
  };

  const handleSavePrompt = async (e) => {
    e.preventDefault();
    if (!name || !content) return;
    setIsSaving(true);
    try {
      await api.createPromptTemplate({
        name,
        purpose,
        prompt_content: content,
        variables_json: JSON.stringify(['customer_name', 'email_sender', 'email_body', 'email_subject'])
      });
      setName('');
      setPurpose('');
      setContent('');
      setShowModal(false);
      fetchPromptTemplates();
    } catch (err) {
      console.error('Failed to save prompt template:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeletePrompt = async (id) => {
    try {
      await api.deletePromptTemplate(id);
      fetchPromptTemplates();
    } catch (err) {
      console.error('Failed to delete prompt:', err);
    }
  };

  const handleClonePrompt = async (id) => {
    try {
      await api.clonePromptTemplate(id);
      fetchPromptTemplates();
    } catch (err) {
      console.error('Failed to clone prompt:', err);
    }
  };

  const handleRunTest = async () => {
    if (!testingTemplate) return;
    setIsTesting(true);
    setTestResult(null);
    try {
      const vars = {};
      try { vars.templateVars = (testingTemplate.prompt_content || '').match(/\{\{(\w+)\}\}/g) || []; } catch { vars.templateVars = []; }
      const detectedVars = [...new Set((vars.templateVars || []).map(v => v.replace(/\{\{|\}\}/g, '')))];

      const sampleInputs = {};
      for (const v of detectedVars) {
        if (v === 'customer_name' || v === 'name') sampleInputs[v] = sampleName;
        else if (v === 'email_sender' || v === 'sender') sampleInputs[v] = sampleSender;
        else if (v === 'email_subject' || v === 'subject') sampleInputs[v] = sampleSubject;
        else if (v === 'email_body' || v === 'body') sampleInputs[v] = sampleBody;
        else sampleInputs[v] = `[${v}]`;
      }

      const result = await api.testPromptTemplate(testingTemplate.id, sampleInputs);
      setTestResult(result || {});
    } catch (err) {
      setTestResult({ success: false, error: err.message || 'Unknown error' });
    } finally {
      setIsTesting(false);
    }
  };

  if (user?.role !== 'Admin' && user?.role !== 'Editor') {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <Shield className="w-16 h-16 text-red-500 mb-4" />
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Access Denied</h2>
        <p className="text-gray-500 mt-2">You don't have permission to perform this action.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <FileText className="w-6 h-6 text-indigo-600" />
            Template Management
          </h1>
          <p className="text-sm text-gray-500 mt-1">Manage email and AI prompt response templates.</p>
        </div>

        {/* 2 Tabs Selection */}
        <div className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl border border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setActiveTab('email')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'email'
                ? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            Email Templates
          </button>
          <button
            onClick={() => setActiveTab('prompt')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5 ${
              activeTab === 'prompt'
                ? 'bg-white dark:bg-gray-900 text-indigo-600 dark:text-indigo-400 shadow-sm'
                : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <Sparkles className="w-4 h-4 text-indigo-500" />
            Prompt Templates
          </button>
        </div>
      </div>

      {activeTab === 'email' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Mail className="w-5 h-5 text-blue-500" />
              Email Templates
            </h2>
            <button disabled className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium transition-colors opacity-50 cursor-not-allowed" title="Coming soon">
              <Plus className="w-4 h-4" /> Create Email Template
            </button>
          </div>

          {emailTemplates.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-12 flex flex-col items-center text-center">
              <FileText className="w-12 h-12 text-gray-400 mb-3" />
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">No email templates yet</h3>
              <p className="text-sm text-gray-500 max-w-md">Create email templates for outbound campaigns and automated responses.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {emailTemplates.map((t) => (
                <div key={t.id} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-bold text-gray-900 dark:text-white">{t.name}</h3>
                      {t.subject && <p className="text-xs text-gray-500 mt-0.5">Subject: {t.subject}</p>}
                    </div>
                    {t.category && <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-[10px] font-semibold uppercase">{t.category}</span>}
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 text-xs font-mono text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 whitespace-pre-wrap max-h-24 overflow-y-auto">
                    {t.body_html?.substring(0, 200)}...
                  </div>
                  <div className="text-xs text-gray-400">Created: {new Date(t.created_at).toLocaleDateString()}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'prompt' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-500" />
              AI Prompt Templates
            </h2>
            <button
              onClick={() => setShowModal(true)}
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create Prompt Template
            </button>
          </div>

          {promptTemplates.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-12 flex flex-col items-center text-center">
              <div className="w-16 h-16 bg-indigo-50 dark:bg-indigo-950/40 rounded-full flex items-center justify-center mb-4">
                <Sparkles className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">No prompt templates created</h3>
              <p className="text-gray-500 max-w-sm mb-6">Create prompt templates to generate AI responses in automated workflows.</p>
              <button
                onClick={() => setShowModal(true)}
                className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700"
              >
                + Create First Prompt Template
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {promptTemplates.map((p) => (
                <div key={p.id} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 space-y-3 relative group">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-lg font-bold text-gray-900 dark:text-white">{p.name}</h3>
                      <p className="text-xs text-gray-500 mt-0.5">{p.purpose || 'General AI Response'}</p>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded text-gray-500">
                        Used by {p.used_by_workflows || 0} workflow{(p.used_by_workflows || 0) !== 1 ? 's' : ''}
                      </span>
                      <button
                        onClick={() => {
                          setTestingTemplate(p);
                          setTestResult(null);
                        }}
                        className="text-xs bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 px-2.5 py-1 rounded-lg font-semibold hover:bg-indigo-100 flex items-center gap-1 transition-colors"
                        title="Test Prompt with Sample Inputs"
                      >
                        <Play className="w-3 h-3 fill-current" /> Test
                      </button>
                      <button
                        onClick={() => handleClonePrompt(p.id)}
                        className="text-gray-400 hover:text-indigo-500 p-1 rounded-lg transition-colors"
                        title="Clone Template"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeletePrompt(p.id)}
                        className="text-gray-400 hover:text-red-500 p-1 rounded-lg transition-colors"
                        title="Delete Prompt Template"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 text-xs font-mono text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 whitespace-pre-wrap max-h-36 overflow-y-auto">
                    {p.prompt_content}
                  </div>

                  {p.description && (
                    <p className="text-xs text-gray-500 italic">{p.description}</p>
                  )}

                  <div className="flex items-center gap-2 pt-2 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-400 flex-wrap">
                    <span>Variables:</span>
                    {(() => {
                      const contentVars = (p.prompt_content || '').match(/\{\{(\w+)\}\}/g) || [];
                      const detectedVars = [...new Set(contentVars.map(v => v.replace(/\{\{|\}\}/g, '')))];
                      if (detectedVars.length === 0) return <span className="text-gray-400">None detected</span>;
                      return detectedVars.map(v => (
                        <span key={v} className="bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 px-2 py-0.5 rounded font-mono text-[11px]">
                          {`{{${v}}}`}
                        </span>
                      ));
                    })()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal for Creating Prompt Template */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-lg w-full p-6 space-y-5 border border-gray-200 dark:border-gray-700 shadow-xl">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-600" />
                Create Prompt Template
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>

            <form onSubmit={handleSavePrompt} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-gray-500 mb-1">Template Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Customer Refund Reply"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-gray-500 mb-1">Purpose / Notes</label>
                <input
                  type="text"
                  placeholder="e.g. Generates polite refund responses"
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-xs font-semibold uppercase text-gray-500">Prompt Content</label>
                  <span className="text-[11px] text-gray-400">Click chip to insert variable:</span>
                </div>

                {/* Clickable Variable Chips */}
                <div className="flex gap-1.5 mb-2 flex-wrap">
                  {[
                    { label: 'Customer Name', key: 'customer_name' },
                    { label: 'Sender Email', key: 'email_sender' },
                    { label: 'Subject', key: 'email_subject' },
                    { label: 'Body', key: 'email_body' }
                  ].map((v) => (
                    <button
                      key={v.key}
                      type="button"
                      onClick={() => handleInsertVariable(v.key)}
                      className="text-[11px] bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 px-2 py-0.5 rounded font-mono hover:bg-indigo-100 transition-colors"
                    >
                      + {v.label}
                    </button>
                  ))}
                </div>

                <textarea
                  required
                  rows={5}
                  placeholder="Draft a friendly response to customer email:\nSubject: {{email_subject}}\nFrom: {{email_sender}}\n\n{{email_body}}"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm font-mono"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg disabled:opacity-50"
                >
                  {isSaving ? 'Saving...' : 'Save Prompt Template'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal for Prompt Testing */}
      {testingTemplate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-2xl w-full p-6 space-y-5 border border-gray-200 dark:border-gray-700 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Play className="w-5 h-5 text-indigo-600 fill-current" />
                Test: {testingTemplate.name}
              </h3>
              <button onClick={() => { setTestingTemplate(null); setTestResult(null); }} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>

            <div className="space-y-4">
              <div className="bg-indigo-50 dark:bg-indigo-950/40 p-3 rounded-lg border border-indigo-200 dark:border-indigo-800">
                <p className="text-xs font-semibold text-indigo-700 dark:text-indigo-300 mb-1">Prompt Variables</p>
                <p className="text-[11px] text-indigo-600 dark:text-indigo-400">Fill in the variables below. They will replace {'{{variable_name}}'} in the prompt.</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold uppercase text-gray-400 mb-1">Customer Name</label>
                  <input
                    type="text"
                    value={sampleName}
                    onChange={(e) => setSampleName(e.target.value)}
                    className="w-full text-xs p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                    placeholder="John Doe"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold uppercase text-gray-400 mb-1">Sender Email</label>
                  <input
                    type="text"
                    value={sampleSender}
                    onChange={(e) => setSampleSender(e.target.value)}
                    className="w-full text-xs p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase text-gray-400 mb-1">Subject</label>
                <input
                  type="text"
                  value={sampleSubject}
                  onChange={(e) => setSampleSubject(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase text-gray-400 mb-1">Email Body</label>
                <textarea
                  rows={3}
                  value={sampleBody}
                  onChange={(e) => setSampleBody(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                />
              </div>

              <button
                onClick={handleRunTest}
                disabled={isTesting}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
              >
                {isTesting ? (
                  <><div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div> Generating AI Response...</>
                ) : (
                  <><Sparkles className="w-4 h-4" /> Run Test & Preview AI Draft</>
                )}
              </button>

              {testResult && (
                <div className="space-y-3">
                  {testResult.success ? (
                    <>
                      {testResult.execution_time_seconds && (
                        <div className="flex gap-3 text-[11px] text-gray-500 flex-wrap">
                          <span className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">⏱ {testResult.execution_time_seconds}s</span>
                          <span className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">🤖 {testResult.model_used || 'AI'}</span>
                          <span className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">🔌 {testResult.provider_used || 'Provider'}</span>
                          <span className="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">📝 v{testResult.template_version || 'draft'}</span>
                        </div>
                      )}

                      <div className="bg-green-50 dark:bg-green-950/30 p-4 rounded-xl border border-green-200 dark:border-green-800">
                        <label className="text-[11px] font-bold text-green-700 dark:text-green-400 uppercase tracking-wider flex items-center gap-1 mb-2">
                          <Check className="w-3.5 h-3.5" /> Generated AI Draft
                        </label>
                        <div className="text-xs font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed">
                          {testResult.ai_response}
                        </div>
                      </div>

                      <details className="group">
                        <summary className="text-[11px] font-semibold text-gray-400 cursor-pointer hover:text-gray-600 dark:hover:text-gray-300 flex items-center gap-1">
                          <span className="group-open:rotate-90 transition-transform text-[10px]">▶</span> Rendered Prompt (what was sent to AI)
                        </summary>
                        <div className="mt-2 bg-gray-50 dark:bg-gray-900 p-3 rounded-lg text-[11px] font-mono text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 whitespace-pre-wrap max-h-40 overflow-y-auto">
                          {testResult.rendered_prompt}
                        </div>
                      </details>
                    </>
                  ) : (
                    <div className="bg-red-50 dark:bg-red-950/30 p-4 rounded-xl border border-red-200 dark:border-red-800">
                      <p className="text-xs font-semibold text-red-700 dark:text-red-400">Test Failed</p>
                      <p className="text-xs text-red-600 dark:text-red-300 mt-1">{testResult.error}</p>
                      {testResult.missing_variables && (
                        <p className="text-xs text-red-500 mt-1">Missing: {testResult.missing_variables.join(', ')}</p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Templates;
