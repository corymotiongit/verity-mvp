import React, { useMemo, useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Table as TableIcon } from 'lucide-react';
import createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';
import { transformDataForPlotly, ChartSpec } from './chartAdapter';
import { useTheme } from '../../services/useTheme';

const Plot = createPlotlyComponent(Plotly);

interface PlotlyChartProps {
    chartSpec: { type: string; spec: ChartSpec } | null;
    tableSource: { columns: string[]; rows: any[][]; total_rows?: number } | null;
    evidenceRef?: string;
}

// Helper Component for Table (defined before use to avoid hoisting issues if any)
const SourceTable = ({ data }: { data: { columns: string[]; rows: any[][]; total_rows?: number } }) => (
    <div className="overflow-x-auto rounded border border-border-subtle bg-bg-base">
        <table className="w-full text-left text-xs text-text-secondary">
            <thead className="bg-bg-elevated text-text-primary font-semibold border-b border-border-subtle">
                <tr>
                    {data.columns.map((col, i) => <th key={i} className="p-2 whitespace-nowrap border-r last:border-0 border-border-subtle">{col}</th>)}
                </tr>
            </thead>
            <tbody>
                {data.rows.slice(0, 5).map((row, i) => ( // Show top 5 by default
                    <tr key={i} className="hover:bg-bg-hover border-b last:border-0 border-border-subtle">
                        {row.map((cell: any, j: number) => (
                            <td key={j} className="p-2 truncate max-w-[150px] border-r last:border-0 border-border-subtle font-mono text-text-secondary">
                                {typeof cell === 'object' && cell !== null ? JSON.stringify(cell) : String(cell)}
                            </td>
                        ))}
                    </tr>
                ))}
            </tbody>
        </table>
        {data.rows.length > 5 && (
            <div className="p-1.5 text-center text-[10px] text-text-muted bg-bg-elevated border-t border-border-subtle">
                Mostrando 5 de {data.total_rows || data.rows.length} filas
            </div>
        )}
    </div>
);

export const PlotlyChart: React.FC<PlotlyChartProps> = ({ chartSpec, tableSource, evidenceRef }) => {
    const [showAudit, setShowAudit] = useState(false);
    const theme = useTheme();

    const isForecast = !!(chartSpec && chartSpec.type === 'plotly' && chartSpec.spec?.chart_type === 'forecast');
    const [tableView, setTableView] = useState<'forecast' | 'history' | 'all'>('forecast');

    useEffect(() => {
        // Default to Forecast view only for forecast charts; otherwise show all.
        setTableView(isForecast ? 'forecast' : 'all');
    }, [isForecast]);

    const tableForView = useMemo(() => {
        if (!tableSource) return null;
        if (!isForecast) return tableSource;

        const cols = tableSource.columns || [];
        const rows = tableSource.rows || [];
        const idx = (name: string) => cols.indexOf(name);

        const iTime = idx('time');
        const iY = idx('y');
        const iHat = idx('y_hat');
        const iLo = idx('y_lo');
        const iHi = idx('y_hi');

        if (iTime < 0 || iHat < 0) return tableSource;

        const isEmpty = (v: any) => v === null || v === undefined || v === '';

        const pickCols = (names: string[]) => {
            const picked = names.filter(n => cols.includes(n));
            const pickedIdxs = picked.map(n => cols.indexOf(n));
            const pickedRows = rows.map(r => pickedIdxs.map(j => (j >= 0 ? r[j] : null)));
            return { columns: picked, rows: pickedRows };
        };

        if (tableView === 'all') {
            return { ...tableSource, total_rows: rows.length };
        }

        // History rows: y present
        // Forecast rows: y empty, but y_hat present. (Interval applies only here.)
        const filtered = rows.filter(r => {
            const yVal = iY >= 0 ? r[iY] : null;
            const hatVal = r[iHat];
            if (tableView === 'history') return !isEmpty(yVal);
            return isEmpty(yVal) && !isEmpty(hatVal);
        });

        if (tableView === 'history') {
            const subset = pickCols(['time', 'y', 'y_hat']);
            return {
                columns: subset.columns,
                rows: filtered.map(r => subset.columns.map(c => r[cols.indexOf(c)])),
                total_rows: filtered.length,
            };
        }

        // forecast
        const subset = pickCols(['time', 'y_hat', 'y_lo', 'y_hi']);
        return {
            columns: subset.columns,
            rows: filtered.map(r => subset.columns.map(c => r[cols.indexOf(c)])),
            total_rows: filtered.length,
        };
    }, [tableSource, isForecast, tableView]);

    const plotData = useMemo(() => {
        if (!chartSpec || chartSpec.type !== 'plotly' || !tableSource) return null;
        try {
            return transformDataForPlotly(chartSpec.spec, tableSource, theme);
        } catch (e) {
            console.error("Failed to transform chart data", e);
            return null;
        }
    }, [chartSpec, tableSource, theme]);

    if (!chartSpec || chartSpec.type !== 'plotly') return null;

    // Rule: No Graph without Table
    if (!tableSource) {
        return (
            <div className="p-3 text-xs text-text-muted italic border border-border-subtle rounded bg-bg-elevated">
                Gráfica no disponible (faltan datos fuente).
            </div>
        );
    }

    // Chart Error Fallback
    if (!plotData || plotData.data.length === 0) {
        return (
            <div className="flex flex-col gap-4 my-2 p-3 border border-border-default rounded bg-bg-surface">
                <div className="text-sm text-text-primary font-medium">
                    No se pudo renderizar la gráfica. Mostrando datos fuente:
                </div>
                <SourceTable data={tableSource} />
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6 my-4 p-5 border border-border-default rounded-lg bg-bg-surface shadow-sm">
            {/* Chart Area */}
            <div className="w-full h-[400px] min-h-[400px]">
                <Plot
                    data={plotData.data}
                    layout={{
                        ...plotData.layout,
                        autosize: true,
                        margin: { l: 60, r: 20, t: 40, b: 60 },
                    }}
                    useResizeHandler={true}
                    style={{ width: '100%', height: '100%' }}
                    config={{ responsive: true, displayModeBar: false }}
                />
            </div>

            {isForecast && (
                <div className="-mt-3 text-xs text-text-muted">
                    El intervalo aplica solo al pronóstico
                </div>
            )}

            {/* Always Visible Source Table (Audit) */}
            <div className="border-t border-border-subtle pt-4">
                <div className="mb-2 flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider flex items-center gap-2">
                        <TableIcon size={14} /> Fuente de Datos
                    </h4>

                    {isForecast && (
                        <div className="flex items-center gap-1">
                            <button
                                onClick={() => setTableView('history')}
                                className={`text-xs px-2 py-1 rounded border transition-colors ${tableView === 'history' ? 'bg-bg-active text-text-primary border-border-default' : 'bg-bg-base text-text-muted border-border-subtle hover:text-text-primary'}`}
                            >
                                Histórico
                            </button>
                            <button
                                onClick={() => setTableView('forecast')}
                                className={`text-xs px-2 py-1 rounded border transition-colors ${tableView === 'forecast' ? 'bg-bg-active text-text-primary border-border-default' : 'bg-bg-base text-text-muted border-border-subtle hover:text-text-primary'}`}
                            >
                                Forecast
                            </button>
                            <button
                                onClick={() => setTableView('all')}
                                className={`text-xs px-2 py-1 rounded border transition-colors ${tableView === 'all' ? 'bg-bg-active text-text-primary border-border-default' : 'bg-bg-base text-text-muted border-border-subtle hover:text-text-primary'}`}
                            >
                                Todo
                            </button>
                        </div>
                    )}
                </div>
                <SourceTable data={tableForView || tableSource} />
            </div>

            {/* Collapsible Evidence Ref */}
            <div className="border-t border-border-subtle pt-2">
                <button
                    onClick={() => setShowAudit(!showAudit)}
                    className="flex items-center gap-2 text-xs text-text-muted hover:text-text-primary transition-colors w-full py-1 text-left"
                >
                    {showAudit ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    {showAudit ? "Ocultar detalles de auditoría" : "Ver detalles de auditoría (Evidence Ref)"}
                </button>

                {showAudit && evidenceRef && (
                    <div className="mt-3 p-3 bg-bg-elevated rounded text-xs font-mono text-text-secondary border border-border-subtle break-all">
                        <span className="font-semibold block mb-1 text-text-primary">EVIDENCE_REF:</span>
                        {evidenceRef}
                    </div>
                )}
            </div>
        </div>
    );
};
