import { useState, useEffect, useCallback } from 'react';
import { Plus, Pencil, Trash2, Play, FileText, History, Copy, Archive, RotateCcw, CheckCircle, XCircle, AlertTriangle, Eye, ChevronDown, ChevronRight } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';
import { Modal } from '../../components/Modal';
import { ConfirmDialog } from '../../components/ConfirmDialog';

const STATUS_COLORS = {
  draft: { bg: 'bg-surface-container-high', text: 'text-on-surface-variant' },
  testing: { bg: 'bg-[#FFF8C5]', text: 'text-[#9A6700]' },
  passed: { bg: 'bg-[#DAFBE1]', text: 'text-[#1A7F37]' },
  failed: { bg: 'bg-error-container', text: 'text-on-error-container' },
  published: { bg: 'bg-primary-container', text: 'text-on-primary-container' },
  archived: { bg: 'bg-surface-container', text: 'text-on-surface-variant' },
};

const emptyPrompt = { name: '', prompt_content: '', business_category_id: '' };

export default function PromptManager() {
  const { user } = useAuth();
  const [prompts, setPrompts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [variables, setVariables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState(null);
  const [activeTab, setActiveTab] = useState('prompts');

  // Form states
  const [showForm, setShowForm] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [form, setForm] = useState({ ...emptyPrompt });
  const [isSaving, setIsSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  // Sandbox states
  const [showSandbox, setShowSandbox] = useState(false);
  const [sandboxPrompt, setSandboxPrompt] = useState(null);
  const [sandboxValues, setSandboxValues] = useState({});
  const [sandboxResult, setSandboxResult] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  // Version history
  const [showVersions, setShowVersions] = useState(false);
  const [versionPrompt, setVersionPrompt] = useState(null);
  const [versions, setVersions] = useState([]);

  // Detail view
  const [expandedId, setExpandedId] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [p, c, v] = await Promise.all([
        api.getBusinessPrompts(),
        api.getBusinessCategories(),
        api.getPromptVariables(),
      ]);
      setPrompts(Array.isArray(p) ? p : []);
      setCategories(Array.isArray(c) ? c : []);
      setVariables(Array.isArray(v) ? v : []);
    } catch (e) {
      console.error('Failed to load data:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (!feedback) return;
    const t = setTimeout(() => setFeedback(null), 5000);
    return () => clearTimeout(t);
  }, [feedback]);

  const openCreate = () => {
    setEditingPrompt(null);
    setForm({ ...emptyPrompt });
    setShowForm(true);
  };

  const openEdit = (prompt) => {
    setEditingPrompt(prompt);
    setForm({ name: prompt.name || '', prompt_content: prompt.prompt_content || '', business_category_id: prompt.business_category_id || '' });
    setShowForm(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!form.name || !form.prompt_content) return;
    setIsSaving(true);
    try {
      if (editingPrompt) {
        await api.updateBusinessPrompt(editingPrompt.id, form);
        setFeedback({ type: 'success', text: 'Prompt updated' });
      } else {
        await api.createBusinessPrompt(form);
        setFeedback({ type: 'success', text: 'Prompt created' });
      }
      setShowForm(false);
      fetchData();
    } catch (e) {
      setFeedback({ type: 'error', text: e?.response?.data?.detail || 'Failed to save' });
    } finally {
      setIsSaving(false);
    }
  };

  const handlePublish = async (prompt) => {
    try {
      await api.publishBusinessPrompt(prompt.id);
      setFeedback({ type: 'success', text: `"${prompt.name}" published (v${(prompt.current_version || 0) + 1})` });
      fetchData();
    } catch (e) {
      setFeedback({ type: 'error', text: e?.response?.data?.detail || 'Failed to publish' });
    }
  };

  const handleArchive = async (prompt) => {
    try {
      await api.archiveBusinessPrompt(prompt.id);
      setFeedback({ type: 'success', text: `"${prompt.name}" archived` });
      fetchData();
    } catch (e) {
      setFeedback({ type: 'error', text: e?.response?.data?.detail || 'Failed to archive' });
    }
  };

  const handleClone = async (prompt) => {
    try {
      await api.cloneBusinessPrompt(prompt.id, { new_name: `${prompt.name} (Copy)` });
      setFeedback({ type: 'success', text: `Cloned "${prompt.name}"` });
      fetchData();
    } catch (e) {
      setFeedback({ type: 'error', text: e?.response?.data?.detail || 'Failed to clone' });
    }
  };

  const handleRollback = async (prompt, versionNumber) => {
    try {
      await api.rollbackBusinessPrompt(prompt.id, { target_version: versionNumber });
      setFeedback({ type: 'success', text: `Rolled back to v${versionNumber}` });
      setShowVersions(false);
      fetchData();
    } catch (e) {
      setFeedback({ type: 'error', text: e?.response?.data?.detail || 'Failed to rollback' });
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteBusinessPrompt(deleteTarget.id);
      setFeedback({ type: 'success', text: 'Prompt deleted' });
      setDeleteTarget(null);
      fetchData();
    } catch (e) {
      setFeedback({ type: 'error', text: e?.response?.data?.detail || 'Failed to delete' });
    }
  };

  const openSandbox = (prompt) => {
    setSandboxPrompt(prompt);
    setSandboxValues({});
    setSandboxResult(null);
    setShowSandbox(true);
  };

  const runSandbox = async () => {
    if (!sandboxPrompt) return;
    setIsRunning(true);
    try {
      const result = await api.runSandboxTest({
        template_id: sandboxPrompt.id,
        variable_values: sandboxValues,
      });
      setSandboxResult(result);
    } catch (e) {
      setSandboxResult({ error: e?.response?.data?.detail || 'Sandbox test failed' });
    } finally {
      setIsRunning(false);
    }
  };

  const openVersions = async (prompt) => {
    setVersionPrompt(prompt);
    setShowVersions(true);
    try {
      const v = await api.getPromptVersions(prompt.id);
      setVersions(Array.isArray(v) ? v : []);
    } catch (e) {
      console.error('Failed to load versions:', e);
      setVersions([]);
    }
  };

  const detectVars = async (content) => {
    try {
      const result = await api.detectVariables(content);
      return result?.variables || [];
    } catch { return []; }
  };

  const inputCls = "w-full px-3 py-2 bg-surface-container border border-outline-variant rounded-md text-on-surface text-sm focus:outline-none focus:ring-2 focus:ring-primary/40";
  const labelCls = "block text-xs font-medium text-on-surface-variant mb-1";
  const getCategoryName = (id) => categories.find(c => c.id === id)?.name || '—';

  const statusBadge = (status) => {
    const s = STATUS_COLORS[status] || STATUS_COLORS.draft;
    return <span className={`text-[10px] px-2 py-0.5 font-bold rounded-full uppercase tracking-widest ${s.bg} ${s.text}`}>{status || 'draft'}</span>;
  };

  const tabs = [
    { id: 'prompts', label: 'Prompts', icon: FileText },
    { id: 'variables', label: 'Variables', icon: Pencil },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-on-surface">Prompt Manager</h1>
          <p className="text-sm text-on-surface-variant mt-1">Manage business email prompts, variables, and sandbox testing</p>
        </div>
        <button onClick={openCreate} className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors font-medium text-sm">
          <Plus size={16} /> New Prompt
        </button>
      </div>

      {feedback && (
        <div className={`px-4 py-3 rounded-lg text-sm font-medium ${
          feedback.type === 'success' ? 'bg-[#DAFBE1] text-[#1A7F37]' : 'bg-error-container text-on-error-container'
        }`}>
          {feedback.text}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-outline-variant">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${activeTab === t.id ? 'border-primary text-primary' : 'border-transparent text-on-surface-variant hover:text-on-surface'}`}>
            <t.icon size={16} /> {t.label}
          </button>
        ))}
      </div>

      {/* Prompts Tab */}
      {activeTab === 'prompts' && (
        <>
          {loading ? (
            <div className="space-y-3">
              {[1,2,3].map(i => <div key={i} className="h-20 bg-surface-container rounded-lg animate-pulse" />)}
            </div>
          ) : prompts.length === 0 ? (
            <div className="text-center py-16 bg-surface-container rounded-lg border border-outline-variant">
              <FileText size={48} className="mx-auto text-on-surface-variant/40 mb-4" />
              <p className="text-on-surface-variant font-medium">No prompts yet</p>
              <p className="text-sm text-on-surface-variant/60 mt-1">Create your first business prompt to get started</p>
            </div>
          ) : (
            <div className="space-y-2">
              {prompts.map((prompt) => (
                <div key={prompt.id} className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden">
                  <div className="flex items-center px-4 py-3 gap-3 cursor-pointer hover:bg-surface-container-high transition-colors" onClick={() => setExpandedId(expandedId === prompt.id ? null : prompt.id)}>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-on-surface text-sm">{prompt.name}</span>
                        {statusBadge(prompt.testing_status || prompt.status)}
                        {prompt.published_version > 0 && <span className="text-[10px] text-on-surface-variant/50">v{prompt.published_version}</span>}
                      </div>
                      <p className="text-xs text-on-surface-variant/60 mt-0.5">{getCategoryName(prompt.business_category_id)}</p>
                    </div>
                    <div className="flex items-center gap-1 text-on-surface-variant/40">
                      {expandedId === prompt.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </div>
                  </div>

                  {expandedId === prompt.id && (
                    <div className="px-4 pb-4 border-t border-outline-variant/50 pt-3">
                      <div className="bg-surface rounded p-3 mb-3 text-xs text-on-surface-variant font-mono whitespace-pre-wrap max-h-32 overflow-y-auto">{prompt.prompt_content}</div>
                      <div className="flex flex-wrap gap-2">
                        <button onClick={(e) => { e.stopPropagation(); openEdit(prompt); }} className="flex items-center gap-1.5 px-3 py-1.5 bg-surface text-on-surface rounded border border-outline-variant hover:bg-surface-container-high transition-colors text-xs font-medium">
                          <Pencil size={13} /> Edit
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); openSandbox(prompt); }} className="flex items-center gap-1.5 px-3 py-1.5 bg-surface text-on-surface rounded border border-outline-variant hover:bg-surface-container-high transition-colors text-xs font-medium">
                          <Play size={13} /> Sandbox Test
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); handlePublish(prompt); }} className="flex items-center gap-1.5 px-3 py-1.5 bg-[#DAFBE1] text-[#1A7F37] rounded border border-[#1A7F37]/20 hover:bg-[#1A7F37]/10 transition-colors text-xs font-medium">
                          <CheckCircle size={13} /> Publish
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); handleClone(prompt); }} className="flex items-center gap-1.5 px-3 py-1.5 bg-surface text-on-surface rounded border border-outline-variant hover:bg-surface-container-high transition-colors text-xs font-medium">
                          <Copy size={13} /> Clone
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); openVersions(prompt); }} className="flex items-center gap-1.5 px-3 py-1.5 bg-surface text-on-surface rounded border border-outline-variant hover:bg-surface-container-high transition-colors text-xs font-medium">
                          <History size={13} /> Versions
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); handleArchive(prompt); }} className="flex items-center gap-1.5 px-3 py-1.5 bg-surface text-on-surface-variant rounded border border-outline-variant hover:bg-surface-container-high transition-colors text-xs font-medium">
                          <Archive size={13} /> Archive
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); setDeleteTarget(prompt); }} className="flex items-center gap-1.5 px-3 py-1.5 bg-surface text-on-error rounded border border-outline-variant hover:bg-error-container/30 transition-colors text-xs font-medium">
                          <Trash2 size={13} /> Delete
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Variables Tab */}
      {activeTab === 'variables' && (
        <div className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden">
          {variables.length === 0 ? (
            <div className="text-center py-16">
              <Pencil size={48} className="mx-auto text-on-surface-variant/40 mb-4" />
              <p className="text-on-surface-variant font-medium">No variables defined</p>
              <p className="text-sm text-on-surface-variant/60 mt-1">Variables are used in prompts as {'{{variable_name}}'}</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-outline-variant bg-surface">
                  <th className="text-left px-4 py-2 text-xs font-bold text-on-surface-variant uppercase">Name</th>
                  <th className="text-left px-4 py-2 text-xs font-bold text-on-surface-variant uppercase">Display Name</th>
                  <th className="text-left px-4 py-2 text-xs font-bold text-on-surface-variant uppercase">Type</th>
                  <th className="text-left px-4 py-2 text-xs font-bold text-on-surface-variant uppercase">Scope</th>
                  <th className="text-left px-4 py-2 text-xs font-bold text-on-surface-variant uppercase">Adapter</th>
                  <th className="text-left px-4 py-2 text-xs font-bold text-on-surface-variant uppercase">Required</th>
                </tr>
              </thead>
              <tbody>
                {variables.map((v) => (
                  <tr key={v.id} className="border-b border-outline-variant/50 hover:bg-surface-container-high">
                    <td className="px-4 py-2 font-mono text-xs text-primary">{v.name}</td>
                    <td className="px-4 py-2 text-on-surface">{v.display_name}</td>
                    <td className="px-4 py-2"><span className="text-[10px] px-2 py-0.5 bg-secondary-container text-on-secondary-container rounded-full font-bold">{v.data_type}</span></td>
                    <td className="px-4 py-2 text-on-surface-variant">{v.scope}</td>
                    <td className="px-4 py-2 text-on-surface-variant text-xs">{v.source_adapter}</td>
                    <td className="px-4 py-2">{v.is_required ? <CheckCircle size={14} className="text-[#1A7F37]" /> : <span className="text-on-surface-variant/30">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Create/Edit Prompt Modal */}
      <Modal isOpen={showForm} onClose={() => setShowForm(false)} title={editingPrompt ? 'Edit Prompt' : 'New Business Prompt'}>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className={labelCls}>Name *</label>
            <input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Refund Acknowledgement" required />
          </div>
          <div>
            <label className={labelCls}>Business Category</label>
            <select className={inputCls} value={form.business_category_id} onChange={(e) => setForm({ ...form, business_category_id: e.target.value })}>
              <option value="">Select category...</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name} ({c.code})</option>)}
            </select>
          </div>
          <div>
            <label className={labelCls}>Prompt Content * (use {'{{variable_name}}'} for variables)</label>
            <textarea className={`${inputCls} min-h-[160px] font-mono text-xs`} value={form.prompt_content} onChange={(e) => setForm({ ...form, prompt_content: e.target.value })} placeholder={"Dear {{customer_name}},\n\nThank you for contacting us regarding your request...\n\nBest regards,\n{{company_name}}"} required />
            {form.prompt_content && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {variables.map(v => (
                  <button key={v.name} type="button" onClick={() => setForm({ ...form, prompt_content: form.prompt_content + ` {{${v.name}}}` })} className="text-[10px] px-2 py-0.5 bg-secondary-container text-on-secondary-container rounded-full hover:bg-secondary-container/80 transition-colors">
                    +{v.name}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm font-medium text-on-surface-variant border border-outline-variant rounded-md hover:bg-surface-container-highest transition-colors">Cancel</button>
            <button type="submit" disabled={isSaving} className="px-4 py-2 text-sm font-medium bg-primary text-on-primary rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50">
              {isSaving ? 'Saving...' : editingPrompt ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Sandbox Modal */}
      <Modal isOpen={showSandbox} onClose={() => setShowSandbox(false)} title={`Sandbox Test — ${sandboxPrompt?.name || ''}`}>
        <div className="space-y-4">
          <div className="bg-surface rounded p-3 text-xs font-mono text-on-surface-variant whitespace-pre-wrap max-h-40 overflow-y-auto border border-outline-variant">{sandboxPrompt?.prompt_content}</div>
          <div className="grid grid-cols-1 gap-3">
            {variables.map(v => (
              <div key={v.name}>
                <label className={labelCls}>{v.display_name || v.name} <span className="text-on-surface-variant/40">({v.data_type})</span></label>
                <input className={inputCls} value={sandboxValues[v.name] || ''} onChange={(e) => setSandboxValues({ ...sandboxValues, [v.name]: e.target.value })} placeholder={v.sample_value || `Enter ${v.name}...`} />
              </div>
            ))}
            {variables.length === 0 && (
              <p className="text-xs text-on-surface-variant/60">No variables registered. Add variables in the Variables tab first.</p>
            )}
          </div>
          <button onClick={runSandbox} disabled={isRunning} className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium disabled:opacity-50">
            <Play size={16} /> {isRunning ? 'Running...' : 'Run Sandbox Test'}
          </button>
          {sandboxResult && (
            <div className={`p-3 rounded-lg border text-xs ${sandboxResult.error ? 'bg-error-container/30 border-error/30 text-on-surface' : 'bg-[#DAFBE1]/30 border-[#1A7F37]/20'}`}>
              {sandboxResult.error ? (
                <div><AlertTriangle className="inline mr-1 text-error" size={14} /> {sandboxResult.error}</div>
              ) : (
                <div className="space-y-2">
                  <div className="font-bold text-sm text-on-surface">Rendered Prompt:</div>
                  <div className="bg-surface rounded p-2 font-mono whitespace-pre-wrap">{sandboxResult.rendered_prompt}</div>
                  <div className="grid grid-cols-2 gap-2 mt-2 text-[10px]">
                    <div><strong>Length:</strong> {sandboxResult.prompt_length_chars} chars</div>
                    <div><strong>Tokens:</strong> ~{sandboxResult.estimated_tokens}</div>
                  </div>
                  {sandboxResult.warnings?.length > 0 && (
                    <div className="mt-2">{sandboxResult.warnings.map((w, i) => <div key={i} className="text-[#9A6700]"><AlertTriangle className="inline mr-1" size={12} /> {w}</div>)}</div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </Modal>

      {/* Version History Modal */}
      <Modal isOpen={showVersions} onClose={() => setShowVersions(false)} title={`Version History — ${versionPrompt?.name || ''}`}>
        <div className="space-y-2">
          {versions.length === 0 ? (
            <p className="text-sm text-on-surface-variant text-center py-4">No versions yet. Publish to create version 1.</p>
          ) : (
            versions.map((v) => (
              <div key={v.id} className={`p-3 rounded-lg border ${v.version_number === versionPrompt?.published_version ? 'border-primary/50 bg-primary-container/10' : 'border-outline-variant bg-surface'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-bold text-sm text-on-surface">v{v.version_number}</span>
                    {v.version_number === versionPrompt?.published_version && <span className="ml-2 text-[10px] bg-primary-container text-on-primary-container px-1.5 py-0.5 rounded-full font-bold">PUBLISHED</span>}
                    {v.status && <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded-full font-bold bg-surface-container-high text-on-surface-variant">{v.status}</span>}
                  </div>
                  {v.version_number !== versionPrompt?.published_version && (
                    <button onClick={() => handleRollback(versionPrompt, v.version_number)} className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-on-surface border border-outline-variant rounded hover:bg-surface-container-high transition-colors">
                      <RotateCcw size={12} /> Rollback
                    </button>
                  )}
                </div>
                <p className="text-[10px] text-on-surface-variant/60 mt-1">Created: {v.created_at ? new Date(v.created_at).toLocaleString() : '—'}</p>
                {v.prompt_content && <p className="text-[10px] text-on-surface-variant/40 mt-1 font-mono truncate">{v.prompt_content.substring(0, 100)}...</p>}
              </div>
            ))
          )}
        </div>
      </Modal>

      <ConfirmDialog isOpen={!!deleteTarget} onClose={() => setDeleteTarget(null)} onConfirm={handleDelete} title="Delete Prompt" message={`Are you sure you want to delete "${deleteTarget?.name}"? This cannot be undone.`} confirmText="Delete" isDestructive />
    </div>
  );
}
