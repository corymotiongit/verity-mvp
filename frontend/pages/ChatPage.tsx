import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, Loader2, Send, Sparkles } from 'lucide-react';
import { ChatMessage } from '../types';
import { queryV2Api } from '../services/api';

const ChatPage: React.FC = () => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const question = input;
        const userMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'user',
            content: question,
            timestamp: new Date().toISOString(),
        };

        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);
        setError(null);

        try {
            const response = await queryV2Api.query(question);
            const assistantMsg: ChatMessage = {
                id: crypto.randomUUID(),
                role: 'assistant',
                content: response.response,
                timestamp: new Date().toISOString(),
            };
            setMessages(prev => [...prev, assistantMsg]);
        } catch (err: any) {
            console.error('Chat error:', err);
            const message = err instanceof Error ? err.message : String(err);
            setError(message || 'Error al comunicarse con Veri');
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
            <div className="flex-1 flex flex-col h-full relative">
                {error && (
                    <div className="border-b border-border-default bg-bg-surface px-6 py-3">
                        <div className="flex items-center gap-2 text-accent-danger text-sm">
                            <AlertCircle className="w-4 h-4" />
                            <span>{error}</span>
                        </div>
                    </div>
                )}

                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {messages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full opacity-60">
                            <Sparkles className="w-12 h-12 text-accent-info mb-4" />
                            <h2 className="text-xl font-medium text-text-primary">Hola, soy Veri</h2>
                            <p className="text-sm text-text-muted mt-2">Haz una pregunta para comenzar.</p>
                        </div>
                    ) : (
                        messages.map(msg => (
                            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[80%] rounded-2xl p-4 text-sm ${msg.role === 'user' ? 'bg-bg-active text-text-primary' : 'bg-bg-surface border border-border-default'}`}>
                                    <p className="whitespace-pre-wrap">{msg.content}</p>
                                </div>
                            </div>
                        ))
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <div className="p-6 bg-bg-base border-t border-border-default">
                    <div className="relative max-w-4xl mx-auto">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Pregunta a Veri..."
                            className="w-full bg-bg-surface border border-border-default rounded-xl pl-4 pr-12 py-3.5 min-h-[56px] focus:outline-none focus:border-accent-info resize-none text-sm"
                            rows={1}
                            disabled={isLoading}
                        />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || isLoading}
                            className={`absolute right-3 top-3 p-1.5 rounded-lg ${input.trim() && !isLoading ? 'bg-accent-success text-white' : 'bg-bg-elevated text-text-disabled'}`}
                            aria-label="Enviar"
                        >
                            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatPage;