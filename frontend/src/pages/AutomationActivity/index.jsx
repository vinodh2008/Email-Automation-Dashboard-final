import { useLiveData } from '../../hooks/useLiveData';
import { api } from '../../api/client';
import { StatusBadge } from '../../components/StatusBadge';
import { ActivityTimeline } from '../../components/ActivityTimeline';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { Activity, Clock, Server, Database, Mail, Zap, CheckCircle2, XCircle, ListTodo } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import TaskQueue from './TaskQueue';

const TABS = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'task-queue', label: 'Task Queue', icon: ListTodo },
];

export const AutomationActivity = () => {
  const { data: summary, loading: loadingSummary } = useLiveData(api.getOperationsSummary, 30000);
  const { data: recentSyncs, loading: loadingSyncs } = useLiveData(api.getRecentSyncs, 15000);
  const { data: historyData, loading: loadingHistory, lastUpdated, error } = useLiveData(api.getAutomationHistory, 10000);

  const [timeAgo, setTimeAgo] = useState('just now');
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (!lastUpdated) return;
    const interval = setInterval(() => {
      const seconds = Math.floor((new Date() - lastUpdated) / 1000);
      if (seconds < 5) setTimeAgo('just now');
      else if (seconds < 60) setTimeAgo(`${seconds}s ago`);
      else setTimeAgo(`${Math.floor(seconds / 60)}m ago`);
    }, 1000);
    return () => clearInterval(interval);
  }, [lastUpdated]);

  const lastSync = recentSyncs?.[0];
  const lastSyncDate = lastSync ? new Date(lastSync.started_at.replace(' ', 'T')) : null;
  const isSchedulerRunning = lastSyncDate && !isNaN(lastSyncDate) && (new Date() - lastSyncDate) < 5 * 60 * 1000;

  const tabBtnCls = (active) => `flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${active ? 'bg-primary-container text-on-primary-container' : 'text-on-surface-variant hover:bg-surface-container-high'}`;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-headline-sm text-on-surface">Operations Dashboard</h2>
          <p className="text-body-md text-on-surface-variant">System health, scheduler metrics, and workflow execution history</p>
        </div>
        <div className="flex items-center gap-2">
          {error && <span className="text-[10px] text-error font-bold uppercase tracking-widest bg-error-container px-2 py-1 rounded">Connection Issue</span>}
          <span className="text-label-md text-on-surface-variant flex items-center gap-1">
            <Clock size={14} /> Last updated {timeAgo}
          </span>
        </div>
      </div>

      <div className="flex gap-1 overflow-x-auto pb-2">
        {TABS.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={tabBtnCls(activeTab === tab.id)}>
            <tab.icon size={16} /> {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
      <>
      {/* Top row: System Health Widgets */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Scheduler */}
        <div className="flat-card p-5 flex flex-col gap-3">
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-2 text-primary">
              <Activity size={20} />
              <span className="font-label-bold uppercase tracking-wider">Scheduler</span>
            </div>
            {isSchedulerRunning ? (
              <span className="flex items-center gap-1 text-xs font-bold text-[#1A7F37] bg-[#1A7F37]/10 px-2 py-1 rounded-full"><CheckCircle2 size={12}/> ACTIVE</span>
            ) : (
              <span className="flex items-center gap-1 text-xs font-bold text-[#D1242F] bg-[#D1242F]/10 px-2 py-1 rounded-full"><XCircle size={12}/> OFFLINE</span>
            )}
          </div>
          <div className="mt-2 text-body-sm text-on-surface-variant space-y-1">
            <div className="flex justify-between"><span>Last Sync:</span> <span className="text-on-surface font-medium">{lastSync ? new Date(lastSync.started_at).toLocaleTimeString() : 'N/A'}</span></div>
            <div className="flex justify-between"><span>Duration:</span> <span className="text-on-surface font-medium">{lastSync?.duration_seconds != null ? `${lastSync.duration_seconds.toFixed(1)}s` : 'Running...'}</span></div>
          </div>
        </div>

        {/* Gmail Sync */}
        <div className="flat-card p-5 flex flex-col gap-3">
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-2 text-primary">
              <Mail size={20} />
              <span className="font-label-bold uppercase tracking-wider">Gmail API</span>
            </div>
            <span className="flex items-center gap-1 text-xs font-bold text-[#1A7F37] bg-[#1A7F37]/10 px-2 py-1 rounded-full"><CheckCircle2 size={12}/> HEALTHY</span>
          </div>
          <div className="mt-2 text-body-sm text-on-surface-variant space-y-1">
            <div className="flex justify-between"><span>Accounts:</span> <span className="text-on-surface font-medium">{summary?.counts?.mailbox_accounts || 0} Connected</span></div>
            <div className="flex justify-between"><span>Emails Collected:</span> <span className="text-on-surface font-medium">{summary?.counts?.emails_collected || 0}</span></div>
          </div>
        </div>

        {/* Workflow Engine */}
        <div className="flat-card p-5 flex flex-col gap-3">
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-2 text-primary">
              <Zap size={20} />
              <span className="font-label-bold uppercase tracking-wider">Workflows</span>
            </div>
            <span className="flex items-center gap-1 text-xs font-bold text-primary bg-primary/10 px-2 py-1 rounded-full"><Activity size={12}/> SYNCHRONOUS</span>
          </div>
          <div className="mt-2 text-body-sm text-on-surface-variant space-y-1">
            <div className="flex justify-between"><span>Executions:</span> <span className="text-on-surface font-medium">{historyData?.total || 0}</span></div>
            <div className="flex justify-between"><span>Queue:</span> <span className="text-on-surface font-medium">0 (Realtime)</span></div>
          </div>
        </div>

        {/* System */}
        <div className="flat-card p-5 flex flex-col gap-3">
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-2 text-primary">
              <Database size={20} />
              <span className="font-label-bold uppercase tracking-wider">Database</span>
            </div>
            <span className="flex items-center gap-1 text-xs font-bold text-[#1A7F37] bg-[#1A7F37]/10 px-2 py-1 rounded-full"><CheckCircle2 size={12}/> CONNECTED</span>
          </div>
          <div className="mt-2 text-body-sm text-on-surface-variant space-y-1">
            <div className="flex justify-between"><span>Sync Errors:</span> <span className="text-error font-medium">{summary?.counts?.sync_errors_total || 0}</span></div>
            <div className="flex justify-between"><span>Attachments:</span> <span className="text-on-surface font-medium">{summary?.counts?.attachments_stored || 0}</span></div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Recent Sync Logs */}
        <div className="lg:col-span-1 flat-card">
          <div className="px-6 py-4 bg-[#F6F8FA] border-b border-outline-variant">
            <h3 className="font-label-bold text-on-surface uppercase tracking-wider">Recent Sync Cycles</h3>
          </div>
          <div className="divide-y divide-outline-variant max-h-[500px] overflow-y-auto">
            {loadingSyncs ? <LoadingSkeleton type="table" rows={4} /> : recentSyncs?.length > 0 ? (
              recentSyncs.map(sync => (
                <div key={sync.id} className="p-4 hover:bg-surface-container-lowest transition-colors flex flex-col gap-2">
                  <div className="flex justify-between items-center">
                    <span className="text-label-md font-medium text-on-surface">{new Date(sync.started_at).toLocaleTimeString()}</span>
                    <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded ${
                      sync.status === 'completed' ? 'bg-[#1A7F37]/10 text-[#1A7F37]' :
                      sync.status === 'failed' ? 'bg-[#D1242F]/10 text-[#D1242F]' :
                      'bg-[#BF8700]/10 text-[#BF8700]'
                    }`}>{sync.status}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-body-sm text-on-surface-variant">
                    <div>Inserted: <span className="font-medium text-on-surface">{sync.metrics.emails_inserted}</span></div>
                    <div>Duplicates: <span className="font-medium text-on-surface">{sync.metrics.duplicates_skipped}</span></div>
                    <div>Failed: <span className="font-medium text-error">{sync.metrics.emails_failed}</span></div>
                    <div>Duration: <span className="font-medium text-on-surface">{sync.duration_seconds != null ? `${sync.duration_seconds.toFixed(1)}s` : 'Running...'}</span></div>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-on-surface-variant text-body-md">No sync history available</div>
            )}
          </div>
        </div>

        {/* Right Column: Workflow History Timeline */}
        <div className="lg:col-span-2 flat-card">
          <div className="px-6 py-4 bg-[#F6F8FA] border-b border-outline-variant flex justify-between items-center">
            <h3 className="font-label-bold text-on-surface uppercase tracking-wider">Recent Workflow Executions</h3>
            <Link to="/automation/logs" className="text-primary text-label-bold uppercase hover:underline">
              View Full Logs
            </Link>
          </div>
          {loadingHistory ? (
            <div className="p-6"><LoadingSkeleton type="table" rows={6} /></div>
          ) : (
            <ActivityTimeline activities={historyData?.data} />
          )}
        </div>
      </div>
      </>
      )}

      {activeTab === 'task-queue' && (
        <TaskQueue />
      )}
    </div>
  );
};

