import React, { useState } from 'react';
import { MOCK_APPROVALS } from '../constants';
import { ApprovalRequest, FieldChange } from '../types';
import { X, Check, ArrowRight, AlertCircle, Clock } from 'lucide-react';

const ApprovalsPage: React.FC = () => {
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);

  return (
    <div className="flex h-full">
        {/* List View */}
        <div className="flex-1 p-8 space-y-8 overflow-y-auto">
            <div className="flex flex-col gap-2">
                <h1 className="text-2xl font-bold text-text-primary">Aprobaciones Pendientes</h1>
                <p className="text-text-muted">Revisa y aprueba cambios propuestos por el agente o usuarios.</p>
            </div>

            <div className="grid gap-4">
                {MOCK_APPROVALS.map(approval => (
                    <div 
                        key={approval.id}
                        onClick={() => setSelectedApproval(approval)}
                        className={`bg-bg-surface border border-border-default p-4 rounded-xl cursor-pointer transition-all hover:border-text-muted group ${
                            selectedApproval?.id === approval.id ? 'border-accent-info shadow-sm' : ''
                        }`}
                    >
                        <div className="flex justify-between items-start">
                            <div className="flex items-center gap-3">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                                    approval.status === 'pending' ? 'bg-amber-500/10 text-amber-500' : 'bg-bg-elevated'
                                }`}>
                                    <Clock className="w-5 h-5" />
                                </div>
                                <div>
                                    <h3 className="text-sm font-semibold text-text-primary group-hover:text-accent-info transition-colors">
                                        {approval.reason}
                                    </h3>
                                    <p className="text-xs text-text-muted mt-0.5">
                                        {approval.entity_type}: <span className="text-text-secondary">{approval.entity_name}</span>
                                    </p>
                                </div>
                            </div>
                            <span className="text-xs text-text-muted bg-bg-elevated px-2 py-1 rounded">
                                {new Date(approval.created_at).toLocaleDateString()}
                            </span>
                        </div>
                        <div className="mt-4 pl-13 flex gap-2">
                            {approval.changes.map((change, idx) => (
                                <span key={idx} className="text-[10px] px-2 py-1 bg-bg-elevated border border-border-subtle rounded text-text-secondary">
                                    {change.field_name}
                                </span>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>

        {/* Detail View */}
        {selectedApproval && (
            <div className="w-96 border-l border-border-default bg-bg-surface flex flex-col h-full shadow-2xl animate-in slide-in-from-right duration-300">
                <div className="p-4 border-b border-border-default flex items-center justify-between">
                    <span className="font-semibold text-text-primary">Detalle de Aprobación</span>
                    <button onClick={() => setSelectedApproval(null)} className="text-text-muted hover:text-text-primary p-1 rounded-md hover:bg-bg-hover">
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    <div className="bg-bg-elevated p-4 rounded-lg border border-border-subtle space-y-2">
                        <div className="flex justify-between">
                            <span className="text-xs text-text-muted uppercase">Solicitado por</span>
                            <span className="text-xs text-text-primary">{selectedApproval.requested_by}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-xs text-text-muted uppercase">Entidad</span>
                            <span className="text-xs text-text-primary">{selectedApproval.entity_name}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-xs text-text-muted uppercase">ID</span>
                            <span className="text-xs font-mono text-text-secondary">{selectedApproval.entity_id}</span>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <h4 className="text-sm font-medium text-text-primary flex items-center gap-2">
                            Cambios Propuestos <span className="bg-bg-elevated text-text-muted px-1.5 py-0.5 rounded text-[10px]">{selectedApproval.changes.length}</span>
                        </h4>
                        
                        {selectedApproval.changes.map((change, idx) => (
                            <div key={idx} className="border border-border-default rounded-lg overflow-hidden">
                                <div className="bg-bg-elevated px-3 py-2 border-b border-border-subtle flex justify-between items-center">
                                    <span className="text-xs font-mono text-text-secondary">{change.field_name}</span>
                                    <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                                </div>
                                <div className="p-3 space-y-3 bg-bg-base/50">
                                    <div className="grid grid-cols-[1fr,auto,1fr] gap-2 items-center text-sm">
                                        <div className="bg-red-500/5 text-red-400 p-2 rounded border border-red-500/10 text-center line-through decoration-red-500/50">
                                            {String(change.old_value)}
                                        </div>
                                        <ArrowRight className="w-4 h-4 text-text-muted" />
                                        <div className="bg-emerald-500/5 text-emerald-400 p-2 rounded border border-emerald-500/10 text-center font-medium">
                                            {String(change.new_value)}
                                        </div>
                                    </div>
                                    
                                    <div className="flex gap-2 pt-2">
                                        <button className="flex-1 py-1.5 bg-bg-surface hover:bg-emerald-500/10 hover:text-emerald-500 border border-border-default rounded text-xs font-medium transition-colors flex justify-center items-center gap-1">
                                            <Check className="w-3 h-3" /> Aprobar
                                        </button>
                                        <button className="flex-1 py-1.5 bg-bg-surface hover:bg-red-500/10 hover:text-red-500 border border-border-default rounded text-xs font-medium transition-colors flex justify-center items-center gap-1">
                                            <X className="w-3 h-3" /> Rechazar
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-medium text-text-secondary">Comentario (Opcional)</label>
                        <textarea className="w-full bg-bg-base border border-border-default rounded-lg p-2 text-sm text-text-primary focus:outline-none focus:border-text-muted resize-none h-20" placeholder="Razón de la aprobación/rechazo..."></textarea>
                    </div>
                </div>
                
                <div className="p-4 border-t border-border-default">
                    <button className="w-full py-2 bg-accent-success hover:bg-accent-success-hover text-bg-base font-bold rounded-lg shadow-glow-success transition-all">
                        Aplicar Cambios Aprobados
                    </button>
                </div>
            </div>
        )}
    </div>
  );
};

export default ApprovalsPage;