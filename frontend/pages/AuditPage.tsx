import React from 'react';
import { MOCK_AUDIT_LOGS } from '../constants';
import { Upload, Search, CheckCircle, XCircle, LogIn, RefreshCw, AlertCircle } from 'lucide-react';

const AuditPage: React.FC = () => {
  const getIcon = (action: string) => {
    switch(action) {
        case 'upload': return <Upload className="w-4 h-4 text-blue-400" />;
        case 'search': return <Search className="w-4 h-4 text-purple-400" />;
        case 'approve': return <CheckCircle className="w-4 h-4 text-emerald-400" />;
        case 'reject': return <XCircle className="w-4 h-4 text-red-400" />;
        case 'login': return <LogIn className="w-4 h-4 text-text-muted" />;
        case 'update': return <RefreshCw className="w-4 h-4 text-amber-400" />;
        default: return <AlertCircle className="w-4 h-4 text-text-muted" />;
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-text-primary">Registro de Auditoría</h1>
        <p className="text-text-muted">Historial inmutable de todas las acciones en la plataforma.</p>
      </div>

      <div className="bg-bg-surface border border-border-default rounded-xl p-6 relative">
          <div className="absolute top-6 left-8 bottom-6 w-px bg-border-default"></div>
          
          <div className="space-y-8">
              {MOCK_AUDIT_LOGS.map((log) => (
                  <div key={log.id} className="relative pl-10 group">
                      {/* Dot */}
                      <div className="absolute left-[3px] top-1 w-2.5 h-2.5 rounded-full bg-bg-elevated border-2 border-text-muted group-hover:border-accent-info group-hover:bg-accent-info transition-colors z-10"></div>
                      
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between bg-bg-base/50 hover:bg-bg-elevated border border-transparent hover:border-border-default p-3 rounded-lg transition-all">
                          <div className="flex items-start gap-3">
                                <div className="mt-1 p-1.5 bg-bg-elevated rounded border border-border-subtle">
                                    {getIcon(log.action)}
                                </div>
                                <div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-semibold text-text-primary capitalize">{log.action}</span>
                                        <span className="text-xs text-text-muted px-1.5 py-0.5 rounded bg-bg-base border border-border-subtle">{log.entity}</span>
                                    </div>
                                    <p className="text-sm text-text-secondary mt-0.5">{log.details}</p>
                                    <p className="text-xs text-text-muted mt-1 font-mono">Actor: {log.actor}</p>
                                </div>
                          </div>
                          <div className="text-right mt-2 sm:mt-0">
                              <span className="text-xs font-mono text-text-muted">
                                  {new Date(log.timestamp).toLocaleString()}
                              </span>
                          </div>
                      </div>
                  </div>
              ))}
          </div>
      </div>
    </div>
  );
};

export default AuditPage;