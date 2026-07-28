import { useState, useEffect } from 'react';
import { X, Clock, FileText, CheckCircle, AlertCircle, Copy } from 'lucide-react';
import { api } from '../../api/client';
import { StatusBadge } from '../StatusBadge';
import DOMPurify from 'dompurify';

export const EmailDetailDrawer = ({ emailId, onClose }) => {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    if (!emailId) return;
    
    const fetchDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getEmailDetail(emailId);
        setDetail(data);
      } catch (err) {
        setError("Failed to load email details.");
      } finally {
        setLoading(false);
      }
    };
    
    fetchDetail();
  }, [emailId]);

  if (!emailId) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-40 transition-opacity" onClick={onClose} />
      
      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 w-full max-w-2xl bg-surface shadow-2xl z-50 flex flex-col border-l border-outline-variant overflow-hidden transform transition-transform duration-300">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-outline-variant bg-surface-container-low">
          <h2 className="text-title-lg text-on-surface font-semibold">Email Details</h2>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-surface-container-high text-on-surface-variant transition-colors">
            <X size={20} />
          </button>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          
          {loading && (
            <div className="flex flex-col items-center justify-center h-48 gap-3">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
              <p className="text-body-md text-on-surface-variant">Loading details...</p>
            </div>
          )}
          
          {error && (
            <div className="p-4 bg-error-container text-on-error-container rounded-md flex items-start gap-3">
              <AlertCircle size={20} className="shrink-0 mt-0.5" />
              <p className="text-body-md">{error}</p>
            </div>
          )}
          
          {detail && !loading && !error && (
            <>
              {/* General Info */}
              <section className="space-y-4">
                <h3 className="text-label-lg uppercase tracking-wider text-on-surface-variant font-bold border-b border-outline-variant pb-2">General</h3>
                
                <div className="grid grid-cols-3 gap-y-4">
                  <div className="col-span-1 text-body-md text-on-surface-variant">Sender:</div>
                  <div className="col-span-2 text-body-md font-medium text-on-surface">{detail.sender}</div>
                  
                  <div className="col-span-1 text-body-md text-on-surface-variant">To:</div>
                  <div className="col-span-2 text-body-md text-on-surface">{detail.to_recipients?.join(', ') || 'N/A'}</div>
                  
                  <div className="col-span-1 text-body-md text-on-surface-variant">Subject:</div>
                  <div className="col-span-2 text-body-md font-medium text-on-surface">{detail.subject}</div>
                  
                  <div className="col-span-1 text-body-md text-on-surface-variant">Received Time:</div>
                  <div className="col-span-2 text-body-md text-on-surface">{new Date(detail.sent_time).toLocaleString()}</div>
                  
                  <div className="col-span-1 text-body-md text-on-surface-variant">Provider Message ID:</div>
                  <div className="col-span-2 text-body-md text-on-surface font-mono text-sm">{detail.provider_message_id || 'N/A'}</div>
                  
                  <div className="col-span-1 text-body-md text-on-surface-variant">Provider Thread ID:</div>
                  <div className="col-span-2 text-body-md text-on-surface font-mono text-sm">{detail.provider_thread_id || 'N/A'}</div>
                </div>
              </section>

              {/* Body Content */}
              <section className="space-y-4">
                <h3 className="text-label-lg uppercase tracking-wider text-on-surface-variant font-bold border-b border-outline-variant pb-2">Body Content</h3>
                <div className="space-y-4">
                  <div>
                    <h4 className="text-label-md text-on-surface-variant mb-2">Plain Text</h4>
                    <div className="p-3 bg-surface-container-lowest border border-outline-variant rounded-md text-body-sm font-mono max-h-60 overflow-y-auto whitespace-pre-wrap">
                      {detail.body_text || <span className="italic text-on-surface-variant">No plain text body</span>}
                    </div>
                  </div>
                  {detail.body_html && (
                    <div>
                      <h4 className="text-label-md text-on-surface-variant mb-2">HTML Outline</h4>
                      <div className="p-3 bg-surface-container-lowest border border-outline-variant rounded-md text-body-sm max-h-60 overflow-y-auto" dangerouslySetInnerHTML={{__html: DOMPurify.sanitize(detail.body_html)}} />
                    </div>
                  )}
                </div>
              </section>

              {/* Classification */}
              <section className="space-y-4">
                <h3 className="text-label-lg uppercase tracking-wider text-on-surface-variant font-bold border-b border-outline-variant pb-2">Classification</h3>
                
                <div className="grid grid-cols-3 gap-y-4 items-center">
                  <div className="col-span-1 text-body-md text-on-surface-variant">Category:</div>
                  <div className="col-span-2 text-body-md font-medium text-on-surface">
                    <span className="bg-surface-container-high px-2 py-1 rounded text-sm">{detail.category}</span>
                  </div>
                  
                  <div className="col-span-1 text-body-md text-on-surface-variant">Labels:</div>
                  <div className="col-span-2 flex flex-wrap gap-2">
                    {detail.labels.length > 0 ? detail.labels.map(l => (
                      <span key={l} className="bg-secondary-container text-on-secondary-container px-2 py-0.5 rounded text-xs">{l}</span>
                    )) : <span className="text-body-md text-on-surface-variant">None</span>}
                  </div>
                  
                  <div className="col-span-1 text-body-md text-on-surface-variant">Workflow:</div>
                  <div className="col-span-2 text-body-md font-medium text-primary">{detail.workflow_name}</div>
                </div>
              </section>

              {/* Processing */}
              <section className="space-y-4">
                <h3 className="text-label-lg uppercase tracking-wider text-on-surface-variant font-bold border-b border-outline-variant pb-2">Processing</h3>
                
                <div className="grid grid-cols-3 gap-y-4 items-center">
                  <div className="col-span-1 text-body-md text-on-surface-variant">Status:</div>
                  <div className="col-span-2"><StatusBadge status={detail.status} /></div>
                  
                  <div className="col-span-1 text-body-md text-on-surface-variant">Last Action:</div>
                  <div className="col-span-2 text-body-md text-on-surface font-medium">{detail.last_action}</div>
                  
                  <div className="col-span-1 text-body-md text-on-surface-variant">Processing Time:</div>
                  <div className="col-span-2 text-body-md text-on-surface">{detail.processing_duration ? `${detail.processing_duration.toFixed(2)}s` : 'N/A'}</div>
                </div>
              </section>

              {/* Execution Timeline */}
              <section className="space-y-4">
                <h3 className="text-label-lg uppercase tracking-wider text-on-surface-variant font-bold border-b border-outline-variant pb-2">Execution Timeline</h3>
                
                <div className="relative border-l border-outline-variant ml-3 space-y-6">
                  {detail.execution_timeline?.map((event, i) => (
                    <div key={i} className="relative pl-6">
                      <div className={`absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 border-surface ${
                        event.status === 'success' ? 'bg-[#1A7F37]' : 
                        event.status === 'error' ? 'bg-[#D1242F]' : 
                        'bg-primary'
                      }`}></div>
                      <div className="flex flex-col">
                        <span className="text-label-sm text-on-surface-variant">{new Date(event.timestamp).toLocaleTimeString()}</span>
                        <span className="text-body-md font-medium text-on-surface">{event.title}</span>
                        <span className="text-body-sm text-on-surface-variant">{event.description}</span>
                      </div>
                    </div>
                  ))}
                  
                  {(!detail.execution_timeline || detail.execution_timeline.length === 0) && (
                    <div className="pl-6 text-body-md text-on-surface-variant italic">No timeline events recorded.</div>
                  )}
                </div>
              </section>
              
              {/* Attachments */}
              {detail.attachments && detail.attachments.length > 0 && (
                <section className="space-y-4">
                  <h3 className="text-label-lg uppercase tracking-wider text-on-surface-variant font-bold border-b border-outline-variant pb-2">Attachments ({detail.attachments.length})</h3>
                  <div className="space-y-2">
                    {detail.attachments.map(a => (
                      <div key={a.id} className="flex items-center gap-3 p-3 border border-outline-variant rounded-md bg-surface-container-lowest">
                        <FileText size={16} className="text-primary" />
                        <span className="text-body-md text-on-surface flex-1 truncate">{a.filename}</span>
                        <span className="text-label-sm text-on-surface-variant">{(a.size_bytes / 1024).toFixed(1)} KB</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>
        
        {/* Footer Actions */}
        {detail && (
          <div className="p-4 border-t border-outline-variant bg-surface-container-low flex flex-wrap justify-end gap-3">
             {detail.provider_message_id && (
               <a 
                 href={`https://mail.google.com/mail/u/0/#all/${detail.provider_message_id}`}
                 target="_blank"
                 rel="noreferrer"
                 className="flex items-center gap-2 px-4 py-2 border border-outline-variant rounded-md text-sm font-medium hover:bg-surface-container-high transition-colors"
               >
                  Open in Gmail
               </a>
             )}
             <button 
                onClick={() => { navigator.clipboard.writeText(detail.provider_message_id || detail.id); }}
                className="flex items-center gap-2 px-4 py-2 border border-outline-variant rounded-md text-sm font-medium hover:bg-surface-container-high transition-colors"
             >
                <Copy size={16} /> Copy Message ID
             </button>
             {detail.provider_thread_id && (
               <button 
                  onClick={() => { navigator.clipboard.writeText(detail.provider_thread_id); }}
                  className="flex items-center gap-2 px-4 py-2 border border-outline-variant rounded-md text-sm font-medium hover:bg-surface-container-high transition-colors"
               >
                  <Copy size={16} /> Copy Thread ID
               </button>
             )}
             <button onClick={onClose} className="px-4 py-2 bg-primary text-on-primary rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">
                Close
             </button>
          </div>
        )}
      </div>
    </>
  );
};
