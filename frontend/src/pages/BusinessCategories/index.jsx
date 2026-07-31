import { useState, useEffect, useCallback } from 'react';
import { Plus, Pencil, Trash2, Star, StarOff, BarChart3, Bot, ChevronDown, ChevronRight, Layers } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';
import { Modal } from '../../components/Modal';
import { ConfirmDialog } from '../../components/ConfirmDialog';

const COLORS = ['#EF4444','#F97316','#EAB308','#22C55E','#06B6D4','#3B82F6','#8B5CF6','#EC4899','#6B7280'];

const emptyCategory = {
  name: '', code: '', description: '', color: '#3B82F6',
  priority: 0, display_order: 0, icon: '',
  ai_model: '', ai_temperature: 0.7, ai_max_tokens: 4096, ai_timeout: 30, ai_retry_count: 2,
};

export default function BusinessCategories() {
  const { user } = useAuth();
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [form, setForm] = useState({ ...emptyCategory });
  const [isSaving, setIsSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  const fetchCategories = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getBusinessCategories();
      setCategories(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Failed to load categories:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCategories(); }, [fetchCategories]);

  useEffect(() => {
    if (!feedback) return;
    const t = setTimeout(() => setFeedback(null), 5000);
    return () => clearTimeout(t);
  }, [feedback]);

  const openCreate = () => {
    setEditingCategory(null);
    setForm({ ...emptyCategory });
    setShowForm(true);
  };

  const openEdit = (cat) => {
    setEditingCategory(cat);
    setForm({
      name: cat.name || '', code: cat.code || '', description: cat.description || '',
      color: cat.color || '#3B82F6', priority: cat.priority || 0, display_order: cat.display_order || 0,
      icon: cat.icon || '',
      ai_model: cat.ai_model || '', ai_temperature: cat.ai_temperature ?? 0.7,
      ai_max_tokens: cat.ai_max_tokens || 4096, ai_timeout: cat.ai_timeout || 30,
      ai_retry_count: cat.ai_retry_count || 2,
    });
    setShowForm(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!form.name || !form.code) return;
    setIsSaving(true);
    try {
      if (editingCategory) {
        await api.updateBusinessCategory(editingCategory.id, form);
        setFeedback({ type: 'success', text: 'Category updated successfully' });
      } else {
        await api.createBusinessCategory(form);
        setFeedback({ type: 'success', text: 'Category created successfully' });
      }
      setShowForm(false);
      fetchCategories();
    } catch (e) {
      setFeedback({ type: 'error', text: e?.response?.data?.detail || 'Failed to save category' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteBusinessCategory(deleteTarget.id);
      setFeedback({ type: 'success', text: 'Category deleted' });
      setDeleteTarget(null);
      fetchCategories();
    } catch (e) {
      setFeedback({ type: 'error', text: e?.response?.data?.detail || 'Failed to delete' });
    }
  };

  const handleSetDefault = async (cat) => {
    try {
      await api.setDefaultBusinessCategory(cat.id);
      setFeedback({ type: 'success', text: `"${cat.name}" set as default` });
      fetchCategories();
    } catch (e) {
      setFeedback({ type: 'error', text: e?.response?.data?.detail || 'Failed to set default' });
    }
  };

  const toggleExpand = (id) => setExpandedId(expandedId === id ? null : id);

  const inputCls = "w-full px-3 py-2 bg-surface-container border border-outline-variant rounded-md text-on-surface text-sm focus:outline-none focus:ring-2 focus:ring-primary/40";
  const labelCls = "block text-xs font-medium text-on-surface-variant mb-1";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-on-surface">Business Categories</h1>
          <p className="text-sm text-on-surface-variant mt-1">Define business email categories, AI overrides, and workflow mappings</p>
        </div>
        <button onClick={openCreate} className="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors font-medium text-sm">
          <Plus size={16} /> New Category
        </button>
      </div>

      {feedback && (
        <div className={`px-4 py-3 rounded-lg text-sm font-medium ${
          feedback.type === 'success' ? 'bg-[#DAFBE1] text-[#1A7F37]' : 'bg-error-container text-on-error-container'
        }`}>
          {feedback.text}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {[1,2,3].map(i => <div key={i} className="h-20 bg-surface-container rounded-lg animate-pulse" />)}
        </div>
      ) : categories.length === 0 ? (
        <div className="text-center py-16 bg-surface-container rounded-lg border border-outline-variant">
          <Layers size={48} className="mx-auto text-on-surface-variant/40 mb-4" />
          <p className="text-on-surface-variant font-medium">No categories yet</p>
          <p className="text-sm text-on-surface-variant/60 mt-1">Create your first business category to organize email workflows</p>
          <button onClick={openCreate} className="mt-4 px-4 py-2 bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium">
            <Plus size={16} className="inline mr-1" /> Create Category
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {categories.map((cat) => (
            <div key={cat.id} className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden">
              <div className="flex items-center px-4 py-3 gap-3 cursor-pointer hover:bg-surface-container-high transition-colors" onClick={() => toggleExpand(cat.id)}>
                <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: cat.color || '#6B7280' }} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-on-surface text-sm">{cat.name}</span>
                    <span className="text-xs text-on-surface-variant/60 font-mono">({cat.code})</span>
                    {cat.is_default && <span className="text-[10px] bg-primary-container text-on-primary-container px-1.5 py-0.5 rounded-full font-bold">DEFAULT</span>}
                  </div>
                  <p className="text-xs text-on-surface-variant/60 mt-0.5 truncate">{cat.description || 'No description'}</p>
                </div>
                <div className="flex items-center gap-1 text-on-surface-variant/40">
                  {expandedId === cat.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </div>
              </div>

              {expandedId === cat.id && (
                <div className="px-4 pb-4 border-t border-outline-variant/50 pt-3">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div>
                      <h4 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2">Metrics</h4>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="bg-surface p-2 rounded">
                          <span className="text-on-surface-variant">Emails Processed</span>
                          <p className="text-on-surface font-bold text-lg">{cat.emails_processed || 0}</p>
                        </div>
                        <div className="bg-surface p-2 rounded">
                          <span className="text-on-surface-variant">Approval Rate</span>
                          <p className="text-on-surface font-bold text-lg">{cat.approval_rate ? `${cat.approval_rate}%` : '—'}</p>
                        </div>
                        <div className="bg-surface p-2 rounded">
                          <span className="text-on-surface-variant">Drafts Generated</span>
                          <p className="text-on-surface font-bold text-lg">{cat.drafts_generated || 0}</p>
                        </div>
                        <div className="bg-surface p-2 rounded">
                          <span className="text-on-surface-variant">Avg Generation</span>
                          <p className="text-on-surface font-bold text-lg">{cat.avg_generation_time_ms ? `${cat.avg_generation_time_ms}ms` : '—'}</p>
                        </div>
                      </div>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2">AI Config Override</h4>
                      <div className="bg-surface p-2 rounded text-xs space-y-1">
                        <div className="flex justify-between"><span className="text-on-surface-variant">Model</span><span className="text-on-surface">{cat.ai_model || 'Inherit global'}</span></div>
                        <div className="flex justify-between"><span className="text-on-surface-variant">Temperature</span><span className="text-on-surface">{cat.ai_temperature ?? 'Inherit'}</span></div>
                        <div className="flex justify-between"><span className="text-on-surface-variant">Max Tokens</span><span className="text-on-surface">{cat.ai_max_tokens || 'Inherit'}</span></div>
                        <div className="flex justify-between"><span className="text-on-surface-variant">Timeout</span><span className="text-on-surface">{cat.ai_timeout ? `${cat.ai_timeout}s` : 'Inherit'}</span></div>
                        <div className="flex justify-between"><span className="text-on-surface-variant">Retry Count</span><span className="text-on-surface">{cat.ai_retry_count ?? 'Inherit'}</span></div>
                      </div>
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2">Actions</h4>
                      <div className="space-y-2">
                        <button onClick={(e) => { e.stopPropagation(); openEdit(cat); }} className="w-full flex items-center gap-2 px-3 py-2 bg-surface text-on-surface rounded border border-outline-variant hover:bg-surface-container-high transition-colors text-xs font-medium">
                          <Pencil size={14} /> Edit Category
                        </button>
                        {!cat.is_default && (
                          <button onClick={(e) => { e.stopPropagation(); handleSetDefault(cat); }} className="w-full flex items-center gap-2 px-3 py-2 bg-surface text-on-surface rounded border border-outline-variant hover:bg-surface-container-high transition-colors text-xs font-medium">
                            <Star size={14} /> Set as Default
                          </button>
                        )}
                        <button onClick={(e) => { e.stopPropagation(); setDeleteTarget(cat); }} className="w-full flex items-center gap-2 px-3 py-2 bg-surface text-on-error rounded border border-outline-variant hover:bg-error-container/30 transition-colors text-xs font-medium">
                          <Trash2 size={14} /> Delete
                        </button>
                      </div>
                    </div>
                  </div>
                  <div className="text-[10px] text-on-surface-variant/40 flex gap-4">
                    <span>Priority: {cat.priority}</span>
                    <span>Display Order: {cat.display_order}</span>
                    <span>Status: {cat.status}</span>
                    <span>ID: {cat.id?.substring(0, 8)}</span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      <Modal isOpen={showForm} onClose={() => setShowForm(false)} title={editingCategory ? 'Edit Category' : 'New Business Category'}>
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Name *</label>
              <input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Refund Requests" required />
            </div>
            <div>
              <label className={labelCls}>Code *</label>
              <input className={inputCls} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, '') })} placeholder="e.g. REFUND" required disabled={!!editingCategory} />
              {editingCategory && <p className="text-[10px] text-on-surface-variant/50 mt-1">Code cannot be changed after creation</p>}
            </div>
          </div>
          <div>
            <label className={labelCls}>Description</label>
            <input className={inputCls} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Brief description of this category" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={labelCls}>Color</label>
              <div className="flex gap-1.5 flex-wrap">
                {COLORS.map(c => (
                  <button key={c} type="button" onClick={() => setForm({ ...form, color: c })} className={`w-6 h-6 rounded-full border-2 transition-all ${form.color === c ? 'border-on-surface scale-110' : 'border-transparent'}`} style={{ backgroundColor: c }} />
                ))}
              </div>
            </div>
            <div>
              <label className={labelCls}>Priority (Runtime)</label>
              <input type="number" className={inputCls} value={form.priority} onChange={(e) => setForm({ ...form, priority: parseInt(e.target.value) || 0 })} />
            </div>
            <div>
              <label className={labelCls}>Display Order (UI)</label>
              <input type="number" className={inputCls} value={form.display_order} onChange={(e) => setForm({ ...form, display_order: parseInt(e.target.value) || 0 })} />
            </div>
          </div>

          <div className="border-t border-outline-variant pt-4">
            <h4 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-3 flex items-center gap-1.5"><Bot size={14} /> AI Config Override (leave blank to inherit global)</h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Model</label>
                <input className={inputCls} value={form.ai_model} onChange={(e) => setForm({ ...form, ai_model: e.target.value })} placeholder="e.g. gpt-4.1" />
              </div>
              <div>
                <label className={labelCls}>Temperature</label>
                <input type="number" step="0.1" min="0" max="2" className={inputCls} value={form.ai_temperature} onChange={(e) => setForm({ ...form, ai_temperature: parseFloat(e.target.value) || 0 })} />
              </div>
              <div>
                <label className={labelCls}>Max Tokens</label>
                <input type="number" className={inputCls} value={form.ai_max_tokens} onChange={(e) => setForm({ ...form, ai_max_tokens: parseInt(e.target.value) || 4096 })} />
              </div>
              <div>
                <label className={labelCls}>Timeout (s)</label>
                <input type="number" className={inputCls} value={form.ai_timeout} onChange={(e) => setForm({ ...form, ai_timeout: parseInt(e.target.value) || 30 })} />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm font-medium text-on-surface-variant border border-outline-variant rounded-md hover:bg-surface-container-highest transition-colors">Cancel</button>
            <button type="submit" disabled={isSaving} className="px-4 py-2 text-sm font-medium bg-primary text-on-primary rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50">
              {isSaving ? 'Saving...' : editingCategory ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog isOpen={!!deleteTarget} onClose={() => setDeleteTarget(null)} onConfirm={handleDelete} title="Delete Category" message={`Are you sure you want to delete "${deleteTarget?.name}"? This action cannot be undone.`} confirmText="Delete" isDestructive />
    </div>
  );
}
