import { useState, useEffect } from 'react';
import { Shield, Plus, Trash2, Edit2, X, CheckCircle2, AlertTriangle, Users as UsersIcon } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';
import { ConfirmDialog } from '../../components/ConfirmDialog';

const ALL_PERMISSIONS = [
  'view_users', 'create_users', 'update_users', 'delete_users', 'activate_user', 'deactivate_user', 'reset_password', 'assign_role',
  'view_roles', 'create_roles', 'update_roles', 'delete_roles', 'clone_role',
  'view_workflows', 'create_workflows', 'update_workflows', 'delete_workflows',
  'view_templates', 'create_templates', 'update_templates', 'delete_templates',
  'view_ai_providers', 'create_ai_providers', 'update_ai_providers', 'delete_ai_providers',
  'view_emails', 'view_attachments', 'view_sync_logs',
];

const Roles = () => {
  const { user } = useAuth();
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [form, setForm] = useState({ name: '', permissions: [] });
  const [feedback, setFeedback] = useState(null);
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const fetchRoles = async () => {
    try {
      setLoading(true);
      const data = await api.getRoles();
      setRoles(Array.isArray(data) ? data : data?.data || []);
    } catch (e) {
      console.error('Failed to load roles:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRoles(); }, []);

  const handleSave = async () => {
    if (!form.name) {
      setFeedback({ type: 'error', message: 'Role name is required' });
      return;
    }
    try {
      setSaving(true);
      const payload = { name: form.name, permissions: form.permissions };
      if (editingRole) {
        await api.updateRole(editingRole.id, payload);
        setFeedback({ type: 'success', message: 'Role updated successfully' });
      } else {
        await api.createRole(payload);
        setFeedback({ type: 'success', message: 'Role created successfully' });
      }
      setShowForm(false);
      setEditingRole(null);
      setForm({ name: '', permissions: [] });
      fetchRoles();
    } catch (e) {
      setFeedback({ type: 'error', message: e.response?.data?.detail || 'Failed to save role' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (roleId) => {
    setDeleteConfirm(roleId);
  };

  const confirmDelete = async () => {
    const roleId = deleteConfirm;
    setDeleteConfirm(null);
    try {
      await api.deleteRole(roleId);
      setFeedback({ type: 'success', message: 'Role deleted' });
      fetchRoles();
    } catch (e) {
      setFeedback({ type: 'error', message: e.response?.data?.detail || 'Failed to delete role' });
    }
  };

  const togglePermission = (perm) => {
    setForm(prev => ({
      ...prev,
      permissions: prev.permissions.includes(perm)
        ? prev.permissions.filter(p => p !== perm)
        : [...prev.permissions, perm]
    }));
  };

  const permissionGroups = {
    'Users': ALL_PERMISSIONS.filter(p => p.startsWith('view_users') || p.startsWith('create_users') || p.startsWith('update_users') || p.startsWith('delete_users') || p.startsWith('activate') || p.startsWith('deactivate') || p.startsWith('reset') || p.startsWith('assign')),
    'Roles': ALL_PERMISSIONS.filter(p => p.includes('role')),
    'Workflows': ALL_PERMISSIONS.filter(p => p.includes('workflow')),
    'Templates': ALL_PERMISSIONS.filter(p => p.includes('template')),
    'AI Providers': ALL_PERMISSIONS.filter(p => p.includes('ai_provider')),
    'Data': ALL_PERMISSIONS.filter(p => p.includes('email') || p.includes('attachment') || p.includes('sync')),
  };

  if (user?.role !== 'Admin') {
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
      <ConfirmDialog
        isOpen={!!deleteConfirm}
        onClose={() => setDeleteConfirm(null)}
        onConfirm={confirmDelete}
        title="Delete Role"
        message="Are you sure you want to delete this role? Users with this role will lose their assigned permissions."
        confirmText="Delete"
        isDestructive
      />
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Shield className="w-6 h-6 text-purple-600" />
            Roles & Permissions
          </h1>
          <p className="text-sm text-gray-500 mt-1">Define access levels for system users.</p>
        </div>
        <button onClick={() => { setShowForm(true); setEditingRole(null); setForm({ name: '', permissions: [] }); }} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium transition-colors">
          <Plus className="w-4 h-4" /> Create Role
        </button>
      </div>

      {feedback && (
        <div className={`p-4 rounded-xl flex items-center gap-3 text-sm ${feedback.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
          {feedback.type === 'success' ? <CheckCircle2 className="w-5 h-5 text-green-600" /> : <AlertTriangle className="w-5 h-5 text-red-600" />}
          <span>{feedback.message}</span>
          <button onClick={() => setFeedback(null)} className="ml-auto"><X className="w-4 h-4" /></button>
        </div>
      )}

      {showForm && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-xl p-5 border border-gray-200 dark:border-gray-700 space-y-4">
          <h3 className="font-bold text-sm text-gray-900 dark:text-white">{editingRole ? 'Edit Role' : 'Create New Role'}</h3>
          <div className="text-xs">
            <label className="block text-gray-400 font-semibold mb-1">Role Name</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full max-w-md p-2.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white" placeholder="e.g. Content Manager" />
          </div>
          <div className="space-y-3">
            <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Permissions</label>
            {Object.entries(permissionGroups).map(([group, perms]) => (
              <div key={group} className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                <div className="text-[10px] font-bold text-gray-400 uppercase mb-2">{group}</div>
                <div className="flex flex-wrap gap-2">
                  {perms.map(perm => (
                    <label key={perm} className="flex items-center gap-1.5 text-[11px] text-gray-600 dark:text-gray-400 cursor-pointer hover:text-gray-900 dark:hover:text-white">
                      <input
                        type="checkbox"
                        checked={form.permissions.includes(perm)}
                        onChange={() => togglePermission(perm)}
                        className="rounded"
                      />
                      {perm.replace(/_/g, ' ')}
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={() => { setShowForm(false); setEditingRole(null); }} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancel</button>
            <button onClick={handleSave} disabled={saving} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50">
              {saving ? 'Saving...' : editingRole ? 'Update' : 'Create'}
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-3 text-center py-8 text-gray-400">Loading...</div>
        ) : roles.length === 0 ? (
          <div className="col-span-3 text-center py-8 text-gray-400">No roles found. Create one to get started.</div>
        ) : roles.map(role => (
          <div key={role.id} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 flex flex-col hover:border-purple-300 dark:hover:border-purple-700 transition-colors">
            <div className="flex justify-between items-start mb-4">
              <div className="w-12 h-12 rounded-lg bg-purple-50 dark:bg-purple-900/20 flex items-center justify-center text-purple-600 dark:text-purple-400">
                <Shield className="w-6 h-6" />
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => {
                    setEditingRole(role);
                    setForm({ name: role.name, permissions: role.permissions || [] });
                    setShowForm(true);
                  }}
                  className="text-gray-400 hover:text-blue-600 p-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button onClick={() => handleDelete(role.id)} className="text-gray-400 hover:text-red-600 p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">{role.name}</h3>
            <div className="flex flex-wrap gap-1 mt-2 mb-4">
              {(role.permissions || []).slice(0, 5).map(p => (
                <span key={p} className="text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded">{p.replace(/_/g, ' ')}</span>
              ))}
              {(role.permissions || []).length > 5 && (
                <span className="text-[10px] text-gray-400">+{(role.permissions || []).length - 5} more</span>
              )}
            </div>
            <div className="pt-4 border-t border-gray-100 dark:border-gray-700/50 flex justify-between items-center text-sm font-medium text-gray-700 dark:text-gray-300 mt-auto">
              <span>Permissions</span>
              <span className="bg-gray-100 dark:bg-gray-700 px-2.5 py-1 rounded-md">{(role.permissions || []).length}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Roles;
