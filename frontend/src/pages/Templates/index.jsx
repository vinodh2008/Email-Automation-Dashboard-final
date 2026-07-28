import { useState, useEffect } from 'react';
import { FileText, Plus, Shield, Sparkles, Trash2, Play, Check, Mail } from 'lucide-react';
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
  const [testResult, setTestResult] = useState('');
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

  const handleRunTest = async () => {
    if (!testingTemplate) return;
    setIsTesting(true);
    setTestResult('');
    try {
      const result = await api.testPromptTemplate(testingTemplate.id, {
        customer_name: 'John Doe',
        email_sender: sampleSender,
        email_subject: sampleSubject,
        email_body: sampleBody
      });
      const safeResult = result || {};
      if (safeResult.success) {
        setTestResult(`--- Rendered Prompt ---\n${safeResult.rendered_prompt || ''}\n\n--- AI Response ---\n${safeResult.ai_response || ''}`);
      } else {
        setTestResult(`Test failed: ${safeResult.error || 'Unknown error'}`);
      }
    } catch (err) {
      setTestResult(`Test failed: ${err.message || 'Unknown error'}`);
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
                          setTestResult('');
                        }}
                        className="text-xs bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 px-2.5 py-1 rounded-lg font-semibold hover:bg-indigo-100 flex items-center gap-1 transition-colors"
                        title="Test Prompt with Sample Inputs"
                      >
                        <Play className="w-3 h-3 fill-current" /> Test Prompt
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
                      try {
                        const vars = JSON.parse(p.variables_json || '[]');
                        return vars.map(v => (
                          <span key={v} className="bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 px-2 py-0.5 rounded font-mono text-[11px]">
                            {`{{${v}}}`}
                          </span>
                        ));
                      } catch {
                        return <span className="text-gray-400">None</span>;
                      }
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
          <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-xl w-full p-6 space-y-5 border border-gray-200 dark:border-gray-700 shadow-xl">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Play className="w-5 h-5 text-indigo-600 fill-current" />
                Test Prompt: {testingTemplate.name}
              </h3>
              <button onClick={() => setTestingTemplate(null)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold uppercase text-gray-400 mb-1">Sample Sender</label>
                  <input
                    type="text"
                    value={sampleSender}
                    onChange={(e) => setSampleSender(e.target.value)}
                    className="w-full text-xs p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold uppercase text-gray-400 mb-1">Sample Subject</label>
                  <input
                    type="text"
                    value={sampleSubject}
                    onChange={(e) => setSampleSubject(e.target.value)}
                    className="w-full text-xs p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase text-gray-400 mb-1">Sample Email Body</label>
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
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
              >
                {isTesting ? 'Generating AI Response...' : '✨ Run Prompt Test & Preview AI Draft'}
              </button>

              {testResult && (
                <div className="space-y-1">
                  <label className="block text-[11px] font-semibold uppercase text-green-600 dark:text-green-400">Generated AI Response Preview</label>
                  <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-xl text-xs font-mono text-gray-800 dark:text-gray-200 border border-green-300 dark:border-green-800 whitespace-pre-wrap">
                    {testResult}
                  </div>
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
