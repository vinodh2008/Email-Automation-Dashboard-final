import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLiveData } from '../../hooks/useLiveData';
import { api } from '../../api/client';
import { KpiCard } from '../../components/KpiCard';
import { ActivityTimeline } from '../../components/ActivityTimeline';
import { LoadingSkeleton } from '../../components/LoadingSkeleton';
import { Mail, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useMailbox } from '../../context/MailboxContext';

export const DashboardOverview = () => {
  const navigate = useNavigate();
  const { isConnected, loading: mailboxLoading } = useMailbox();

  const { data: summary, loading: summaryLoading } = useLiveData(
    api.getDashboardSummary,
    5000,
    [isConnected],
    isConnected
  );
  const { data: recentActivity, loading: activityLoading } = useLiveData(
    api.getRecentActivity,
    5000,
    [isConnected],
    isConnected
  );

  return (
    <div className="flex flex-col gap-8">
      {/* Connection State Onboarding Banner */}
      {!mailboxLoading && !isConnected && (
        <div className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white rounded-2xl p-6 md:p-8 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-white/20 text-white backdrop-blur-sm">
              <Mail className="w-3.5 h-3.5 mr-1.5" /> Setup Required
            </div>
            <h2 className="text-xl md:text-2xl font-bold">Connect your Gmail Account to start automation</h2>
            <p className="text-sm text-blue-100 leading-relaxed">
              Workflows, automated categorization, and email monitoring are currently paused. Connect your Google OAuth account to begin parsing emails in real time.
            </p>
          </div>
          <button
            onClick={() => navigate('/settings')}
            className="bg-white text-blue-700 hover:bg-blue-50 font-bold px-6 py-3 rounded-xl text-sm transition-all shadow-sm flex items-center gap-2 whitespace-nowrap"
          >
            Connect Gmail Account <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* KPI Grid - Only show when connected */}
      {isConnected && (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {summaryLoading ? (
            Array(8).fill(0).map((_, i) => <LoadingSkeleton key={i} type="card" />)
          ) : summary ? (
            <>
              <KpiCard label="Emails Processed" value={(summary.emails_processed ?? 0) >= 1000 ? ((summary.emails_processed / 1000).toFixed(1) + 'k') : (summary.emails_processed ?? 0).toLocaleString()} />
              <KpiCard label="Awaiting Approval" value={(summary.pending_approvals ?? 0).toLocaleString()} status={summary.pending_approvals > 0 ? 'warning' : 'success'} />
              <KpiCard label="Workflows Active" value={(summary.active_workflows ?? 0).toLocaleString()} />
              <KpiCard label="AI Success Rate" value={`${summary.ai_success_rate ?? 0}%`} status={summary.ai_success_rate >= 80 ? 'success' : summary.ai_success_rate >= 50 ? 'warning' : 'error'} />
              <KpiCard label="System Health" value={`${summary.system_health_percent ?? 0}%`} status="success" />
              <KpiCard label="Failed Executions" value={(summary.failed_executions ?? 0).toLocaleString()} status={summary.failed_executions > 0 ? 'error' : 'success'} />
              <KpiCard label="Sync Errors" value={(summary.total_sync_errors ?? 0).toLocaleString()} status={summary.total_sync_errors > 0 ? 'warning' : 'success'} />
              <KpiCard label="Pending Jobs" value={(summary.pending_jobs ?? 0).toLocaleString()} />
            </>
          ) : (
            Array(8).fill(0).map((_, i) => <KpiCard key={i} label="—" value="—" />)
          )}
        </section>
      )}

      {/* Zero-state KPIs when disconnected */}
      {!mailboxLoading && !isConnected && (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <KpiCard label="Emails Processed" value="0" />
          <KpiCard label="Awaiting Approval" value="0" />
          <KpiCard label="Workflows Active" value="0" />
          <KpiCard label="AI Success Rate" value="--" />
        </section>
      )}

      {/* Line Chart Area - Only show when connected */}
      {isConnected && (
        <section className="flat-card p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="font-headline-sm text-headline-sm text-on-surface">Email Processing Volume</h2>
            <div className="flex gap-4">
              <span className="text-label-md text-on-surface-variant flex items-center gap-1">
                <span className="w-3 h-3 bg-primary block rounded-full"></span> Incoming
              </span>
              <span className="text-label-md text-on-surface-variant flex items-center gap-1">
                <span className="w-3 h-3 bg-secondary block rounded-full"></span> Automated
              </span>
            </div>
          </div>

          <div className="h-64 w-full flex items-end justify-between gap-1 border-b border-l border-outline-variant pb-1 pl-1">
            <div className="relative w-full h-full flex flex-col justify-end pb-[10px]">
               <div className="absolute inset-0 flex flex-col justify-between pointer-events-none mb-[10px]">
                 <div className="border-t border-outline-variant/30 w-full h-px"></div>
                 <div className="border-t border-outline-variant/30 w-full h-px"></div>
                 <div className="border-t border-outline-variant/30 w-full h-px"></div>
                 <div className="border-t border-outline-variant/30 w-full h-px"></div>
               </div>

               {summaryLoading ? (
                  <div className="w-full h-full bg-surface-container-low animate-pulse"></div>
                ) : (
                  (() => {
                    const series = summary?.email_volume_series || [];
                    if (series.length < 2) return null;

                    const maxVal = Math.max(...series.map(d => Math.max(d.incoming, 1)));
                    const points = series.map((d, i) => {
                      const x = (i / (series.length - 1)) * 1000;
                      const y = 100 - ((d.incoming / maxVal) * 80);
                      return `${x},${y}`;
                    }).join(' ');

                    return (
                      <svg className="w-full h-[calc(100%-10px)] absolute bottom-[10px]" preserveAspectRatio="none" viewBox="0 0 1000 100">
                         <polyline fill="none" points={points} stroke="#0051ae" strokeWidth="2"></polyline>
                         <path d={`M0,100 L${points} L1000,100 Z`} fill="rgba(0, 81, 174, 0.05)"></path>
                      </svg>
                    );
                  })()
                )}
            </div>
          </div>

          <div className="flex justify-between mt-2 text-[10px] text-on-surface-variant font-bold uppercase tracking-tighter">
            {summary?.email_volume_series ? summary.email_volume_series.map((pt, i) => (
               <span key={i}>{pt.time} {parseInt(pt.time) < 12 ? 'AM' : 'PM'}</span>
            )) : (
               <>
                  <span>08:00 AM</span>
                  <span>10:00 AM</span>
                  <span>12:00 PM</span>
                  <span>02:00 PM</span>
                  <span>04:00 PM</span>
                  <span>06:00 PM</span>
                  <span>08:00 PM</span>
               </>
            )}
          </div>
        </section>
      )}

      {/* Recent Activity - Only show when connected */}
      {isConnected && (
        <section className="flat-card overflow-hidden">
          <div className="px-6 py-4 bg-[#F6F8FA] border-b border-outline-variant">
            <h3 className="font-label-bold text-on-surface uppercase tracking-wider">Recent System Activity</h3>
          </div>
          {activityLoading ? (
            <div className="p-6"><LoadingSkeleton type="table" rows={4} /></div>
          ) : (
            <ActivityTimeline activities={recentActivity?.data} />
          )}
          <div className="px-6 py-3 bg-[#F6F8FA] flex justify-center border-t border-outline-variant">
            <button onClick={() => navigate('/logs')} className="text-label-bold text-primary hover:underline transition-all">View All Activity History</button>
          </div>
        </section>
      )}

      {/* Activity Paused State when disconnected */}
      {!mailboxLoading && !isConnected && (
        <section className="flat-card overflow-hidden">
          <div className="px-6 py-4 bg-[#F6F8FA] border-b border-outline-variant">
            <h3 className="font-label-bold text-on-surface uppercase tracking-wider">Recent System Activity</h3>
          </div>
          <div className="p-12 text-center">
            <CheckCircle2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2">Activity tracking paused</h3>
            <p className="text-sm text-gray-500">Connect your Gmail account to see real-time activity.</p>
          </div>
        </section>
      )}
    </div>
  );
};
