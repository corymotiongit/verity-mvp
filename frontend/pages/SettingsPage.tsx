import React, { useState, useEffect } from 'react';
import { Building2, Plug, Shield, Key, Users } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import TeamPage from './TeamPage';
import { updateProfile } from '../services/profileStore';
import { useProfile } from '../services/useProfile';

const SettingsPage: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const profile = useProfile();

    // Determine active tab from URL or default
    const getActiveTab = () => {
        if (location.pathname.includes('/team')) return 'team';
        if (location.pathname.includes('/integrations')) return 'integrations';
        return 'organization';
    };

    const [activeTab, setActiveTab] = useState(getActiveTab());
    const [orgName, setOrgName] = useState(profile.organizationName);

    // Update URL when tab changes (locally)
    const handleTabChange = (tab: string) => {
        setActiveTab(tab);
        if (tab === 'team') {
            navigate('/settings/team');
        } else if (tab === 'integrations') {
            navigate('/settings/integrations');
        } else {
            navigate('/settings');
        }
    };

    useEffect(() => {
        setActiveTab(getActiveTab());
    }, [location]);

    useEffect(() => {
        setOrgName(profile.organizationName);
    }, [profile.organizationName]);

    const handleSaveOrganization = () => {
        updateProfile({ organizationName: orgName.trim() || profile.organizationName });
    };

    return (
        <div className="p-8 max-w-6xl mx-auto space-y-8">
            <div className="flex flex-col gap-2">
                <h1 className="text-2xl font-bold text-text-primary">Configuración</h1>
                <p className="text-text-muted">Administra tu organización e integraciones.</p>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-border-default space-x-6">
                <button
                    onClick={() => handleTabChange('organization')}
                    className={`pb-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'organization' ? 'border-accent-success text-accent-success' : 'border-transparent text-text-muted hover:text-text-primary'
                        }`}
                >
                    Organización
                </button>
                <button
                    onClick={() => handleTabChange('team')}
                    className={`pb-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'team' ? 'border-accent-success text-accent-success' : 'border-transparent text-text-muted hover:text-text-primary'
                        }`}
                >
                    Equipo
                </button>
                <button
                    onClick={() => handleTabChange('integrations')}
                    className={`pb-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'integrations' ? 'border-accent-success text-accent-success' : 'border-transparent text-text-muted hover:text-text-primary'
                        }`}
                >
                    Integraciones
                </button>
            </div>

            {/* Content */}
            <div className={activeTab === 'team' ? '' : "bg-bg-surface border border-border-default rounded-xl p-6 min-h-[400px]"}>
                {activeTab === 'organization' && (
                    <div className="space-y-6 max-w-lg animate-in fade-in duration-300">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-text-secondary">Nombre de la Organización</label>
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-bg-elevated rounded text-text-muted">
                                    <Building2 className="w-5 h-5" />
                                </div>
                                <input
                                    type="text"
                                    value={orgName}
                                    onChange={(e) => setOrgName(e.target.value)}
                                    className="flex-1 bg-bg-base border border-border-default rounded-lg px-3 py-2 text-text-primary focus:border-accent-success focus:outline-none"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-text-secondary">File Search Store ID (Google GenAI)</label>
                            <div className="flex items-center gap-3">
                                <input type="text" readOnly value="files_store_abc123xyz" className="flex-1 bg-bg-elevated border border-border-subtle rounded-lg px-3 py-2 text-text-muted font-mono text-sm" />
                                <button className="text-xs text-accent-info hover:underline">Copiar</button>
                            </div>
                            <p className="text-xs text-text-muted">Identificador de solo lectura conectado a tu base de conocimientos.</p>
                        </div>

                        <div className="pt-4 border-t border-border-default">
                            <button
                                onClick={handleSaveOrganization}
                                className="px-4 py-2 bg-accent-success hover:bg-accent-success-hover text-bg-base font-medium rounded-lg shadow-glow-success transition-all"
                            >
                                Guardar Cambios
                            </button>
                        </div>
                    </div>
                )}

                {activeTab === 'integrations' && (
                    <div className="space-y-6 animate-in fade-in duration-300">
                        {/* WhatsApp */}
                        <div className="flex items-center justify-between p-4 bg-bg-base border border-border-default rounded-lg">
                            <div className="flex items-center gap-4">
                                <div className="w-10 h-10 bg-[#25D366]/20 text-[#25D366] rounded-full flex items-center justify-center">
                                    <MessageSquare className="w-5 h-5" />
                                </div>
                                <div>
                                    <h3 className="text-sm font-bold text-text-primary">WhatsApp Business</h3>
                                    <p className="text-xs text-text-muted">Autenticación y notificaciones</p>
                                </div>
                            </div>
                            <span className="flex items-center gap-1.5 px-2 py-1 bg-emerald-500/10 text-emerald-500 rounded text-xs font-medium">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Conectado
                            </span>
                        </div>

                        {/* n8n */}
                        <div className="flex items-center justify-between p-4 bg-bg-base border border-border-default rounded-lg">
                            <div className="flex items-center gap-4">
                                <div className="w-10 h-10 bg-orange-500/20 text-orange-500 rounded-full flex items-center justify-center">
                                    <Plug className="w-5 h-5" />
                                </div>
                                <div>
                                    <h3 className="text-sm font-bold text-text-primary">n8n Workflows</h3>
                                    <p className="text-xs text-text-muted">Automatización de procesos</p>
                                </div>
                            </div>
                            <button className="px-3 py-1.5 border border-border-default hover:bg-bg-elevated rounded text-xs font-medium text-text-primary transition-colors">
                                Conectar
                            </button>
                        </div>

                        {/* API Key */}
                        <div className="flex items-center justify-between p-4 bg-bg-base border border-border-default rounded-lg opacity-75">
                            <div className="flex items-center gap-4">
                                <div className="w-10 h-10 bg-bg-elevated text-text-muted rounded-full flex items-center justify-center">
                                    <Key className="w-5 h-5" />
                                </div>
                                <div>
                                    <h3 className="text-sm font-bold text-text-primary">Verity API Key</h3>
                                    <p className="text-xs text-text-muted font-mono">veri_*****************8392</p>
                                </div>
                            </div>
                            <button className="text-xs text-text-secondary hover:text-text-primary underline">
                                Regenerar
                            </button>
                        </div>
                    </div>
                )}

                {activeTab === 'team' && (
                    <TeamPage embedded={true} />
                )}
            </div>
        </div>
    );
};

const MessageSquare = ({ className }: { className?: string }) => (
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className}
    >
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
    </svg>
);

export default SettingsPage;