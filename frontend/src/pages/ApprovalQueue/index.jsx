import { useState, useEffect } from 'react';
import { Shield, Check, X, Edit3, Search, Clock, Sparkles, Filter, CheckSquare, Mail } from 'lucide-react';
import { api } from '../../api/client';
import { StatusBadge } from '../../components/StatusBadge';
import { useMailbox } from '../../context/MailboxContext';

const ApprovalQueue = () => {
  const { isConnected, loading: mailboxLoading } = useMailbox();
  const [approvals, setApprovals] = useState([]);
  const [activeTab, setActiveTab] = useState('pending');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editedText, setEditedText] = useState('');

  const fetchApprovals = async () => {
    try {
      setLoading(true);
      const data = await api.getPendingApprovals();
      setApprovals(data || []);
    } catch (err) {
      console.error('Failed to load approvals:', err);
      setApprovals([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isConnected) {
      fetchApprovals();
    } else {
      setLoading(false);
    }
  }, [isConnected]);

  const handleApprove = async (id, customText = null) => {
    try {
      await api.approveAIDraft(id, customText);
      setEditingId(null);
      fetchApprovals();
    } catch (err) {
      console.error('Failed to approve draft:', err);
    }
  };

  const handleReject = async (id) => {
    try {
      await api.rejectAIDraft(id);
      fetchApprovals();
    } catch (err) {
      console.error('Failed to reject draft:', err);
    }
  };

  const handleBulkApprove = async () => {
    for (const id of selectedIds) {
      await api.approveAIDraft(id);
    }
    setSelectedIds([]);
    fetchApprovals();
  };

  const handleBulkReject = async () => {
    for (const id of selectedIds) {
      await api.rejectAIDraft(id);
    }
    setSelectedIds([]);
    fetchApprovals();
  };

  const filteredApprovals = approvals.filter(item => {
    const matchesTab = 
      activeTab === 'all' ? true :
      activeTab === 'pending' ? item.status === 'pending_review' :
      activeTab === 'approved' ? item.status === 'approved' :
      activeTab === 'rejected' ? item.status === 'rejected' : true;

    const matchesSearch = 
      !search || 
      item.email_subject?.toLowerCase().includes(search.toLowerCase()) ||
      item.email_sender?.toLowerCase().includes(search.toLowerCase()) ||
      item.workflow_name?.toLowerCase().includes(search.toLowerCase());

    return matchesTab && matchesSearch;
  });

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredApprovals.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredApprovals.map(i => i.id));
    }
  };

  const toggleSelect = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  return (
    <div className="space-y-6">
      {/* Disconnected State */}
      {!mailboxLoading && !isConnected && (
        <div className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white rounded-2xl p-6 md:p-8 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-white/20 text-white backdrop-blur-sm">
              <Mail className="w-3.5 h-3.5 mr-1.5" /> Gmail Not Connected
            </div>
            <h2 className="text-xl md:text-2xl font-bold">AI Approval Queue unavailable</h2>
            <p className="text-sm text-blue-100 leading-relaxed">
              Connect your Gmail account to enable AI draft generation and approval workflows.
            </p>
          </div>
          <a
            href="/settings"
            className="bg-white text-blue-700 hover:bg-blue-50 font-bold px-6 py-3 rounded-xl text-sm transition-all shadow-sm flex items-center gap-2 whitespace-nowrap"
          >
            Connect Gmail <Mail className="w-4 h-4" />
          </a>
        </div>
      )}

      {/* Header Bar - Only show when connected */}
      {isConnected && (
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Shield className="w-6 h-6 text-amber-500" />
              AI Draft Approval Queue
            </h2>
            <p className="text-sm text-gray-500 mt-1">Review and approve AI-generated email drafts. Email sending will be available in a future release.</p>
          </div>

          {selectedIds.length > 0 && (
            <div className="flex items-center gap-2 bg-amber-50 dark:bg-amber-950/40 p-2 rounded-xl border border-amber-200 dark:border-amber-800">
              <span className="text-xs font-semibold text-amber-800 dark:text-amber-300 px-2">{selectedIds.length} Selected</span>
              <button
                onClick={handleBulkApprove}
                className="bg-green-600 hover:bg-green-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1 transition-colors"
              >
                <Check className="w-3.5 h-3.5" /> Bulk Approve
              </button>
              <button
                onClick={handleBulkReject}
                className="bg-red-600 hover:bg-red-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1 transition-colors"
              >
                <X className="w-3.5 h-3.5" /> Bulk Reject
              </button>
            </div>
          )}
        </div>
      )}

      {/* Filters & Tabs - Only show when connected */}
      {isConnected && (
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-200 dark:border-gray-700 shadow-xs">
          <div className="flex items-center gap-2">
            {['pending', 'approved', 'rejected', 'all'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-lg text-xs font-semibold capitalize transition-all ${
                  activeTab === tab
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                {tab === 'pending' ? 'Pending Review' : tab} ({
                  tab === 'all' ? approvals.length : approvals.filter(i => (tab === 'pending' ? i.status === 'pending_review' : i.status === tab)).length
                })
              </button>
            ))}
          </div>

          <div className="relative w-full md:w-64">
            <Search className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
            <input
              type="text"
              placeholder="Search by subject, sender..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        </div>
      )}

      {/* Approvals Table / Card Grid - Only show when connected */}
      {isConnected && (
        loading ? (
          <div className="bg-white dark:bg-gray-800 p-12 text-center text-gray-400 text-sm rounded-xl border border-gray-200 dark:border-gray-700">
            Loading AI approval queue...
          </div>
        ) : filteredApprovals.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 p-16 text-center rounded-xl border border-gray-200 dark:border-gray-700 space-y-3">
            <div className="w-12 h-12 bg-green-50 dark:bg-green-950/40 text-green-600 rounded-full flex items-center justify-center mx-auto">
              <Check className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-gray-900 dark:text-white">No drafts to display</h3>
            <p className="text-xs text-gray-500 max-w-sm mx-auto">There are currently no AI drafts matching your filter criteria.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Table Header Controls */}
            <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 dark:bg-gray-900 rounded-lg text-xs font-semibold text-gray-500">
              <input
                type="checkbox"
                checked={selectedIds.length === filteredApprovals.length && filteredApprovals.length > 0}
                onChange={toggleSelectAll}
                className="rounded text-indigo-600 focus:ring-indigo-500"
              />
              <span>Select All</span>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {filteredApprovals.map((item) => (
                <div
                  key={item.id}
                  className={`bg-white dark:bg-gray-800 border rounded-xl p-5 space-y-4 transition-all shadow-xs ${
                    selectedIds.includes(item.id) ? 'border-indigo-500 ring-1 ring-indigo-500' : 'border-gray-200 dark:border-gray-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(item.id)}
                        onChange={() => toggleSelect(item.id)}
                        className="rounded text-indigo-600 focus:ring-indigo-500 mt-1"
                      />
                      <div>
                        <div className="flex items-center gap-2 text-xs text-gray-400">
                          <span className="font-semibold text-indigo-600 dark:text-indigo-400">{item.workflow_name}</span>
                          <span>•</span>
                          <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {new Date(item.created_at).toLocaleString()}</span>
                        </div>
                        <h3 className="text-base font-bold text-gray-900 dark:text-white mt-0.5">{item.email_subject}</h3>
                        <p className="text-xs text-gray-500">From: {item.email_sender}</p>
                      </div>
                    </div>

                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                      item.status === 'approved' ? 'bg-green-100 text-green-800' : item.status === 'rejected' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
                    }`}>
                      {item.status === 'pending_review' ? 'Pending Review' : item.status}
                    </span>
                  </div>

                  {/* Draft Body */}
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1">
                        <Sparkles className="w-3.5 h-3.5 text-indigo-500" /> Proposed AI Response Draft
                      </label>
                      {item.status === 'pending_review' && editingId !== item.id && (
                        <button
                          onClick={() => {
                            setEditingId(item.id);
                            setEditedText(item.edited_content || item.generated_content);
                          }}
                          className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                        >
                          <Edit3 className="w-3 h-3" /> Edit Draft
                        </button>
                      )}
                    </div>

                    {editingId === item.id ? (
                      <div className="space-y-2">
                        <textarea
                          rows={6}
                          value={editedText}
                          onChange={(e) => setEditedText(e.target.value)}
                          className="w-full text-xs p-3 rounded-lg border border-indigo-400 dark:border-indigo-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white font-mono focus:ring-1 focus:ring-indigo-500"
                        />
                        <div className="flex justify-end gap-2">
                          <button onClick={() => setEditingId(null)} className="px-3 py-1 text-xs text-gray-500 hover:bg-gray-100 rounded">Cancel</button>
                          <button onClick={() => handleApprove(item.id, editedText)} className="px-3 py-1 text-xs bg-green-600 text-white rounded font-semibold">Save & Approve</button>
                        </div>
                      </div>
                    ) : (
                      <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-xl text-xs font-mono text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 whitespace-pre-wrap">
                        {item.edited_content || item.generated_content}
                      </div>
                    )}
                  </div>

                  {/* Footer Controls */}
                  {item.status === 'pending_review' && editingId !== item.id && (
                    <div className="flex justify-end gap-2 pt-2 border-t border-gray-100 dark:border-gray-700">
                      <button
                        onClick={() => handleReject(item.id)}
                        className="px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-red-100 hover:text-red-700 text-gray-600 dark:text-gray-300 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1"
                      >
                        <X className="w-4 h-4" /> Reject
                      </button>
                      <button
                        onClick={() => handleApprove(item.id)}
                        className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-1"
                      >
                        <Check className="w-4 h-4" /> Approve
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )
      )}
    </div>
  );
};

export default ApprovalQueue;
