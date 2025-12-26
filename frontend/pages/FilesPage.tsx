import React, { useState, useEffect } from 'react';
import FileDropzone, { FileMetadata } from '../components/FileDropzone';
import { formatBytes } from '../constants';
import { VerityDocument } from '../types';
import { documentsApi, DocumentResponse, queryV2Api } from '../services/api';
import { FileText, Image as ImageIcon, FileSpreadsheet, MoreVertical, Search, Filter, X, Eye, RefreshCw, Trash2, Loader2 } from 'lucide-react';

// Convert API response to frontend type
const toVerityDocument = (doc: DocumentResponse): VerityDocument => ({
    id: doc.id,
    display_name: doc.display_name,
    mime_type: doc.mime_type,
    size_bytes: doc.size_bytes,
    status: doc.status,
    created_at: doc.created_at,
    metadata: doc.metadata || undefined,
});

const FilesPage: React.FC = () => {
    const [documents, setDocuments] = useState<VerityDocument[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState('Todos');
    const [selectedDoc, setSelectedDoc] = useState<VerityDocument | null>(null);
    const [uploading, setUploading] = useState(false);
    const [storeInfo, setStoreInfo] = useState<{
        store_id: string | null;
        document_count: number;
    } | null>(null);

    // Summary generation state
    const [generatingSummary, setGeneratingSummary] = useState(false);
    const [summaries, setSummaries] = useState<Record<string, string>>({});

    // Fetch documents and store info from API
    const fetchDocuments = async () => {
        setLoading(true);
        setError(null);

        try {
            // 1. Fetch documents (Required)
            const docsResponse = await documentsApi.list(50);
            setDocuments(docsResponse.items.map(toVerityDocument));

            // 2. Fetch store info (Optional - non blocking)
            try {
                const storeResponse = await documentsApi.getStoreInfo();
                setStoreInfo({
                    store_id: storeResponse.store_id,
                    document_count: storeResponse.document_count,
                });
            } catch (storeErr) {
                console.warn('Store info fetch failed (ignoring):', storeErr);
                // Don't set global error, just leave storeInfo null or stale
            }

        } catch (err) {
            console.error('Failed to fetch documents:', err);
            const message = err instanceof Error ? err.message : String(err);
            setError(`Error al cargar documentos: ${message}`);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDocuments();
    }, []);

    const handleFilesAccepted = async (newFiles: File[], metadata: FileMetadata) => {
        setUploading(true);
        setError(null); // Clear previous errors
        try {
            for (const file of newFiles) {
                // Build metadata for File Search store
                const uploadMetadata: Record<string, any> = {};
                if (metadata.category) uploadMetadata.category = metadata.category;
                if (metadata.project) uploadMetadata.project = metadata.project;
                if (metadata.tags?.length) uploadMetadata.tags = metadata.tags.join(',');

                const uploaded = await documentsApi.upload(
                    file,
                    undefined,
                    Object.keys(uploadMetadata).length > 0 ? uploadMetadata : undefined
                );
                setDocuments(prev => [toVerityDocument(uploaded), ...prev]);
            }
            // Refresh store info quietly
            try {
                const storeResponse = await documentsApi.getStoreInfo();
                setStoreInfo({
                    store_id: storeResponse.store_id,
                    document_count: storeResponse.document_count,
                });
            } catch (ignore) { }

        } catch (err) {
            console.error('Upload failed:', err);
            const message = err instanceof Error ? err.message : String(err);
            setError(`Error al subir archivo: ${message}`);
        } finally {
            setUploading(false);
        }
    };

    const handleDelete = async (docId: string) => {
        try {
            await documentsApi.delete(docId);
            setDocuments(prev => prev.filter(d => d.id !== docId));
            if (selectedDoc?.id === docId) setSelectedDoc(null);

            // Refresh store info after delete
            const storeResponse = await documentsApi.getStoreInfo();
            setStoreInfo({
                store_id: storeResponse.store_id,
                document_count: storeResponse.document_count,
            });
        } catch (err) {
            console.error('Delete failed:', err);
            setError('Error al eliminar documento.');
        }
    };

    const handleGenerateSummary = async (doc: VerityDocument) => {
        if (generatingSummary) return;

        setGeneratingSummary(true);
        try {
            const response = await queryV2Api.query(
                `Genera un resumen completo del documento "${doc.display_name}". Incluye:
1. Tipo de documento
2. Puntos clave o temas principales
3. Fechas importantes si las hay
4. Personas o entidades mencionadas
5. Conclusiones o acciones requeridas`,
                {
                    // Best-effort: el backend v2 puede ignorar esto hoy.
                    document: {
                        id: doc.id,
                        display_name: doc.display_name,
                        mime_type: doc.mime_type,
                        created_at: doc.created_at,
                    },
                }
            );

            setSummaries(prev => ({
                ...prev,
                [doc.id]: response.response,
            }));
        } catch (err) {
            console.error('Summary generation failed:', err);
            setError('Error al generar resumen.');
        } finally {
            setGeneratingSummary(false);
        }
    };

    const getFileIcon = (mimeType: string, className: string = "") => {
        if (mimeType.includes('pdf')) return <FileText className={`text-red-400 ${className}`} />;
        if (mimeType.includes('image')) return <ImageIcon className={`text-purple-400 ${className}`} />;
        if (mimeType.includes('sheet') || mimeType.includes('csv')) return <FileSpreadsheet className={`text-green-400 ${className}`} />;
        return <FileText className={`text-text-muted ${className}`} />;
    };

    const getStatusPill = (status: string) => {
        const styles = {
            ready: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
            processing: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
            failed: 'bg-red-500/10 text-red-500 border-red-500/20'
        };
        const labels = {
            ready: 'Listo',
            processing: 'Procesando',
            failed: 'Error'
        }
        const s = status as keyof typeof styles;
        return (
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wide border ${styles[s]}`}>
                {labels[s] || status}
            </span>
        );
    };

    const filteredDocuments = documents.filter(doc => {
        if (filter === 'Todos') return true;
        if (filter === 'Documentos') return doc.mime_type.includes('pdf') || doc.mime_type.includes('word');
        if (filter === 'Hojas de Cálculo') return doc.mime_type.includes('sheet') || doc.mime_type.includes('csv');
        if (filter === 'Imágenes') return doc.mime_type.includes('image');
        return true;
    });

    return (
        <div className="flex h-full">
            {/* Main Content */}
            <div className="flex-1 p-8 space-y-8 overflow-y-auto">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div className="flex flex-col gap-2">
                        <h1 className="text-2xl font-bold text-text-primary">Archivos</h1>
                        <p className="text-text-muted">Gestiona los documentos y activos de tu organización.</p>
                    </div>

                    {/* Store Status Indicator */}
                    {storeInfo && (
                        <div className="flex items-center gap-3 px-4 py-2 bg-bg-surface border border-border-default rounded-lg">
                            <div className={`w-2 h-2 rounded-full ${storeInfo.store_id ? 'bg-accent-success animate-pulse' : 'bg-text-muted'}`} />
                            <div className="text-xs">
                                <div className="text-text-primary font-medium">
                                    {storeInfo.store_id ? 'File Search Activo' : 'Sin Store'}
                                </div>
                                <div className="text-text-muted">
                                    {storeInfo.document_count} docs indexados en Google
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {error && (
                    <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-sm flex items-center justify-between">
                        <span>{error}</span>
                        <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                )}

                <div className="bg-bg-surface p-6 rounded-xl border border-border-default">
                    <h2 className="text-sm font-semibold text-text-primary mb-4">
                        {uploading ? 'Subiendo...' : 'Subir Nuevos Documentos'}
                    </h2>
                    <FileDropzone onFilesAccepted={handleFilesAccepted} />
                </div>

                <div className="space-y-4">
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                        <div className="flex items-center space-x-2 bg-bg-elevated p-1 rounded-lg border border-border-subtle overflow-x-auto">
                            {['Todos', 'Documentos', 'Hojas de Cálculo', 'Imágenes'].map(tab => (
                                <button
                                    key={tab}
                                    onClick={() => setFilter(tab)}
                                    className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all whitespace-nowrap ${filter === tab
                                        ? 'bg-bg-active text-text-primary shadow-sm'
                                        : 'text-text-muted hover:text-text-primary'
                                        }`}
                                >
                                    {tab}
                                </button>
                            ))}
                        </div>

                        <div className="flex items-center gap-2 w-full sm:w-auto">
                            <div className="relative flex-1 sm:flex-initial">
                                <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
                                <input
                                    type="text"
                                    placeholder="Filtrar archivos..."
                                    className="w-full pl-9 pr-3 py-1.5 bg-bg-surface border border-border-default rounded-lg text-sm text-text-primary focus:border-accent-success focus:outline-none"
                                />
                            </div>
                            <button className="p-2 border border-border-default rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-surface">
                                <Filter className="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    <div className="bg-bg-surface border border-border-default rounded-xl overflow-hidden shadow-sm">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-border-default bg-bg-elevated/50">
                                    <th className="py-3 px-4 w-12 text-center"><input type="checkbox" className="rounded border-border-default bg-bg-base" /></th>
                                    <th className="py-3 px-4 text-xs font-semibold text-text-secondary uppercase tracking-wider">Nombre</th>
                                    <th className="py-3 px-4 text-xs font-semibold text-text-secondary uppercase tracking-wider">Tipo</th>
                                    <th className="py-3 px-4 text-xs font-semibold text-text-secondary uppercase tracking-wider">Tamaño</th>
                                    <th className="py-3 px-4 text-xs font-semibold text-text-secondary uppercase tracking-wider">Fecha</th>
                                    <th className="py-3 px-4 text-xs font-semibold text-text-secondary uppercase tracking-wider">Estado</th>
                                    <th className="py-3 px-4 w-12"></th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border-subtle">
                                {loading ? (
                                    <tr>
                                        <td colSpan={7} className="py-12 text-center text-text-muted">
                                            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-accent-info" />
                                            Cargando documentos...
                                        </td>
                                    </tr>
                                ) : filteredDocuments.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="py-12 text-center text-text-muted">
                                            No se encontraron archivos. Sube tu primer documento.
                                        </td>
                                    </tr>
                                ) : (
                                    filteredDocuments.map((doc) => (
                                        <tr
                                            key={doc.id}
                                            className={`group hover:bg-bg-hover transition-colors cursor-pointer ${selectedDoc?.id === doc.id ? 'bg-bg-active' : ''}`}
                                            onClick={() => setSelectedDoc(doc)}
                                        >
                                            <td className="py-3 px-4 text-center" onClick={(e) => e.stopPropagation()}>
                                                <input type="checkbox" className="rounded border-border-default bg-bg-base cursor-pointer" />
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="p-2 bg-bg-elevated rounded border border-border-subtle">
                                                        {getFileIcon(doc.mime_type)}
                                                    </div>
                                                    <span className="font-medium text-text-primary text-sm group-hover:text-accent-info transition-colors">
                                                        {doc.display_name}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="py-3 px-4">
                                                <span className="px-2 py-1 bg-bg-elevated rounded text-xs text-text-secondary font-mono">
                                                    {doc.mime_type.split('/')[1]?.toUpperCase().split('.')[0] || 'FILE'}
                                                </span>
                                            </td>
                                            <td className="py-3 px-4 text-sm text-text-secondary font-mono">
                                                {formatBytes(doc.size_bytes)}
                                            </td>
                                            <td className="py-3 px-4 text-sm text-text-secondary">
                                                {new Date(doc.created_at).toLocaleDateString()}
                                            </td>
                                            <td className="py-3 px-4">
                                                {getStatusPill(doc.status)}
                                            </td>
                                            <td className="py-3 px-4 text-center">
                                                <button className="text-text-muted hover:text-text-primary p-1 rounded hover:bg-bg-active">
                                                    <MoreVertical className="w-4 h-4" />
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Detail Drawer */}
            {selectedDoc && (
                <div className="w-80 border-l border-border-default bg-bg-surface flex flex-col h-full shadow-2xl animate-in slide-in-from-right duration-300">
                    <div className="p-4 border-b border-border-default flex items-center justify-between">
                        <span className="font-semibold text-text-primary">Detalles</span>
                        <button onClick={() => setSelectedDoc(null)} className="text-text-muted hover:text-text-primary p-1 rounded-md hover:bg-bg-hover">
                            <X className="w-4 h-4" />
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-6">
                        <div className="flex flex-col items-center p-6 bg-bg-elevated rounded-xl border border-border-subtle">
                            <div className="p-4 bg-bg-base rounded-lg mb-3 shadow-inner">
                                {getFileIcon(selectedDoc.mime_type, "w-12 h-12")}
                            </div>
                            <h3 className="text-center font-medium text-text-primary break-all">{selectedDoc.display_name}</h3>
                            <div className="mt-2">{getStatusPill(selectedDoc.status)}</div>
                        </div>

                        <div className="space-y-3">
                            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">Metadatos</h4>
                            <div className="grid grid-cols-2 gap-3 text-sm">
                                <div className="text-text-secondary">Tipo</div>
                                <div className="text-text-primary text-right truncate" title={selectedDoc.mime_type}>{selectedDoc.mime_type}</div>

                                <div className="text-text-secondary">Tamaño</div>
                                <div className="text-text-primary text-right">{formatBytes(selectedDoc.size_bytes)}</div>

                                <div className="text-text-secondary">Subido</div>
                                <div className="text-text-primary text-right">{new Date(selectedDoc.created_at).toLocaleDateString()}</div>
                            </div>
                        </div>

                        <div className="space-y-3">
                            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">Resumen IA</h4>
                            <div className="p-3 bg-bg-elevated/50 rounded-lg text-xs text-text-secondary leading-relaxed border border-border-subtle max-h-48 overflow-y-auto">
                                {summaries[selectedDoc.id] ? (
                                    <p className="whitespace-pre-wrap">{summaries[selectedDoc.id]}</p>
                                ) : (
                                    <>
                                        Este documento parece contener información relacionada con <span className="text-text-primary font-medium">{selectedDoc.metadata?.category || 'general'}</span>.
                                        Verity puede analizarlo para extraer cláusulas clave o datos financieros.
                                    </>
                                )}
                            </div>
                            <button
                                onClick={() => handleGenerateSummary(selectedDoc)}
                                disabled={generatingSummary}
                                className={`w-full py-2 border rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-2 ${generatingSummary
                                    ? 'bg-bg-elevated border-border-default text-text-muted cursor-wait'
                                    : 'bg-accent-info/10 hover:bg-accent-info/20 border-accent-info/30 text-accent-info'
                                    }`}
                            >
                                {generatingSummary ? (
                                    <>
                                        <Loader2 className="w-3 h-3 animate-spin" /> Generando...
                                    </>
                                ) : (
                                    <>
                                        <RefreshCw className="w-3 h-3" /> Generar Resumen Completo
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    <div className="p-4 border-t border-border-default grid grid-cols-2 gap-3">
                        <button
                            onClick={() => {
                                // Open document in new tab for viewing/downloading
                                const downloadUrl = documentsApi.getDownloadUrl(selectedDoc.id);
                                window.open(downloadUrl, '_blank');
                            }}
                            className="flex items-center justify-center gap-2 py-2 rounded-lg bg-bg-elevated hover:bg-bg-hover border border-border-default text-xs font-medium text-text-primary transition-colors"
                        >
                            <Eye className="w-3 h-3" /> Ver
                        </button>
                        <button
                            onClick={() => handleDelete(selectedDoc.id)}
                            className="flex items-center justify-center gap-2 py-2 rounded-lg bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-xs font-medium text-red-500 transition-colors"
                        >
                            <Trash2 className="w-3 h-3" /> Borrar
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default FilesPage;