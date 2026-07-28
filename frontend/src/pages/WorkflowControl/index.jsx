import { useState, useEffect, useCallback } from 'react';
import { useLiveData } from '../../hooks/useLiveData';
import { useAuth } from '../../context/AuthContext';
import { useMailbox } from '../../context/MailboxContext';
import { api } from '../../api/client';
import { DataTable } from '../../components/DataTable';
import { SearchBar } from '../../components/SearchBar';
import { StatusBadge } from '../../components/StatusBadge';
import { Modal } from '../../components/Modal';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { EmptyState } from '../../components/EmptyState';
import { Plus, Play, Square, Trash2, Edit2, Check, X, PlusCircle, MinusCircle, GripVertical } from 'lucide-react';

import { AlertTriangle, Mail } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const WorkflowControl = () => {
  const navigate = useNavigate();
  const { canEdit } = useAuth();
  const { isConnected, activeMailbox, loading: mailboxLoading } = useMailbox();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState(null);
  const [deletingWorkflow, setDeletingWorkflow] = useState(null);
  const [viewingWorkflow, setViewingWorkflow] = useState(null);
  const [workflowExecutions, setWorkflowExecutions] = useState([]);
  
  const defaultFormData = { 
    name: '', 
    description: '',
    is_active: true,
    trigger_type: 'automatic',
    trigger_conditions_json: { operator: 'AND', rules: [{ field: 'subject', operator: 'contains', value: '' }] },
    actions_json: { actions: [{ type: 'add_label', value: '' }] }
  };
  const [formData, setFormData] = useState(defaultFormData);
  
  const [formError, setFormError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchWorkflows = useCallback(() => api.getWorkflows({ status: 'all', search, page, pageSize }), [search, page, pageSize]);
  const { data, loading, error, addItem, updateItem, removeItem } = useLiveData(fetchWorkflows, null, [fetchWorkflows, isConnected], isConnected);
  
  const { data: categoriesData } = useLiveData(api.getCategories, null, [], isConnected);
  
  const [promptTemplates, setPromptTemplates] = useState([]);
  
  useEffect(() => {
    const loadPromptTemplates = async () => {
      try {
        const templates = await api.getPromptTemplates();
        setPromptTemplates(Array.isArray(templates) ? templates : []);
      } catch (e) {
        console.error('Failed to load prompt templates:', e);
      }
    };
    loadPromptTemplates();
  }, []);

  const handleCreateEdit = async () => {
    setFormError(null);
    if (!formData.name?.trim()) {
      setFormError('Workflow name is required.');
      return;
    }
    
    setIsSubmitting(true);
    try {
      const payload = {
        ...formData,
        name: formData.name.replace(/</g, "&lt;").replace(/>/g, "&gt;"),
        description: formData.description?.replace(/</g, "&lt;").replace(/>/g, "&gt;") || "No description",
        mailbox_account_id: activeMailbox?.id
      };

      if (!payload.mailbox_account_id) {
        setFormError('No mailbox connected. Please connect Gmail first.');
        setIsSubmitting(false);
        return;
      }

      if (editingWorkflow) {
        const updated = await api.updateWorkflow(editingWorkflow.id, payload);
        updateItem('id', editingWorkflow.id, updated);
      } else {
        const created = await api.createWorkflow(payload);
        addItem(created);
      }
      setIsModalOpen(false);
    } catch (err) {
      setFormError('Failed to save workflow. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    try {
      await api.deleteWorkflow(deletingWorkflow.id);
      removeItem('id', deletingWorkflow.id);
      setIsDeleteDialogOpen(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAction = async (id, action) => {
    try {
      const updated = await api.toggleWorkflowState(id, action);
      updateItem('id', id, updated);
    } catch (err) {
      console.error(err);
    }
  };

  const columns = [
    { header: 'Workflow Name', accessor: 'name', cellClassName: 'font-medium text-on-surface' },
    { header: 'Status', render: (row) => <StatusBadge status={row.status || (row.is_active ? 'active' : 'disabled')} /> },
    { 
      header: 'Actions Summary', 
      render: (row) => {
        const actionTypes = row.actions_json?.actions?.map(a => {
          if (a.type === 'generate_ai_reply') return '✨ AI Reply';
          if (a.type === 'add_label') return `Label (${a.value || 'Tag'})`;
          if (a.type === 'send_email') return 'Send Email';
          if (a.type === 'forward') return 'Forward';
          if (a.type === 'create_ticket') return 'Create Ticket';
          return a.type;
        }) || ['None'];
        return (
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded border border-gray-200 dark:border-gray-700">
            {actionTypes.join(' + ')}
          </span>
        );
      }
    },
    { 
      header: 'Approval Status', 
      render: (row) => {
        const aiAction = row.actions_json?.actions?.find(a => a.type === 'generate_ai_reply');
        if (!aiAction) return <span className="text-gray-400 text-xs">N/A</span>;
        return aiAction.require_approval !== false ? (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">Required</span>
        ) : (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-600">Auto-Executed</span>
        );
      }
    },
    { header: 'Trigger', render: (row) => <span className="text-body-md uppercase">{row.trigger_type || 'automatic'}</span> },
    { header: 'Last Run', render: (row) => row.last_run ? new Date(row.last_run).toLocaleString() : 'Never' },
    { header: 'Actions', render: (row) => (
      <div className="flex gap-2">
        <button onClick={async () => {
          setViewingWorkflow(row);
          setIsDetailsModalOpen(true);
          try {
            const execs = await api.getWorkflowExecutions(row.id);
            setWorkflowExecutions(execs);
          } catch (e) {
            console.error("Failed to load executions", e);
          }
        }} className="text-on-surface-variant hover:text-primary transition-colors text-body-md" title="View Details">
          View
        </button>
        {row.status === 'active' || row.is_active ? (
           <button onClick={() => handleAction(row.id, 'disable')} className="text-on-surface-variant hover:text-error transition-colors" title="Disable">
             <X size={16} />
           </button>
        ) : (
          <button onClick={() => handleAction(row.id, 'enable')} className="text-on-surface-variant hover:text-[#1A7F37] transition-colors" title="Enable">
            <Check size={16} />
          </button>
        )}
        {canEdit && (
          <>
            <button onClick={() => {
              setEditingWorkflow(row);
              setFormData({
                name: row.name,
                description: row.description || '',
                is_active: row.is_active !== false,
                trigger_type: row.trigger_type || 'automatic',
                trigger_conditions_json: row.trigger_conditions_json || defaultFormData.trigger_conditions_json,
                actions_json: row.actions_json || defaultFormData.actions_json
              });
              setIsModalOpen(true);
            }} className="text-on-surface-variant hover:text-primary transition-colors" title="Edit">
              <Edit2 size={16} />
            </button>
            <button onClick={() => {
              setDeletingWorkflow(row);
              setIsDeleteDialogOpen(true);
            }} className="text-on-surface-variant hover:text-error transition-colors" title="Delete">
              <Trash2 size={16} />
            </button>
          </>
        )}
      </div>
    ) }
  ];

  // Condition Builder Handlers
  const addCondition = () => {
    setFormData(prev => ({
      ...prev,
      trigger_conditions_json: {
        ...prev.trigger_conditions_json,
        rules: [...(prev.trigger_conditions_json.rules || []), { field: 'subject', operator: 'contains', value: '' }]
      }
    }));
  };

  const updateCondition = (index, key, value) => {
    setFormData(prev => {
      const newRules = [...prev.trigger_conditions_json.rules];
      newRules[index] = { ...newRules[index], [key]: value };
      return { ...prev, trigger_conditions_json: { ...prev.trigger_conditions_json, rules: newRules } };
    });
  };

  const removeCondition = (index) => {
    setFormData(prev => {
      const newRules = [...prev.trigger_conditions_json.rules];
      newRules.splice(index, 1);
      return { ...prev, trigger_conditions_json: { ...prev.trigger_conditions_json, rules: newRules } };
    });
  };

  // Action Builder Handlers
  const addAction = () => {
    setFormData(prev => ({
      ...prev,
      actions_json: {
        actions: [...(prev.actions_json?.actions || []), { type: 'add_label', value: 'Processed' }]
      }
    }));
  };

  const updateAction = (index, key, value) => {
    setFormData(prev => {
      const newActions = [...prev.actions_json.actions];
      newActions[index] = { ...newActions[index], [key]: value };
      return { ...prev, actions_json: { actions: newActions } };
    });
  };

  const removeAction = (index) => {
    setFormData(prev => {
      const newActions = [...prev.actions_json.actions];
      newActions.splice(index, 1);
      return { ...prev, actions_json: { actions: newActions } };
    });
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Disconnected Notice */}
      {!mailboxLoading && !isConnected && (
        <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-300">Gmail Not Connected</h3>
            <p className="text-xs text-amber-700 dark:text-amber-400 mt-1">
              Connect your Gmail account in Settings to enable workflow creation and execution. 
              Workflows will remain inactive until a mailbox is connected.
            </p>
            <button
              onClick={() => navigate('/settings')}
              className="mt-2 text-xs font-semibold text-amber-800 dark:text-amber-300 underline hover:no-underline"
            >
              Go to Settings →
            </button>
          </div>
        </div>
      )}

      <div className="flex justify-between items-center">
        <h2 className="font-headline-sm text-on-surface">Workflows</h2>
        <div className="flex gap-4">
          <SearchBar onSearch={(q) => { setSearch(q); setPage(1); }} placeholder="Search workflows..." />
          {canEdit && (
            <button 
              onClick={() => {
                if (!isConnected) return;
                setEditingWorkflow(null);
                setFormData(defaultFormData);
                setIsModalOpen(true);
              }}
              disabled={!isConnected}
              className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium text-body-md transition-colors ${
                isConnected 
                  ? 'bg-primary text-on-primary hover:bg-primary/90' 
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
              }`}
              title={isConnected ? 'Create Workflow' : 'Connect Gmail to create workflows'}
            >
              <Plus size={18} /> Create Workflow
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-surface-container p-4 rounded-xl text-body-md flex items-center gap-3 border border-outline-variant">
          <AlertTriangle className="w-4 h-4 text-on-surface-variant shrink-0" />
          <span className="text-on-surface-variant">{error}</span>
        </div>
      )}

      <div className="flat-card overflow-hidden">
        <DataTable
          columns={columns}
          data={data?.data || []}
          page={page}
          pageSize={pageSize}
          total={data?.total || 0}
          onPageChange={setPage}
          loading={loading}
          loadingSkeleton={<LoadingSkeleton type="table" rows={5} />}
          emptyState={
            !isConnected ? (
              <EmptyState 
                message="Connect Gmail to create and manage workflows." 
                actionText="Go to Settings"
                onAction={() => navigate('/settings')}
              />
            ) : (
              <EmptyState message="No workflows found." actionText="Create Workflow" onAction={() => setIsModalOpen(true)} />
            )
          }
        />
      </div>

      <Modal 
        isOpen={isModalOpen} 
        onClose={() => !isSubmitting && setIsModalOpen(false)} 
        title={editingWorkflow ? 'Edit Workflow' : 'Create Workflow'}
      >
        <div className="flex flex-col gap-8 py-2 max-h-[70vh] overflow-y-auto px-1">
          {formError && <div className="text-error text-body-md p-3 bg-error-container/20 rounded border border-error/30">{formError}</div>}
          
          {/* SECTION 1: GENERAL */}
          <section className="space-y-4">
            <h3 className="text-label-lg font-bold text-primary uppercase tracking-wider border-b border-outline-variant pb-2">1. General Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2 flex flex-col gap-1">
                <label className="text-label-bold text-on-surface-variant">Name</label>
                <input 
                  type="text" 
                  value={formData.name} 
                  onChange={e => setFormData({...formData, name: e.target.value})} 
                  className="px-3 py-2 border border-outline-variant rounded-md focus:ring-1 focus:ring-primary"
                  placeholder="e.g. Route Invoices"
                />
              </div>
              <div className="col-span-2 flex flex-col gap-1">
                <label className="text-label-bold text-on-surface-variant">Description</label>
                <input 
                  type="text" 
                  value={formData.description} 
                  onChange={e => setFormData({...formData, description: e.target.value})} 
                  className="px-3 py-2 border border-outline-variant rounded-md focus:ring-1 focus:ring-primary"
                  placeholder="Optional"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-label-bold text-on-surface-variant">Status</label>
                <select 
                  value={formData.is_active ? 'active' : 'disabled'}
                  onChange={e => setFormData({...formData, is_active: e.target.value === 'active'})}
                  className="px-3 py-2 border border-outline-variant rounded-md focus:ring-1 focus:ring-primary"
                >
                  <option value="active">Active</option>
                  <option value="disabled">Disabled</option>
                </select>
              </div>
            </div>
          </section>

          {/* SECTION 2: TRIGGER */}
          <section className="space-y-4">
            <h3 className="text-label-lg font-bold text-primary uppercase tracking-wider border-b border-outline-variant pb-2">2. Trigger</h3>
            <div className="flex flex-col gap-1">
              <select 
                value={formData.trigger_type} 
                onChange={e => setFormData({...formData, trigger_type: e.target.value})}
                className="px-3 py-2 border border-outline-variant rounded-md w-full focus:ring-1 focus:ring-primary"
              >
                <option value="automatic">Automatic (On Inbound Email)</option>
                <option value="manual">Manual Run</option>
              </select>
            </div>
          </section>

          {/* SECTION 3: CONDITIONS */}
          <section className="space-y-4">
            <h3 className="text-label-lg font-bold text-primary uppercase tracking-wider border-b border-outline-variant pb-2 flex justify-between items-center">
              3. Conditions
              <select 
                value={formData.trigger_conditions_json.operator}
                onChange={(e) => setFormData(p => ({...p, trigger_conditions_json: {...p.trigger_conditions_json, operator: e.target.value}}))}
                className="text-xs px-2 py-1 border border-outline-variant rounded bg-surface-container-lowest"
              >
                <option value="AND">Match ALL (AND)</option>
                <option value="OR">Match ANY (OR)</option>
              </select>
            </h3>
            <div className="space-y-3">
              {formData.trigger_conditions_json.rules?.map((rule, idx) => (
                <div key={idx} className="flex gap-2 items-center bg-surface-container-lowest p-2 border border-outline-variant rounded-md">
                  <select value={rule.field} onChange={(e) => updateCondition(idx, 'field', e.target.value)} className="p-2 border border-outline-variant rounded bg-surface flex-1">
                    <option value="sender">Sender</option>
                    <option value="subject">Subject</option>
                    <option value="label">Gmail Label</option>
                    <option value="has_attachment">Has Attachment</option>
                  </select>
                  <select value={rule.operator} onChange={(e) => updateCondition(idx, 'operator', e.target.value)} className="p-2 border border-outline-variant rounded bg-surface flex-1">
                    <option value="contains">Contains</option>
                    <option value="equals">Equals</option>
                    <option value="starts_with">Starts With</option>
                  </select>
                  <input type="text" value={rule.value} onChange={(e) => updateCondition(idx, 'value', e.target.value)} placeholder="Value..." className="p-2 border border-outline-variant rounded bg-surface flex-1" />
                  <button onClick={() => removeCondition(idx)} className="p-2 text-on-surface-variant hover:text-error"><Trash2 size={16}/></button>
                </div>
              ))}
              <button onClick={addCondition} className="text-primary text-body-md font-medium flex items-center gap-1 hover:underline">
                <PlusCircle size={16} /> Add Condition
              </button>
            </div>
          </section>

          {/* SECTION 4: ACTIONS */}
          <section className="space-y-4">
            <h3 className="text-label-lg font-bold text-primary uppercase tracking-wider border-b border-outline-variant pb-2">4. Actions</h3>
            <div className="space-y-3">
              {formData.actions_json.actions?.map((action, idx) => (
                <div key={idx} className="flex gap-2 items-center bg-surface-container-lowest p-2 border border-outline-variant rounded-md">
                  <span className="text-on-surface-variant"><GripVertical size={16} /></span>
                  <select value={action.type} onChange={(e) => updateAction(idx, 'type', e.target.value)} className="p-2 border border-outline-variant rounded bg-surface flex-1 font-semibold text-indigo-600 dark:text-indigo-400">
                    <option value="generate_ai_reply">✨ Generate AI Reply</option>
                    <option value="add_label">Add Gmail Label</option>
                    <option value="mark_important">Mark Important</option>
                    <option value="archive">Archive</option>
                    <option value="move_to_category">Move to Category</option>
                    <option value="log_execution">Log Execution</option>
                  </select>
                  {action.type === 'generate_ai_reply' ? (
                    <div className="flex flex-wrap gap-2 flex-[2] items-center">
                      <select 
                        value={action.prompt_template_id || ''}
                        onChange={(e) => updateAction(idx, 'prompt_template_id', e.target.value)}
                        className="p-2 border border-outline-variant rounded bg-surface text-xs flex-1 font-medium"
                      >
                        <option value="">-- Select Prompt Template --</option>
                        {promptTemplates.map(t => (
                          <option key={t.id} value={t.id}>{t.name}{t.purpose ? ` (${t.purpose})` : ''}</option>
                        ))}
                      </select>

                      <select 
                        value={action.require_approval !== false ? 'yes' : 'no'}
                        onChange={(e) => updateAction(idx, 'require_approval', e.target.value === 'yes')}
                        className="p-2 border border-outline-variant rounded bg-surface text-xs font-semibold"
                      >
                        <option value="yes">Human Approval: YES</option>
                        <option value="no">Human Approval: NO</option>
                      </select>

                      <select 
                        value={action.fallback_behaviour || 'label_failed'}
                        onChange={(e) => updateAction(idx, 'fallback_behaviour', e.target.value)}
                        className="p-2 border border-outline-variant rounded bg-surface text-xs text-gray-500"
                      >
                        <option value="label_failed">Fallback: Add Label 'AI-Failed'</option>
                        <option value="do_nothing">Fallback: Do Nothing</option>
                      </select>
                    </div>
                  ) : (
                    <input type="text" value={action.value || ''} onChange={(e) => updateAction(idx, 'value', e.target.value)} placeholder="Value (e.g. INVOICE)" className="p-2 border border-outline-variant rounded bg-surface flex-1 text-xs" />
                  )}
                  <button onClick={() => removeAction(idx)} className="p-2 text-on-surface-variant hover:text-error"><Trash2 size={16}/></button>
                </div>
              ))}
              <button onClick={addAction} className="text-primary text-body-md font-medium flex items-center gap-1 hover:underline">
                <PlusCircle size={16} /> Add Action
              </button>
            </div>
          </section>

        </div>
        <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-outline-variant">
          <button onClick={() => setIsModalOpen(false)} disabled={isSubmitting} className="px-4 py-2 border border-outline-variant rounded-md text-on-surface-variant hover:bg-surface-container-highest">Cancel</button>
          <button onClick={handleCreateEdit} disabled={isSubmitting} className="px-6 py-2 bg-primary text-on-primary font-medium rounded-md hover:bg-primary/90 disabled:opacity-70 flex items-center gap-2">
            {isSubmitting ? 'Saving...' : 'Save Workflow'}
          </button>
        </div>
      </Modal>

      <ConfirmDialog 
        isOpen={isDeleteDialogOpen} 
        onClose={() => setIsDeleteDialogOpen(false)}
        title="Delete Workflow"
        message={`Are you sure you want to delete "${deletingWorkflow?.name}"?`}
        confirmText="Delete"
        isDestructive={true}
        onConfirm={handleDelete}
      />

      <Modal 
        isOpen={isDetailsModalOpen} 
        onClose={() => setIsDetailsModalOpen(false)} 
        title="Workflow Details"
      >
        {viewingWorkflow && (
          <div className="flex flex-col gap-6 py-2 max-h-[75vh] overflow-y-auto px-1">
            <section className="space-y-2">
              <h3 className="text-label-lg font-bold text-primary uppercase border-b border-outline-variant pb-1">General Info</h3>
              <div className="grid grid-cols-2 gap-2 text-body-md">
                <div><span className="font-bold text-on-surface-variant">Name:</span> {viewingWorkflow.name}</div>
                <div><span className="font-bold text-on-surface-variant">Status:</span> <StatusBadge status={viewingWorkflow.is_active ? 'active' : 'disabled'} /></div>
                <div className="col-span-2"><span className="font-bold text-on-surface-variant">Description:</span> {viewingWorkflow.description || 'N/A'}</div>
              </div>
            </section>

            <section className="space-y-2">
              <h3 className="text-label-lg font-bold text-primary uppercase border-b border-outline-variant pb-1">Conditions</h3>
              <div className="bg-surface-container-lowest p-3 rounded border border-outline-variant text-body-sm whitespace-pre-wrap">
                {JSON.stringify(viewingWorkflow.trigger_conditions_json, null, 2)}
              </div>
            </section>

            <section className="space-y-2">
              <h3 className="text-label-lg font-bold text-primary uppercase border-b border-outline-variant pb-1">Configured Actions & Bound Templates</h3>
              <div className="bg-surface-container-lowest p-3 rounded border border-outline-variant text-body-sm space-y-2">
                {viewingWorkflow.actions_json?.actions?.map((act, i) => (
                  <div key={i} className="flex justify-between items-center bg-white dark:bg-gray-800 p-2 rounded border border-gray-200 dark:border-gray-700">
                    <span className="font-bold text-xs uppercase text-indigo-600 dark:text-indigo-400">{act.type}</span>
                    <span className="text-xs text-gray-500">
                      {act.type === 'generate_ai_reply' 
                        ? `Bound Prompt: ${act.prompt_template_id ? 'Customer Refund Reply' : 'Default Assistant'}`
                        : `Value: ${act.value || 'N/A'}`}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            <section className="space-y-2">
              <h3 className="text-label-lg font-bold text-primary uppercase border-b border-outline-variant pb-1">Step-by-Step Execution Trace Log</h3>
              {workflowExecutions.length === 0 ? (
                <div className="text-body-md text-on-surface-variant italic">No recent execution logs.</div>
              ) : (
                <div className="flex flex-col gap-3">
                  {workflowExecutions.map(ex => (
                    <div key={ex.id} className="p-3 border border-outline-variant rounded bg-surface-container-lowest text-body-sm space-y-2">
                      <div className="flex justify-between items-center border-b border-gray-200 dark:border-gray-700 pb-1">
                        <span className="font-semibold text-xs text-gray-900 dark:text-white">{new Date(ex.executed_at).toLocaleString()}</span>
                        <StatusBadge status={ex.status} />
                      </div>
                      <div className="space-y-1 text-xs text-gray-600 dark:text-gray-300 font-mono">
                        <div>📧 Email: {ex.email_id ? ex.email_id.substring(0,8) + '...' : 'N/A'}</div>
                        <div>⏱ Executed: {new Date(ex.executed_at).toLocaleString()}</div>
                        <div>📊 Status: {ex.status}</div>
                        {ex.error_message && <div className="text-red-500">❌ Error: {ex.error_message}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </Modal>
    </div>
  );
};

