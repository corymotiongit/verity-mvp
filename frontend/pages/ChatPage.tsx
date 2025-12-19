import React, { useRef, useState, useEffect } from 'react';
import { Send, FileText, Sparkles, Copy, ThumbsUp, ThumbsDown, Plus, Loader2, AlertCircle, Trash2, Filter, X, Tag, Folder, Database, ArrowRight } from 'lucide-react';
import { ChatMessage, Conversation, SourceCitation } from '../types';
import { agentApi, AgentChatResponse, ConversationSummary, documentsApi, ChatScope, ResolvedScope, ScopeSuggestion } from '../services/api';
import { PlotlyChart } from '../components/Chart/PlotlyChart';

const DEFAULT_SCOPE: ChatScope = {
    project: null,
    tag_ids: [],
    category: null,
    period: null,
    source: null,
    collection_id: null,
    doc_ids: [],
    mode: 'empty'
};

const ChatPage: React.FC = () => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [activeConvId, setActiveConvId] = useState<string | null>(() => localStorage.getItem('verity_active_conversation'));
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [loadingConvs, setLoadingConvs] = useState(true);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Scope State
    const [scope, setScope] = useState<ChatScope>(DEFAULT_SCOPE);
    const [scopeInfo, setScopeInfo] = useState<ResolvedScope | null>(null);
    const [showScopePanel, setShowScopePanel] = useState(false);
    const [isSavingScope, setIsSavingScope] = useState(false);

    // Filter Options
    const [availableFilters, setAvailableFilters] = useState<{
        categories: string[];
        projects: string[];
        tags: string[];
    }>({ categories: [], projects: [], tags: [] });

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Load conversation history details
    const loadConversation = async (convId: string) => {
        try {
            setIsLoading(true);
            const conv = await agentApi.getConversation(convId);
            setActiveConvId(convId);
            localStorage.setItem('verity_active_conversation', convId); // Persist

            // Map enriched message history
            setMessages(conv.messages.map(m => ({
                id: m.request_id || crypto.randomUUID(),
                role: m.role as 'user' | 'assistant',
                content: m.content,
                timestamp: m.timestamp,
                sources: m.sources || undefined,
                chart_spec: m.chart_spec || undefined,
                table_source: m.table_preview as any || undefined,
                evidence_ref: m.evidence_ref || undefined
            })));
        } catch (err: any) {
            console.error('Failed to load conversation:', err);
            setError('Error al cargar la conversacion');
            // Only clear local storage if error is 404 (Not Found) to avoid losing state on network error
            if (err.status === 404 || err.message?.includes('404')) {
                localStorage.removeItem('verity_active_conversation');
                setActiveConvId(null);
            }
        } finally {
            setIsLoading(false);
        }
    };

    const startNewChat = () => {
        setMessages([]);
        setActiveConvId(null);
        localStorage.removeItem('verity_active_conversation');
        setError(null);
        setScope(DEFAULT_SCOPE);
        setScopeInfo(null);
        setShowScopePanel(true);
    };

    useEffect(() => {
        const loadInitData = async () => {
            try {
                setLoadingConvs(true);
                const [convsRes, filters] = await Promise.all([
                    agentApi.listConversations(20),
                    documentsApi.getFilters()
                ]);

                setConversations(convsRes.items.map((c: ConversationSummary) => ({
                    id: c.id,
                    title: c.title || 'Sin titulo',
                    last_message: `${c.message_count} mensajes`,
                    updated_at: c.updated_at || c.created_at,
                })));
                setAvailableFilters(filters);

                // If there's an active conversation from localStorage, load it
                const storedId = localStorage.getItem('verity_active_conversation');
                if (storedId) {
                    loadConversation(storedId);
                }

            } catch (err) {
                console.error('Failed to load init data:', err);
            } finally {
                setLoadingConvs(false);
            }
        };
        loadInitData();
    }, []);

    // Load Scope when conversation changes
    useEffect(() => {
        const fetchScope = async () => {
            if (!activeConvId) {
                setScope(DEFAULT_SCOPE);
                setScopeInfo(null);
                // Por defecto mostrar el panel si es nuevo chat
                setShowScopePanel(true);
                return;
            }
            try {
                const s = await agentApi.getScope(activeConvId);
                if (s) {
                    setScope(s);
                    // Resolve to get summary
                    const resolved = await agentApi.resolveScope(activeConvId);
                    setScopeInfo(resolved);
                } else {
                    setScope(DEFAULT_SCOPE);
                }
            } catch (error) {
                console.error("Error fetching scope:", error);
            }
        };
        fetchScope();
    }, [activeConvId]);

    const handleUpdateScope = async (newScope: ChatScope) => {
        setScope(newScope);
        if (activeConvId) {
            setIsSavingScope(true);
            try {
                await agentApi.updateScope(activeConvId, newScope);
                const resolved = await agentApi.resolveScope(activeConvId);
                setScopeInfo(resolved);
            } catch (err) {
                console.error("Failed to update scope:", err);
            } finally {
                setIsSavingScope(false);
            }
        }
    };

    const handleSuggestionAction = async (suggestion: ScopeSuggestion) => {
        if (suggestion.action === 'clear_filters') {
            await handleUpdateScope({ ...DEFAULT_SCOPE, mode: 'all_docs' });
        } else if (suggestion.action === 'select_all') {
            await handleUpdateScope({ ...DEFAULT_SCOPE, mode: 'all_docs' });
        } else if (suggestion.action === 'select_project' && suggestion.project_id) {
            await handleUpdateScope({ ...DEFAULT_SCOPE, project: suggestion.project_id, mode: 'filtered' });
        } else if (suggestion.action === 'upload') {
            alert("Redirigir a carga de documentos para: " + suggestion.project_id);
            // TODO: Navigate to upload
        }
    };

    const convertSources = (sources: AgentChatResponse['sources'] | undefined | null): SourceCitation[] => {
        if (!Array.isArray(sources)) return [];

        return sources
            .filter((s: any) => s && typeof s === 'object')
            .map((s: any) => ({
                // UI currently renders all citations uniformly.
                type: 'document' as const,
                id: String(s.id ?? crypto.randomUUID()),
                title: String(s.title ?? s.file ?? 'Fuente'),
                snippet: String(s.snippet ?? ''),
                relevance: typeof s.relevance === 'number' ? s.relevance : 0,
            }));
    };

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        // If no conversation, create one implicitly by sending msg
        // Scope will be sent in context if modified locally before sync

        const userMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'user',
            content: input,
            timestamp: new Date().toISOString()
        };

        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);
        setError(null);

        try {
            const response = await agentApi.chat({
                message: input,
                conversation_id: activeConvId,
                // We send scope in context ONLY if it's a new conversation or we want to force update
                context: !activeConvId ? {
                    // Pass current scope state to backend for new conversation context
                    ...scope
                } as any : undefined
            });

            if (response.conversation_id && response.conversation_id !== activeConvId) {
                setActiveConvId(response.conversation_id);
                localStorage.setItem('verity_active_conversation', response.conversation_id);
            }
            // Update scope info from response (backend may send a simplified shape)
            if (response.scope_info) {
                const si: any = response.scope_info;
                if (typeof si === 'object' && si) {
                    setScopeInfo({
                        display_summary: si.display_summary ?? si.display ?? '',
                        doc_count: typeof si.doc_count === 'number' ? si.doc_count : 0,
                        requires_action: Boolean(si.requires_action),
                        is_empty: Boolean(si.is_empty),
                        empty_reason: si.empty_reason ?? null,
                        suggestion: si.suggestion ?? null,
                    } as any);
                }
            }

            const assistantMsg: ChatMessage = {
                id: crypto.randomUUID(),
                role: 'assistant',
                content: response.message.content,
                timestamp: new Date().toISOString(),
                request_id: response.request_id,
                sources: convertSources(response.sources),
                proposed_changes: response.proposed_changes || undefined,
                chart_spec: response.chart_spec || undefined,  // Keep full structure {type, spec}
                table_source: response.table_preview as any || undefined,
            };

            setMessages(prev => [...prev, assistantMsg]);

            // Refresh conv list if new
            if (!activeConvId) {
                const convsRes = await agentApi.listConversations(20);
                setConversations(convsRes.items.map((c: ConversationSummary) => ({
                    id: c.id,
                    title: c.title || 'Sin titulo',
                    last_message: `${c.message_count} mensajes`,
                    updated_at: c.updated_at || c.created_at,
                })));
            }

        } catch (err: any) {
            console.error('Chat error:', err);
            setError(err.message || 'Error al comunicarse con Veri');
            setMessages(prev => [...prev, {
                id: crypto.randomUUID(),
                role: 'assistant',
                content: 'Lo siento, hubo un error al procesar tu mensaje. Por favor intenta de nuevo.',
                timestamp: new Date().toISOString(),
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };



    return (
        <div className="flex h-full overflow-hidden">
            {/* Sidebar History (Simplified) */}
            <div className="w-64 border-r border-border-default bg-bg-surface hidden md:flex flex-col">
                <div className="p-4 border-b border-border-default">
                    <button onClick={startNewChat} className="w-full flex items-center gap-2 justify-center bg-accent-success text-bg-base font-medium py-2 rounded-lg hover:shadow-glow-success transition-all">
                        <Plus className="w-4 h-4" /> Nuevo Chat
                    </button>
                </div>
                <div className="flex-1 overflow-y-auto p-2">
                    {conversations.map(conv => (
                        <div key={conv.id} onClick={() => loadConversation(conv.id)} className={`p-3 rounded-lg cursor-pointer text-sm mb-1 ${activeConvId === conv.id ? 'bg-bg-active text-text-primary' : 'text-text-secondary hover:bg-bg-hover'}`}>
                            <div className="font-medium truncate">{conv.title}</div>
                            <div className="text-[10px] text-text-muted">{conv.last_message}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Main Area */}
            <div className="flex-1 flex flex-col h-full relative">

                {/* SCOPE BANNER */}
                <div className="border-b border-border-default bg-bg-surface px-6 py-3 flex items-center justify-between shadow-sm z-10">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 text-sm text-text-secondary">
                            <Database className="w-4 h-4 text-accent-info" />
                            <span className="font-medium text-text-primary">Buscando en:</span>
                            {scopeInfo ? (
                                <span className="bg-bg-elevated px-2 py-0.5 rounded border border-border-default text-text-primary flex items-center gap-2">
                                    {scopeInfo.display_summary}
                                    {scopeInfo.doc_count === 0 && <span className="text-red-400 text-xs">(0 docs)</span>}
                                </span>
                            ) : (
                                <span className="text-text-muted italic">Sin definir (Selecciona scope)</span>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={() => setShowScopePanel(!showScopePanel)}
                        className={`text-xs px-3 py-1.5 rounded-lg border transition-all flex items-center gap-2 ${showScopePanel ? 'bg-accent-success/10 text-accent-success border-accent-success' : 'bg-bg-base text-text-muted border-border-default hover:border-text-primary'}`}
                    >
                        <Filter className="w-3.5 h-3.5" />
                        {showScopePanel ? 'Ocultar Filtros' : 'Cambiar Scope'}
                    </button>
                </div>

                {/* SCOPE PANEL (Toggleable) */}
                {showScopePanel && (
                    <div className="bg-bg-subtle border-b border-border-default p-4 animate-in slide-in-from-top-2">
                        <div className="max-w-4xl mx-auto space-y-4">
                            <div>
                                <h4 className="text-xs font-semibold text-text-muted uppercase mb-2">Proyecto</h4>
                                <div className="flex flex-wrap gap-2">
                                    <button
                                        onClick={() => handleUpdateScope({ ...scope, project: null, mode: scope.tag_ids.length ? 'filtered' : 'all_docs' })}
                                        className={`px-3 py-1 text-xs rounded-full border ${!scope.project ? 'bg-accent-success text-bg-base border-transparent' : 'bg-bg-surface border-border-default'}`}
                                    >
                                        Cualquiera
                                    </button>
                                    {availableFilters.projects.map(p => (
                                        <button
                                            key={p}
                                            onClick={() => handleUpdateScope({ ...scope, project: p, mode: 'filtered' })}
                                            className={`px-3 py-1 text-xs rounded-full border ${scope.project === p ? 'bg-accent-success text-bg-base border-transparent' : 'bg-bg-surface border-border-default'}`}
                                        >
                                            {p}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <h4 className="text-xs font-semibold text-text-muted uppercase mb-2">Etiquetas</h4>
                                <div className="flex flex-wrap gap-2 text-xs text-text-muted italic">
                                    (Implementación futura: selección múltiple)
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* DIAGNOSTIC / SUGGESTION BANNER */}
                {scopeInfo?.requires_action && (
                    <div className="bg-red-500/10 border-b border-red-500/20 p-3 px-6 flex items-center justify-between">
                        <div className="flex items-center gap-2 text-red-400 text-sm">
                            <AlertCircle className="w-4 h-4" />
                            <span>{scopeInfo.empty_reason || "No se encontraron documentos."}</span>
                        </div>
                        {scopeInfo.suggestion && (
                            <button
                                onClick={() => scopeInfo.suggestion && handleSuggestionAction(scopeInfo.suggestion)}
                                className="flex items-center gap-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 px-3 py-1 rounded text-xs transition-colors font-medium border border-red-500/30"
                            >
                                {scopeInfo.suggestion.label} <ArrowRight className="w-3 h-3" />
                            </button>
                        )}
                    </div>
                )}

                {/* Chat Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {messages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full opacity-60">
                            <Sparkles className="w-12 h-12 text-accent-info mb-4" />
                            <h2 className="text-xl font-medium text-text-primary">Hola, soy Veri</h2>
                            <p className="text-sm text-text-muted mt-2">Configura el scope arriba y empieza a preguntar.</p>
                        </div>
                    ) : (
                        messages.map(msg => (
                            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[80%] rounded-2xl p-4 text-sm ${msg.role === 'user' ? 'bg-bg-active text-text-primary' : 'bg-bg-surface border border-border-default'}`}>
                                    <p className="whitespace-pre-wrap">{msg.content}</p>

                                    {/* Chart & Data Evidence */}
                                    {msg.chart_spec && (
                                        <div className="mt-4 w-full overflow-hidden rounded-lg border border-border-subtle bg-bg-base">
                                            <PlotlyChart
                                                chartSpec={msg.chart_spec}
                                                tableSource={msg.table_source || null}
                                                evidenceRef={msg.evidence_ref}
                                            />
                                        </div>
                                    )}
                                    {/* Sources */}
                                    {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                                        <div className="mt-3 pt-3 border-t border-border-subtle space-y-2">
                                            <div className="text-xs font-semibold text-text-muted uppercase">Fuentes</div>
                                            {msg.sources.map(s => (
                                                <div key={s.id} className="text-xs bg-bg-elevated p-2 rounded border border-border-default">
                                                    <div className="font-medium text-accent-info truncate">{s.title}</div>
                                                    <div className="text-text-muted truncate mt-0.5">{s.snippet}</div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-6 bg-bg-base border-t border-border-default">
                    <div className="relative max-w-4xl mx-auto">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Pregunta a Veri..."
                            className="w-full bg-bg-surface border border-border-default rounded-xl pl-4 pr-12 py-3.5 min-h-[56px] focus:outline-none focus:border-accent-info resize-none text-sm"
                            rows={1}
                        />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || isLoading}
                            className={`absolute right-3 top-3 p-1.5 rounded-lg ${input.trim() ? 'bg-accent-success text-white' : 'bg-bg-elevated text-text-disabled'}`}
                        >
                            <Send className="w-4 h-4" />
                        </button>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default ChatPage;