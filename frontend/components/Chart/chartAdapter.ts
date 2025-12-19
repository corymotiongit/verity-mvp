
export interface ChartSpec {
    chart_type: 'bar' | 'line' | 'scatter' | 'stacked_bar' | 'heatmap' | 'treemap' | 'pie' | 'donut' | 'funnel' | 'forecast';
    title: string;
    subtitle?: string;
    x: { field: string; label: string; type: string };
    y: { field: string; label: string; type: string };
    series?: { field: string; label: string; type: string };
    format?: { type: string; unit?: string };
}

const VERITY_THEMES = {
    dark: {
        colors: {
            paper_bg: '#151931',
            plot_bg: '#151931',
            text: '#F2F2ED',
            muted_text: '#E9E9E1',
            grid: 'rgba(242,242,237,0.08)',
            line_color: 'rgba(242,242,237,0.18)',
            accent: '#00FFCC',
            secondary: '#3850A0',
            secondary_dark: '#2A407E',
        },
        colorway: ['#00FFCC', '#3850A0', '#2A407E', '#E9E9E1', '#F2F2ED']
    },
    light: {
        colors: {
            paper_bg: '#FFFFFF',
            plot_bg: '#FFFFFF',
            text: '#1F2937', // Gray 800
            muted_text: '#6B7280', // Gray 500
            grid: 'rgba(0,0,0,0.06)',
            line_color: 'rgba(0,0,0,0.1)',
            accent: '#0D9488', // Teal 600
            secondary: '#2563EB', // Blue 600
            secondary_dark: '#1E40AF', // Blue 800
        },
        colorway: ['#0D9488', '#2563EB', '#1E40AF', '#6B7280', '#1F2937']
    }
};

export function transformDataForPlotly(
    spec: ChartSpec,
    tableData: { columns: string[], rows: any[][] },
    mode: 'light' | 'dark' = 'light' // Default to light for broader compatibility
) {
    const theme = VERITY_THEMES[mode];

    if (!tableData || !tableData.columns || !tableData.rows || !spec) {
        return { data: [], layout: {} };
    }

    const colIdx = tableData.columns.reduce((acc, col, idx) => ({ ...acc, [col]: idx }), {} as Record<string, number>);

    const xIdx = colIdx[spec.x.field];
    const yIdx = colIdx[spec.y.field];
    const sIdx = spec.series ? colIdx[spec.series.field] : -1;

    if (xIdx === undefined || yIdx === undefined) {
        console.warn("Chart adapter: Columns not found in table data", spec.x.field, spec.y.field, tableData.columns);
        return { data: [], layout: {} };
    }

    // Forecast: expects a combined table with columns:
    // - time (spec.x.field)
    // - y (spec.y.field) for historical actuals (future rows may be null)
    // - y_hat, y_lo, y_hi for model output
    if (spec.chart_type === 'forecast') {
        const yHatIdx = colIdx['y_hat'];
        const yLoIdx = colIdx['y_lo'];
        const yHiIdx = colIdx['y_hi'];

        if (yHatIdx === undefined || yLoIdx === undefined || yHiIdx === undefined) {
            console.warn("Forecast chart requires y_hat/y_lo/y_hi columns", tableData.columns);
            return { data: [], layout: {} };
        }

        const historyX: any[] = [];
        const historyY: number[] = [];
        const futureX: any[] = [];
        const futureHat: number[] = [];
        const futureLo: number[] = [];
        const futureHi: number[] = [];

        const toNum = (v: any) => {
            if (v === null || v === undefined || v === '') return null;
            if (typeof v === 'number') return Number.isFinite(v) ? v : null;
            if (typeof v === 'string') {
                const n = parseFloat(v.replace(/[^0-9.-]+/g, ''));
                return Number.isFinite(n) ? n : null;
            }
            return null;
        };

        tableData.rows.forEach(row => {
            const xVal = row[xIdx];
            const actual = toNum(row[yIdx]);
            const hat = toNum(row[yHatIdx]);
            const lo = toNum(row[yLoIdx]);
            const hi = toNum(row[yHiIdx]);

            if (actual !== null) {
                historyX.push(xVal);
                historyY.push(actual);
            } else if (hat !== null && lo !== null && hi !== null) {
                futureX.push(xVal);
                futureHat.push(hat);
                futureLo.push(lo);
                futureHi.push(hi);
            }
        });

        // Confidence band: upper then lower with fill to next y
        const bandUpper: any = {
            type: 'scatter',
            mode: 'lines',
            x: futureX,
            y: futureHi,
            line: { color: 'rgba(0,0,0,0)' },
            hoverinfo: 'skip',
            showlegend: false,
        };

        const bandLower: any = {
            type: 'scatter',
            mode: 'lines',
            x: futureX,
            y: futureLo,
            fill: 'tonexty',
            fillcolor: mode === 'dark' ? 'rgba(0,255,204,0.12)' : 'rgba(13,148,136,0.12)',
            line: { color: 'rgba(0,0,0,0)' },
            name: 'Intervalo',
            hoverlabel: {
                bgcolor: theme.colors.secondary_dark,
                font: { color: theme.colors.text }
            },
            hovertemplate: `%{x}<br>Rango: %{y:.2f}<extra></extra>`,
        };

        const histTrace: any = {
            type: 'scatter',
            mode: 'lines+markers',
            x: historyX,
            y: historyY,
            name: 'Histórico',
            line: { color: theme.colors.secondary, width: 2 },
            marker: { color: theme.colors.secondary, size: 5 },
            hoverlabel: {
                bgcolor: theme.colors.secondary_dark,
                font: { color: theme.colors.text }
            },
        };

        const forecastTrace: any = {
            type: 'scatter',
            mode: 'lines',
            x: futureX,
            y: futureHat,
            name: 'Pronóstico',
            line: { color: theme.colors.accent, width: 2, dash: 'dash' },
            hoverlabel: {
                bgcolor: theme.colors.secondary_dark,
                font: { color: theme.colors.text }
            },
        };

        const layout = {
            title: {
                text: spec.title,
                font: { size: 16, color: theme.colors.text },
                x: 0
            },
            paper_bgcolor: theme.colors.paper_bg,
            plot_bgcolor: theme.colors.plot_bg,
            font: {
                color: theme.colors.text,
                size: 12
            },
            colorway: theme.colorway,
            margin: { l: 56, r: 24, t: 56, b: 56 },
            xaxis: {
                title: spec.x.label,
                automargin: true,
                showgrid: true,
                gridcolor: theme.colors.grid,
                zeroline: false,
                linecolor: theme.colors.line_color,
                tickfont: { color: theme.colors.muted_text },
            },
            yaxis: {
                title: spec.y.label,
                automargin: true,
                showgrid: true,
                gridcolor: theme.colors.grid,
                zeroline: false,
                linecolor: theme.colors.line_color,
                tickfont: { color: theme.colors.muted_text },
            },
            autosize: true,
            height: 400,
            showlegend: true,
            legend: {
                orientation: 'h',
                yanchor: 'bottom',
                y: 1.02,
                x: 0,
                font: { color: theme.colors.muted_text }
            }
        };

        return { data: [histTrace, bandUpper, bandLower, forecastTrace], layout };
    }

    // Heatmap (matrix): we use x as columns, series as rows, y as value
    // This keeps the backend schema simple (no explicit z axis).
    if (spec.chart_type === 'heatmap') {
        if (xIdx === undefined || yIdx === undefined || sIdx < 0) {
            console.warn("Heatmap requires x, y and series fields", spec);
            return { data: [], layout: {} };
        }

        const xLabels: string[] = [];
        const yLabels: string[] = [];
        const zMap: Record<string, Record<string, number>> = {};

        const ensure = (outer: string, inner: string) => {
            if (!zMap[outer]) zMap[outer] = {};
            if (zMap[outer][inner] === undefined) zMap[outer][inner] = 0;
        };

        tableData.rows.forEach(row => {
            const xLabel = String(row[xIdx]);
            const yLabel = String(row[sIdx]);
            let v: any = row[yIdx];
            if (typeof v === 'string') v = parseFloat(v.replace(/[^0-9.-]+/g, ''));
            const num = typeof v === 'number' && !Number.isNaN(v) ? v : 0;

            if (!xLabels.includes(xLabel)) xLabels.push(xLabel);
            if (!yLabels.includes(yLabel)) yLabels.push(yLabel);
            ensure(yLabel, xLabel);
            // if duplicates exist, sum them
            zMap[yLabel][xLabel] += num;
        });

        const z = yLabels.map(yl => xLabels.map(xl => zMap[yl]?.[xl] ?? 0));

        const trace: any = {
            type: 'heatmap',
            x: xLabels,
            y: yLabels,
            z,
            colorscale: mode === 'dark'
                ? [[0, 'rgba(0,255,204,0.08)'], [1, theme.colors.accent]]
                : [[0, 'rgba(37,99,235,0.08)'], [1, theme.colors.secondary]],
            hoverlabel: {
                bgcolor: theme.colors.secondary_dark,
                font: { color: theme.colors.text }
            },
            hovertemplate: `%{y}<br>%{x}<br>${spec.y.label}: %{z}<extra></extra>`,
        };

        const layout = {
            title: {
                text: spec.title,
                font: { size: 16, color: theme.colors.text },
                x: 0
            },
            paper_bgcolor: theme.colors.paper_bg,
            plot_bgcolor: theme.colors.plot_bg,
            font: {
                color: theme.colors.text,
                size: 12
            },
            margin: { l: 72, r: 24, t: 56, b: 56 },
            xaxis: {
                title: spec.x.label,
                automargin: true,
                showgrid: false,
                zeroline: false,
                tickfont: { color: theme.colors.muted_text },
            },
            yaxis: {
                title: spec.series?.label || 'Serie',
                automargin: true,
                showgrid: false,
                zeroline: false,
                tickfont: { color: theme.colors.muted_text },
            },
            autosize: true,
            height: 400,
        };

        return { data: [trace], layout };
    }

    // Treemap: x=label, y=value, series=parent (optional)
    if (spec.chart_type === 'treemap') {
        if (xIdx === undefined || yIdx === undefined) {
            console.warn("Treemap requires x and y fields", spec);
            return { data: [], layout: {} };
        }

        const labels: string[] = [];
        const parents: string[] = [];
        const values: number[] = [];

        tableData.rows.forEach(row => {
            const label = String(row[xIdx]);
            const parent = sIdx >= 0 ? String(row[sIdx]) : '';
            let v: any = row[yIdx];
            if (typeof v === 'string') v = parseFloat(v.replace(/[^0-9.-]+/g, ''));
            const num = typeof v === 'number' && !Number.isNaN(v) ? v : 0;

            labels.push(label);
            parents.push(parent);
            values.push(num);
        });

        const trace: any = {
            type: 'treemap',
            labels,
            parents,
            values,
            marker: {
                colors: values,
                colorscale: mode === 'dark'
                    ? [[0, 'rgba(0,255,204,0.10)'], [1, theme.colors.accent]]
                    : [[0, 'rgba(37,99,235,0.10)'], [1, theme.colors.secondary]],
                line: { width: 1, color: theme.colors.line_color }
            },
            textinfo: 'label+value',
            hoverlabel: {
                bgcolor: theme.colors.secondary_dark,
                font: { color: theme.colors.text }
            },
        };

        const layout = {
            title: {
                text: spec.title,
                font: { size: 16, color: theme.colors.text },
                x: 0
            },
            paper_bgcolor: theme.colors.paper_bg,
            plot_bgcolor: theme.colors.plot_bg,
            font: {
                color: theme.colors.text,
                size: 12
            },
            margin: { l: 24, r: 24, t: 56, b: 24 },
            autosize: true,
            height: 420,
        };

        return { data: [trace], layout };
    }

    // Funnel: categories on y, values on x
    if (spec.chart_type === 'funnel') {
        if (xIdx === undefined || yIdx === undefined) {
            console.warn("Funnel requires x and y fields", spec);
            return { data: [], layout: {} };
        }

        const labels: string[] = [];
        const values: number[] = [];
        tableData.rows.forEach(row => {
            const label = String(row[xIdx]);
            let v: any = row[yIdx];
            if (typeof v === 'string') v = parseFloat(v.replace(/[^0-9.-]+/g, ''));
            const num = typeof v === 'number' && !Number.isNaN(v) ? v : 0;
            labels.push(label);
            values.push(num);
        });

        const trace: any = {
            type: 'funnel',
            y: labels,
            x: values,
            textinfo: 'value+percent initial',
            marker: {
                color: theme.colors.accent,
                line: { width: 1, color: theme.colors.line_color }
            },
            hoverlabel: {
                bgcolor: theme.colors.secondary_dark,
                font: { color: theme.colors.text }
            },
        };

        const layout = {
            title: {
                text: spec.title,
                font: { size: 16, color: theme.colors.text },
                x: 0
            },
            paper_bgcolor: theme.colors.paper_bg,
            plot_bgcolor: theme.colors.plot_bg,
            font: {
                color: theme.colors.text,
                size: 12
            },
            margin: { l: 120, r: 24, t: 56, b: 24 },
            autosize: true,
            height: 420,
        };

        return { data: [trace], layout };
    }

    // Grouping
    const groups: Record<string, { x: any[], y: any[] }> = {};
    const seriesOrder: string[] = [];

    tableData.rows.forEach(row => {
        const seriesKey = sIdx >= 0 ? String(row[sIdx]) : 'Default';
        if (!groups[seriesKey]) {
            groups[seriesKey] = { x: [], y: [] };
            seriesOrder.push(seriesKey);
        }

        // Data Extraction
        let xVal = row[xIdx];
        let yVal = row[yIdx];

        // Ensure Y is numeric
        if (typeof yVal === 'string') {
            yVal = parseFloat(yVal.replace(/[^0-9.-]+/g, ''));
        }

        groups[seriesKey].x.push(xVal);
        groups[seriesKey].y.push(yVal);
    });

    // Auto-Orientation Logic: If many categories on X, swap to Horizontal Bar
    // (Only if simplistic bar chart)
    let isHorizontal = false;
    let categoryCount = 0;

    // Check first series X length (assuming all align)
    if (seriesOrder.length > 0) {
        categoryCount = groups[seriesOrder[0]].x.length;
    }

    if (spec.chart_type === 'bar' && categoryCount > 8) {
        isHorizontal = true;
    }

    // Generate traces
    const traces = seriesOrder.map(name => {
        const data = groups[name];

        // Swap for horizontal bar charts
        const x = isHorizontal ? data.y : data.x;
        const y = isHorizontal ? data.x : data.y;

        // Pie/Donut is a single-trace chart in our adapter.
        if (spec.chart_type === 'pie' || spec.chart_type === 'donut') {
            if (name !== seriesOrder[0]) return null;
            return {
                type: 'pie',
                labels: data.x,
                values: data.y,
                hole: spec.chart_type === 'donut' ? 0.45 : 0,
                hoverlabel: {
                    bgcolor: theme.colors.secondary_dark,
                    font: { color: theme.colors.text }
                },
            };
        }

        let type = 'bar';
        let scatterMode: string | undefined;
        let orientation: 'h' | 'v' | undefined = isHorizontal ? 'h' : 'v';

        if (spec.chart_type === 'line') {
            type = 'scatter';
            scatterMode = 'lines+markers';
            orientation = undefined;
        } else if (spec.chart_type === 'scatter') {
            type = 'scatter';
            scatterMode = 'markers';
            orientation = undefined;
        }

        const trace: any = {
            x,
            y,
            name: name === 'Default' ? spec.y.label : name,
            type,
            orientation,
            hoverlabel: {
                bgcolor: theme.colors.secondary_dark,
                font: { color: theme.colors.text }
            }
        };

        if (scatterMode) trace.mode = scatterMode;

        // Formatting
        if (spec.format?.type === 'currency' && !isHorizontal) {
            trace.texttemplate = '%{y:$.2s}';
            trace.hovertemplate = '%{x}<br>%{y:$,.2f}';
        } else if (spec.format?.type === 'currency' && isHorizontal) {
            trace.texttemplate = '%{x:$.2s}';
            trace.hovertemplate = '%{y}<br>%{x:$,.2f}';
        }

        return trace;
    }).filter(Boolean);

    // Layout
    const layout = {
        title: {
            text: spec.title,
            font: { size: 16, color: theme.colors.text },
            x: 0
        },
        paper_bgcolor: theme.colors.paper_bg,
        plot_bgcolor: theme.colors.plot_bg,
        font: {
            color: theme.colors.text,
            size: 12
        },
        colorway: theme.colorway,
        margin: { l: 56, r: 24, t: 56, b: 56 },
        xaxis: {
            title: isHorizontal ? spec.y.label : spec.x.label,
            automargin: true,
            showgrid: true,
            gridcolor: theme.colors.grid,
            zeroline: false,
            linecolor: theme.colors.line_color,
            tickfont: { color: theme.colors.muted_text },
            tickformat: (isHorizontal && spec.format?.type === 'currency') ? '$.2s' : undefined
        },
        yaxis: {
            title: isHorizontal ? spec.x.label : spec.y.label,
            automargin: true,
            showgrid: true,
            gridcolor: theme.colors.grid,
            zeroline: false,
            linecolor: theme.colors.line_color,
            tickfont: { color: theme.colors.muted_text },
            tickformat: (!isHorizontal && spec.format?.type === 'currency') ? '$.2s' : undefined
        },
        barmode: spec.chart_type === 'stacked_bar' ? 'stack' : 'group',
        autosize: true,
        height: 400,
        showlegend: sIdx >= 0,
        legend: {
            orientation: "h",
            yanchor: "bottom",
            y: 1.02,
            x: 0,
            font: { color: theme.colors.muted_text }
        }
    };

    return { data: traces as any[], layout };
}
