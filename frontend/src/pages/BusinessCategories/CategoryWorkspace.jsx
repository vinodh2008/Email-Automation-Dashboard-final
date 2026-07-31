import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Settings, Workflow, FileText, Bot, BookOpen, Scale, Radio, Plus, Trash2, Pencil, Save, X, AlertCircle, CheckCircle } from 'lucide-react';
import { api } from '../../api/client';

const TABS = [
  { id: 'overview', label: 'Overview', icon: Settings },
  { id: 'workflows', label: 'Workflows', icon: Workflow },
  { id: 'prompts', label: 'Prompts', icon: FileText },
  { id: 'ai-tasks', label: 'AI Tasks', icon: Bot },
  { id: 'knowledge', label: 'Knowledge', icon: BookOpen },
  { id: 'decision-rules', label: 'Decision Rules', icon: Scale },
  { id: 'channels', label: 'Channels', icon: Radio },
];

export default function CategoryWorkspace() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [category, setCategory] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState(null);

  const [aiTasks, setAiTasks] = useState([]);
  const [knowledgeSources, setKnowledgeSources] = useState([]);
  const [decisionRules, setDecisionRules] = useState([]);
  const [channels, setChannels] = useState([]);
  const [metrics, setMetrics] = useState(null);

  const [showAITaskForm, setShowAITaskForm] = useState(false);
  const [aiTaskForm, setAiTaskForm] = useState({ task_type: 'generate_reply', name: '', description: '', execution_order: 0 });
  const [showKnowledgeForm, setShowKnowledgeForm] = useState(false);
  const [knowledgeForm, setKnowledgeForm] = useState({ name: '', source_type: 'faq', content_text: '', description: '' });
  const [showDecisionForm, setShowDecisionForm] = useState(false);
  const [decisionForm, setDecisionForm] = useState({ name: '', action: 'escalate', min_confidence: 0.9, max_risk_level: 'low', priority: 0 });
  const [editingCategory, setEditingCategory] = useState(false);
  const [catForm, setCatForm] = useState({});

  const fetchCategory = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getBusinessCategory(id);
      setCategory(data);
      setCatForm(data);
    } catch (e) {
      console.error('Failed to load category:', e);
    } finally {
      setLoading(false);
    }
  }, [id]);

  const fetchTabData = useCallback(async () => {
    if (!id) return;
    try {
      if (activeTab === 'ai-tasks') {
        const data = await api.getAITasks(id);
        setAiTasks(Array.isArray(data) ? data : []);
      } else if (activeTab === 'knowledge') {
        const data = await api.getKnowledgeSources(id);
        setKnowledgeSources(Array.isArray(data) ? data : []);
      } else if (activeTab === 'decision-rules') {
        const data = await api.getDecisionRules(id);
        setDecisionRules(Array.isArray(data) ? data : []);
      } else if (activeTab === 'channels') {
        const data = await api.getCategoryChannels(id);
        setChannels(Array.isArray(data) ? data : []);
      } else if (activeTab === 'overview') {
        try {
          const data = await api.getCategoryMetrics(id);
          setMetrics(data);
        } catch { setMetrics(null); }
      }
    } catch (e) {
      console.error(`Failed to load ${activeTab} data:`, e);
    }
  }, [id, activeTab]);

  useEffect(() => { fetchCategory(); }, [fetchCategory]);
  useEffect(() => { fetchTabData(); }, [fetchTabData]);

  useEffect(() => {
    if (!feedback) return;
    const t = setTimeout(() => setFeedback(null), 4000);
    return () => clearTimeout(t);
  }, [feedback]);

  const showFeedback = (type, text) => setFeedback({ type, text });

  const handleCreateAITask = async (e) => {
    e.preventDefault();
    try {
      await api.createAITask({ business_category_id: id, ...aiTaskForm });
      showFeedback('success', 'AI task created');
      setShowAITaskForm(false);
      setAiTaskForm({ task_type: 'generate_reply', name: '', description: '', execution_order: 0 });
      fetchTabData();
    } catch (e) {
      showFeedback('error', e?.response?.data?.detail || 'Failed to create AI task');
    }
  };

  const handleDeleteAITask = async (taskId) => {
    try {
      await api.deleteAITask(taskId);
      showFeedback('success', 'AI task deleted');
      fetchTabData();
    } catch (e) {
      showFeedback('error', 'Failed to delete AI task');
    }
  };

  const handleCreateKnowledge = async (e) => {
    e.preventDefault();
    try {
      await api.createKnowledgeSource({ business_category_id: id, ...knowledgeForm });
      showFeedback('success', 'Knowledge source added');
      setShowKnowledgeForm(false);
      setKnowledgeForm({ name: '', source_type: 'faq', content_text: '', description: '' });
      fetchTabData();
    } catch (e) {
      showFeedback('error', e?.response?.data?.detail || 'Failed to add knowledge source');
    }
  };

  const handleDeleteKnowledge = async (sourceId) => {
    try {
      await api.deleteKnowledgeSource(sourceId);
      showFeedback('success', 'Knowledge source removed');
      fetchTabData();
    } catch (e) {
      showFeedback('error', 'Failed to remove knowledge source');
    }
  };

  const handleCreateDecision = async (e) => {
    e.preventDefault();
    try {
      await api.createDecisionRule({ business_category_id: id, ...decisionForm });
      showFeedback('success', 'Decision rule created');
      setShowDecisionForm(false);
      setDecisionForm({ name: '', action: 'escalate', min_confidence: 0.9, max_risk_level: 'low', priority: 0 });
      fetchTabData();
    } catch (e) {
      showFeedback('error', e?.response?.data?.detail || 'Failed to create decision rule');
    }
  };

  const handleDeleteDecision = async (ruleId) => {
    try {
      await api.deleteDecisionRule(ruleId);
      showFeedback('success', 'Decision rule deleted');
      fetchTabData();
    } catch (e) {
      showFeedback('error', 'Failed to delete decision rule');
    }
  };

  const handleSaveCategory = async () => {
    try {
      await api.updateBusinessCategory(id, catForm);
      showFeedback('success', 'Category updated');
      setEditingCategory(false);
      fetchCategory();
    } catch (e) {
      showFeedback('error', e?.response?.data?.detail || 'Failed to update');
    }
  };

  const inputCls = "w-full px-3 py-2 bg-surface-container border border-outline-variant rounded-md text-on-surface text-sm focus:outline-none focus:ring-2 focus:ring-primary/40";
  const labelCls = "block text-xs font-medium text-on-surface-variant mb-1";
  const tabBtnCls = (active) => `flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${active ? 'bg-primary-container text-on-primary-container' : 'text-on-surface-variant hover:bg-surface-container-high'}`;

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 bg-surface-container rounded animate-pulse w-48" />
        <div className="h-12 bg-surface-container rounded animate-pulse" />
        <div className="h-64 bg-surface-container rounded animate-pulse" />
      </div>
    );
  }

  if (!category) {
    return (
      <div className="text-center py-16">
        <p className="text-on-surface-variant">Category not found</p>
        <button onClick={() => navigate('/business-categories')} className="mt-4 text-primary hover:underline text-sm">Back to Categories</button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/business-categories')} className="p-2 hover:bg-surface-container-high rounded-lg transition-colors">
          <ArrowLeft size={20} className="text-on-surface-variant" />
        </button>
        <div className="w-4 h-4 rounded-full flex-shrink-0" style={{ backgroundColor: category.color || '#6B7280' }} />
        <div>
          <h1 className="text-xl font-bold text-on-surface">{category.name}</h1>
          <p className="text-xs text-on-surface-variant">{category.code} · {category.description || 'No description'}</p>
        </div>
      </div>

      {feedback && (
        <div className={`px-4 py-3 rounded-lg text-sm font-medium flex items-center gap-2 ${
          feedback.type === 'success' ? 'bg-[#DAFBE1] text-[#1A7F37]' : 'bg-error-container text-on-error-container'
        }`}>
          {feedback.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
          {feedback.text}
        </div>
      )}

      <div className="flex gap-1 overflow-x-auto pb-2">
        {TABS.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={tabBtnCls(activeTab === tab.id)}>
            <tab.icon size={16} /> {tab.label}
          </button>
        ))}
      </div>

      <div className="bg-surface-container border border-outline-variant rounded-xl p-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-on-surface">Overview</h2>
              <button onClick={() => setEditingCategory(!editingCategory)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-outline-variant rounded-lg hover:bg-surface-container-high">
                <Pencil size={14} /> Edit
              </button>
            </div>

            {editingCategory ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelCls}>Name</label>
                    <input className={inputCls} value={catForm.name || ''} onChange={e => setCatForm({ ...catForm, name: e.target.value })} />
                  </div>
                  <div>
                    <label className={labelCls}>Description</label>
                    <input className={inputCls} value={catForm.description || ''} onChange={e => setCatForm({ ...catForm, description: e.target.value })} />
                  </div>
                  <div>
                    <label className={labelCls}>Risk Level</label>
                    <select className={inputCls} value={catForm.risk_level || 'medium'} onChange={e => setCatForm({ ...catForm, risk_level: e.target.value })}>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                  <div>
                    <label className={labelCls}>Auto-Approve</label>
                    <select className={inputCls} value={catForm.default_auto_approve ? 'true' : 'false'} onChange={e => setCatForm({ ...catForm, default_auto_approve: e.target.value === 'true' })}>
                      <option value="false">No</option>
                      <option value="true">Yes</option>
                    </select>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={handleSaveCategory} className="flex items-center gap-1.5 px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90">
                    <Save size={14} /> Save
                  </button>
                  <button onClick={() => { setEditingCategory(false); setCatForm(category); }} className="flex items-center gap-1.5 px-4 py-2 border border-outline-variant rounded-lg text-sm font-medium hover:bg-surface-container-high">
                    <X size={14} /> Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: 'Status', value: category.status },
                  { label: 'Priority', value: category.priority },
                  { label: 'Risk Level', value: category.risk_level || 'medium' },
                  { label: 'Auto-Approve', value: category.default_auto_approve ? 'Yes' : 'No' },
                  { label: 'AI Model', value: category.ai_model || 'Inherit global' },
                  { label: 'Temperature', value: category.ai_temperature ?? 'Inherit' },
                  { label: 'Max Tokens', value: category.ai_max_tokens || 'Inherit' },
                  { label: 'Is Default', value: category.is_default ? 'Yes' : 'No' },
                ].map((item, i) => (
                  <div key={i} className="bg-surface p-3 rounded-lg">
                    <p className="text-[10px] uppercase tracking-wider text-on-surface-variant font-bold">{item.label}</p>
                    <p className="text-sm text-on-surface mt-1 font-medium">{item.value}</p>
                  </div>
                ))}
              </div>
            )}

            {metrics && (
              <div>
                <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-3">Metrics</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { label: 'Emails Processed', value: metrics.emails_processed || 0 },
                    { label: 'Drafts Generated', value: metrics.drafts_generated || 0 },
                    { label: 'Approval Rate', value: metrics.approval_rate ? `${(metrics.approval_rate * 100).toFixed(1)}%` : 'N/A' },
                    { label: 'Avg Gen Time', value: metrics.avg_generation_time_ms ? `${metrics.avg_generation_time_ms}ms` : 'N/A' },
                  ].map((item, i) => (
                    <div key={i} className="bg-surface p-2 rounded text-center">
                      <p className="text-lg font-bold text-on-surface">{item.value}</p>
                      <p className="text-[10px] text-on-surface-variant">{item.label}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'ai-tasks' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-on-surface">AI Tasks</h2>
              <button onClick={() => setShowAITaskForm(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-on-primary rounded-lg text-xs font-medium hover:bg-primary/90">
                <Plus size={14} /> Add Task
              </button>
            </div>

            {showAITaskForm && (
              <form onSubmit={handleCreateAITask} className="bg-surface p-4 rounded-lg border border-outline-variant space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={labelCls}>Task Type</label>
                    <select className={inputCls} value={aiTaskForm.task_type} onChange={e => setAiTaskForm({ ...aiTaskForm, task_type: e.target.value })}>
                      <option value="classify">Classify</option>
                      <option value="summarize">Summarize</option>
                      <option value="generate_reply">Generate Reply</option>
                      <option value="extract">Extract Entities</option>
                      <option value="route">Route</option>
                    </select>
                  </div>
                  <div>
                    <label className={labelCls}>Name</label>
                    <input className={inputCls} value={aiTaskForm.name} onChange={e => setAiTaskForm({ ...aiTaskForm, name: e.target.value })} placeholder="e.g. Draft Refund Reply" required />
                  </div>
                </div>
                <div>
                  <label className={labelCls}>Description</label>
                  <input className={inputCls} value={aiTaskForm.description} onChange={e => setAiTaskForm({ ...aiTaskForm, description: e.target.value })} placeholder="What this task does" />
                </div>
                <div className="flex gap-2">
                  <button type="submit" className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90">Create</button>
                  <button type="button" onClick={() => setShowAITaskForm(false)} className="px-4 py-2 border border-outline-variant rounded-lg text-sm font-medium hover:bg-surface-container-high">Cancel</button>
                </div>
              </form>
            )}

            {aiTasks.length === 0 ? (
              <p className="text-sm text-on-surface-variant py-8 text-center">No AI tasks configured. Add a task to get started.</p>
            ) : (
              <div className="space-y-2">
                {aiTasks.map(task => (
                  <div key={task.id} className="flex items-center justify-between bg-surface p-3 rounded-lg border border-outline-variant/50">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center">
                        <Bot size={16} className="text-on-primary-container" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-on-surface">{task.name}</p>
                        <p className="text-xs text-on-surface-variant">{task.task_type} · Order: {task.execution_order}</p>
                      </div>
                    </div>
                    <button onClick={() => handleDeleteAITask(task.id)} className="p-1.5 hover:bg-error-container/30 rounded-lg transition-colors">
                      <Trash2 size={14} className="text-on-error-container" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'knowledge' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-on-surface">Knowledge Sources</h2>
              <button onClick={() => setShowKnowledgeForm(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-on-primary rounded-lg text-xs font-medium hover:bg-primary/90">
                <Plus size={14} /> Add Source
              </button>
            </div>

            {showKnowledgeForm && (
              <form onSubmit={handleCreateKnowledge} className="bg-surface p-4 rounded-lg border border-outline-variant space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={labelCls}>Name</label>
                    <input className={inputCls} value={knowledgeForm.name} onChange={e => setKnowledgeForm({ ...knowledgeForm, name: e.target.value })} placeholder="e.g. Refund Policy" required />
                  </div>
                  <div>
                    <label className={labelCls}>Type</label>
                    <select className={inputCls} value={knowledgeForm.source_type} onChange={e => setKnowledgeForm({ ...knowledgeForm, source_type: e.target.value })}>
                      <option value="faq">FAQ</option>
                      <option value="policy">Policy</option>
                      <option value="manual">Manual</option>
                      <option value="template">Template</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className={labelCls}>Content</label>
                  <textarea className={inputCls} rows={4} value={knowledgeForm.content_text} onChange={e => setKnowledgeForm({ ...knowledgeForm, content_text: e.target.value })} placeholder="Paste knowledge content here..." />
                </div>
                <div className="flex gap-2">
                  <button type="submit" className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90">Create</button>
                  <button type="button" onClick={() => setShowKnowledgeForm(false)} className="px-4 py-2 border border-outline-variant rounded-lg text-sm font-medium hover:bg-surface-container-high">Cancel</button>
                </div>
              </form>
            )}

            {knowledgeSources.length === 0 ? (
              <p className="text-sm text-on-surface-variant py-8 text-center">No knowledge sources yet. Add content to help AI generate better responses.</p>
            ) : (
              <div className="space-y-2">
                {knowledgeSources.map(source => (
                  <div key={source.id} className="flex items-center justify-between bg-surface p-3 rounded-lg border border-outline-variant/50">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center">
                        <BookOpen size={16} className="text-on-secondary-container" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-on-surface">{source.name}</p>
                        <p className="text-xs text-on-surface-variant">{source.source_type} · {source.embedding_status}</p>
                      </div>
                    </div>
                    <button onClick={() => handleDeleteKnowledge(source.id)} className="p-1.5 hover:bg-error-container/30 rounded-lg transition-colors">
                      <Trash2 size={14} className="text-on-error-container" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'decision-rules' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-on-surface">Decision Rules</h2>
              <button onClick={() => setShowDecisionForm(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-on-primary rounded-lg text-xs font-medium hover:bg-primary/90">
                <Plus size={14} /> Add Rule
              </button>
            </div>

            {showDecisionForm && (
              <form onSubmit={handleCreateDecision} className="bg-surface p-4 rounded-lg border border-outline-variant space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={labelCls}>Rule Name</label>
                    <input className={inputCls} value={decisionForm.name} onChange={e => setDecisionForm({ ...decisionForm, name: e.target.value })} placeholder="e.g. High-Confidence Auto-Approve" required />
                  </div>
                  <div>
                    <label className={labelCls}>Action</label>
                    <select className={inputCls} value={decisionForm.action} onChange={e => setDecisionForm({ ...decisionForm, action: e.target.value })}>
                      <option value="auto_approve">Auto-Approve</option>
                      <option value="escalate">Escalate to Human</option>
                      <option value="reject">Reject</option>
                    </select>
                  </div>
                  <div>
                    <label className={labelCls}>Min Confidence</label>
                    <input type="number" step="0.05" min="0" max="1" className={inputCls} value={decisionForm.min_confidence} onChange={e => setDecisionForm({ ...decisionForm, min_confidence: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div>
                    <label className={labelCls}>Max Risk Level</label>
                    <select className={inputCls} value={decisionForm.max_risk_level} onChange={e => setDecisionForm({ ...decisionForm, max_risk_level: e.target.value })}>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button type="submit" className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90">Create</button>
                  <button type="button" onClick={() => setShowDecisionForm(false)} className="px-4 py-2 border border-outline-variant rounded-lg text-sm font-medium hover:bg-surface-container-high">Cancel</button>
                </div>
              </form>
            )}

            {decisionRules.length === 0 ? (
              <p className="text-sm text-on-surface-variant py-8 text-center">No decision rules configured. Rules control auto-approve vs escalation.</p>
            ) : (
              <div className="space-y-2">
                {decisionRules.map(rule => (
                  <div key={rule.id} className="flex items-center justify-between bg-surface p-3 rounded-lg border border-outline-variant/50">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-tertiary-container flex items-center justify-center">
                        <Scale size={16} className="text-on-tertiary-container" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-on-surface">{rule.name}</p>
                        <p className="text-xs text-on-surface-variant">
                          Action: {rule.action} · Min confidence: {rule.min_confidence} · Max risk: {rule.max_risk_level}
                        </p>
                      </div>
                    </div>
                    <button onClick={() => handleDeleteDecision(rule.id)} className="p-1.5 hover:bg-error-container/30 rounded-lg transition-colors">
                      <Trash2 size={14} className="text-on-error-container" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'channels' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-on-surface">Channel Configuration</h2>
            {channels.length === 0 ? (
              <p className="text-sm text-on-surface-variant py-8 text-center">No channel configs. Email is enabled by default.</p>
            ) : (
              <div className="space-y-2">
                {channels.map(ch => (
                  <div key={ch.id} className="flex items-center justify-between bg-surface p-3 rounded-lg border border-outline-variant/50">
                    <div className="flex items-center gap-3">
                      <Radio size={16} className={ch.is_enabled ? 'text-green-500' : 'text-on-surface-variant/40'} />
                      <div>
                        <p className="text-sm font-medium text-on-surface">{ch.channel}</p>
                        <p className="text-xs text-on-surface-variant">{ch.is_enabled ? 'Enabled' : 'Disabled'}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'workflows' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-on-surface">Linked Workflows</h2>
            <p className="text-sm text-on-surface-variant">Workflows linked to this category will be triggered during async email processing.</p>
            <p className="text-xs text-on-surface-variant/60">Configure workflow links from the Workflow Control page.</p>
          </div>
        )}

        {activeTab === 'prompts' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-on-surface">Prompt Templates</h2>
            <p className="text-sm text-on-surface-variant">Manage prompt templates used by AI tasks in this category.</p>
            <button onClick={() => navigate('/prompt-manager')} className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-on-primary rounded-lg text-xs font-medium hover:bg-primary/90">
              <FileText size={14} /> Open Prompt Manager
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
