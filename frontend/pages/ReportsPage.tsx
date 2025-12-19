import React, { useState } from 'react';
import { MOCK_REPORTS } from '../constants';
import { Report } from '../types';
import { FileText, ChevronRight, BarChart2, Download, Share2 } from 'lucide-react';

const ReportsPage: React.FC = () => {
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);

  return (
    <div className="flex h-full">
        {/* Reports List */}
        <div className={`${selectedReport ? 'hidden lg:flex lg:w-1/3' : 'w-full'} flex-col border-r border-border-default bg-bg-base`}>
            <div className="p-6 border-b border-border-default">
                <h1 className="text-2xl font-bold text-text-primary">Reportes</h1>
                <p className="text-text-muted text-sm mt-1">Análisis generados por Veri</p>
            </div>
            <div className="flex-1 overflow-y-auto">
                {MOCK_REPORTS.map(report => (
                    <div 
                        key={report.id}
                        onClick={() => setSelectedReport(report)}
                        className={`p-4 border-b border-border-subtle cursor-pointer hover:bg-bg-hover transition-colors ${
                            selectedReport?.id === report.id ? 'bg-bg-active' : ''
                        }`}
                    >
                        <div className="flex justify-between items-start mb-1">
                            <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                                report.type === 'financial' ? 'bg-emerald-500/10 text-emerald-500' :
                                report.type === 'analysis' ? 'bg-blue-500/10 text-blue-500' :
                                'bg-purple-500/10 text-purple-500'
                            }`}>
                                {report.type}
                            </span>
                            <span className="text-xs text-text-muted">{new Date(report.created_at).toLocaleDateString()}</span>
                        </div>
                        <h3 className="text-sm font-semibold text-text-primary">{report.title}</h3>
                        <p className="text-xs text-text-secondary mt-1">Por {report.author}</p>
                    </div>
                ))}
            </div>
        </div>

        {/* Report Content */}
        <div className={`${selectedReport ? 'flex' : 'hidden lg:flex'} flex-1 flex-col bg-bg-surface overflow-hidden`}>
            {selectedReport ? (
                <>
                    <div className="h-16 border-b border-border-default flex items-center justify-between px-6 bg-bg-base/50 backdrop-blur">
                        <button onClick={() => setSelectedReport(null)} className="lg:hidden text-text-muted mr-2">
                            ← Volver
                        </button>
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-bg-elevated rounded text-text-primary">
                                <FileText className="w-5 h-5" />
                            </div>
                            <div>
                                <h2 className="text-sm font-bold text-text-primary">{selectedReport.title}</h2>
                                <p className="text-xs text-text-muted">ID: {selectedReport.id}</p>
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <button className="p-2 text-text-muted hover:text-text-primary hover:bg-bg-elevated rounded-lg transition-colors">
                                <Share2 className="w-4 h-4" />
                            </button>
                            <button className="p-2 text-text-muted hover:text-accent-success hover:bg-bg-elevated rounded-lg transition-colors">
                                <Download className="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-8 max-w-4xl mx-auto w-full space-y-8">
                        {/* Mock Chart Visualization */}
                        {selectedReport.chart_data && (
                            <div className="bg-bg-elevated border border-border-default rounded-xl p-6 shadow-sm">
                                <div className="flex items-center justify-between mb-6">
                                    <h4 className="text-sm font-medium text-text-secondary flex items-center gap-2">
                                        <BarChart2 className="w-4 h-4" /> Visualización de Datos
                                    </h4>
                                </div>
                                {/* Simulated Chart Bars */}
                                <div className="h-48 flex items-end justify-around gap-4 px-4 pb-2 border-b border-border-subtle">
                                    {selectedReport.chart_data.values.map((v: any, i: number) => (
                                        <div key={i} className="flex flex-col items-center gap-2 w-full group">
                                            <div 
                                                className="w-full bg-accent-info/20 border-t border-x border-accent-info/30 rounded-t-sm group-hover:bg-accent-info/40 transition-all relative"
                                                style={{ height: `${(v.y / 200) * 100}%` }}
                                            >
                                                <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs font-bold text-text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                                                    {v.y}
                                                </span>
                                            </div>
                                            <span className="text-xs text-text-muted">{v.x}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Content */}
                        <div className="prose prose-invert prose-sm max-w-none">
                            <div className="whitespace-pre-wrap font-sans text-text-secondary leading-relaxed">
                                {selectedReport.content}
                            </div>
                            
                            <hr className="border-border-default my-8" />
                            
                            <div className="bg-bg-base p-4 rounded-lg border border-border-subtle text-xs text-text-muted">
                                Este reporte fue generado automáticamente por Verity AI basado en los documentos disponibles hasta la fecha {new Date(selectedReport.created_at).toLocaleDateString()}.
                            </div>
                        </div>
                    </div>
                </>
            ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-text-muted p-8 text-center">
                    <div className="w-16 h-16 bg-bg-elevated rounded-full flex items-center justify-center mb-4">
                        <BarChart2 className="w-8 h-8 opacity-50" />
                    </div>
                    <h3 className="text-lg font-medium text-text-primary">Selecciona un reporte</h3>
                    <p className="max-w-xs mt-2">Explora los análisis financieros, de riesgos y cumplimiento generados.</p>
                </div>
            )}
        </div>
    </div>
  );
};

export default ReportsPage;