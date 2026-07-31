import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Clock, CheckCircle, AlertTriangle, XCircle, RotateCcw, Trash2 } from 'lucide-react';
import { api } from '../../api/client';

export default function TaskQueue() {
  const [stats, setStats] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsData, tasksData] = await Promise.all([
        api.getTaskQueueStats(),
        api.getPendingTasks(50),
      ]);
      setStats(statsData);
      setTasks(Array.isArray(tasksData) ? tasksData : []);
    } catch (e) {
      console.error('Failed to load task queue:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => {
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  useEffect(() => {
    if (!feedback) return;
    const t = setTimeout(() => setFeedback(null), 4000);
    return () => clearTimeout(t);
  }, [feedback]);

  const handleRetry = async (taskId) => {
    try {
      await api.retryTask(taskId);
      setFeedback({ type: 'success', text: 'Task queued for retry' });
      fetchData();
    } catch (e) {
      setFeedback({ type: 'error', text: 'Failed to retry task' });
    }
  };

  const handleCancel = async (taskId) => {
    try {
      await api.cancelTask(taskId);
      setFeedback({ type: 'success', text: 'Task cancelled' });
      fetchData();
    } catch (e) {
      setFeedback({ type: 'error', text: 'Failed to cancel task' });
    }
  };

  const statCard = (label, value, icon, color) => (
    <div className="bg-surface-container border border-outline-variant rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );

  const statusBadge = (status) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      dead_letter: 'bg-purple-100 text-purple-800',
      cancelled: 'bg-gray-100 text-gray-800',
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${styles[status] || 'bg-gray-100 text-gray-800'}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-on-surface">Task Queue</h1>
          <p className="text-sm text-on-surface-variant mt-1">Real-time async email processing pipeline</p>
        </div>
        <button onClick={fetchData} className="flex items-center gap-2 px-3 py-2 border border-outline-variant rounded-lg text-sm font-medium hover:bg-surface-container-high transition-colors">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {feedback && (
        <div className={`px-4 py-3 rounded-lg text-sm font-medium ${
          feedback.type === 'success' ? 'bg-[#DAFBE1] text-[#1A7F37]' : 'bg-error-container text-on-error-container'
        }`}>
          {feedback.text}
        </div>
      )}

      {loading && !stats ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-24 bg-surface-container rounded-lg animate-pulse" />)}
        </div>
      ) : stats ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {statCard('Pending', stats.pending || 0, <Clock size={16} className="text-yellow-500" />, 'text-yellow-600')}
          {statCard('Processing', stats.processing || 0, <RefreshCw size={16} className="text-blue-500" />, 'text-blue-600')}
          {statCard('Completed', stats.completed || 0, <CheckCircle size={16} className="text-green-500" />, 'text-green-600')}
          {statCard('Failed', (stats.failed || 0) + (stats.dead_letter || 0), <AlertTriangle size={16} className="text-red-500" />, 'text-red-600')}
        </div>
      ) : null}

      <div className="bg-surface-container border border-outline-variant rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-outline-variant">
          <h2 className="text-sm font-bold text-on-surface">Recent Tasks</h2>
        </div>
        {tasks.length === 0 ? (
          <div className="py-12 text-center">
            <Clock size={40} className="mx-auto text-on-surface-variant/30 mb-3" />
            <p className="text-sm text-on-surface-variant">No pending tasks</p>
          </div>
        ) : (
          <div className="divide-y divide-outline-variant/50">
            {tasks.map(task => (
              <div key={task.id} className="px-4 py-3 flex items-center justify-between hover:bg-surface-container-high transition-colors">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-2 h-2 rounded-full flex-shrink-0" style={{
                    backgroundColor: task.status === 'pending' ? '#EAB308' : task.status === 'processing' ? '#3B82F6' : task.status === 'completed' ? '#22C55E' : '#EF4444'
                  }} />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-on-surface truncate">{task.task_type}</span>
                      {statusBadge(task.status)}
                    </div>
                    <p className="text-xs text-on-surface-variant truncate">{task.entity_type}:{task.entity_id?.slice(0, 8)}...</p>
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <span className="text-[10px] text-on-surface-variant/50 mr-2">P{task.priority}</span>
                  {task.status === 'pending' && task.retry_count > 0 && (
                    <button onClick={() => handleRetry(task.id)} className="p-1.5 hover:bg-surface-container rounded-lg transition-colors" title="Retry">
                      <RotateCcw size={12} className="text-on-surface-variant" />
                    </button>
                  )}
                  {task.status === 'pending' && (
                    <button onClick={() => handleCancel(task.id)} className="p-1.5 hover:bg-error-container/30 rounded-lg transition-colors" title="Cancel">
                      <Trash2 size={12} className="text-on-error-container" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
