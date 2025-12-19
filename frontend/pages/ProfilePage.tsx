import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, Check, LogOut, Save, Smartphone, Mail, Shield, Globe, Clock, Moon } from 'lucide-react';
import { computeInitials, updateProfile } from '../services/profileStore';
import { useProfile } from '../services/useProfile';
import { setTheme, setThemeSetting } from '../services/themeStore';
import { useThemeSetting } from '../services/useThemeSetting';

const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
    const profile = useProfile();
    const [displayName, setDisplayName] = useState(profile.displayName);
    const [email, setEmail] = useState(profile.email);
  const [language, setLanguage] = useState('es');
  const [timezone, setTimezone] = useState('UTC-6');
    const theme = useThemeSetting();

  const handleLogout = () => {
      localStorage.removeItem('verity_token');
      navigate('/login');
  };

    const handleSave = () => {
        updateProfile({
            displayName: displayName.trim() || profile.displayName,
            email: email.trim() || profile.email,
        });
    };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8 animate-in fade-in duration-300">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-text-primary">Tu Perfil</h1>
        <p className="text-text-muted">Administra tu información personal y preferencias.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* Left Column: Avatar & Main Info */}
        <div className="md:col-span-1 space-y-6">
            <div className="bg-bg-surface border border-border-default rounded-xl p-6 flex flex-col items-center text-center">
                <div className="relative group cursor-pointer mb-4">
                    <div className="w-24 h-24 rounded-full bg-bg-elevated border-2 border-border-default flex items-center justify-center overflow-hidden">
                        <span className="text-2xl font-bold text-text-muted">{computeInitials(profile.displayName)}</span>
                    </div>
                    <div className="absolute inset-0 bg-black/50 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <Camera className="w-6 h-6 text-white" />
                    </div>
                    <button className="absolute bottom-0 right-0 p-1.5 bg-accent-info rounded-full text-bg-base border-2 border-bg-surface shadow-sm">
                        <Camera className="w-3 h-3" />
                    </button>
                </div>
                <h2 className="text-lg font-bold text-text-primary">{displayName}</h2>
                <p className="text-sm text-text-muted">{profile.organizationName}</p>
                
                <div className="w-full mt-6 space-y-3">
                    <div className="flex flex-wrap gap-2 justify-center">
                        <span className="px-2 py-1 rounded-md bg-purple-500/10 text-purple-400 border border-purple-500/20 text-xs font-medium uppercase">Admin</span>
                        <span className="px-2 py-1 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs font-medium uppercase">Approver</span>
                    </div>
                </div>
            </div>
            
             <button 
                onClick={handleLogout}
                className="w-full py-2.5 px-4 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 rounded-lg flex items-center justify-center gap-2 font-medium text-sm transition-colors"
             >
                <LogOut className="w-4 h-4" /> Cerrar Sesión
            </button>
        </div>

        {/* Right Column: Edit Forms */}
        <div className="md:col-span-2 space-y-6">
            {/* Personal Info */}
            <div className="bg-bg-surface border border-border-default rounded-xl p-6 space-y-5">
                <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wide border-b border-border-subtle pb-3">Información Personal</h3>
                
                <div className="space-y-4">
                    <div className="grid grid-cols-1 gap-4">
                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-text-secondary">Nombre para mostrar</label>
                            <input 
                                type="text" 
                                value={displayName}
                                onChange={(e) => setDisplayName(e.target.value)}
                                className="w-full bg-bg-base border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-success focus:outline-none"
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-1.5 opacity-75">
                            <label className="text-xs font-medium text-text-secondary flex items-center gap-2">
                                Teléfono <span className="text-[10px] px-1.5 py-0.5 bg-emerald-500/10 text-emerald-500 rounded-full flex items-center gap-1"><Check className="w-3 h-3"/> Verificado</span>
                            </label>
                            <div className="relative">
                                <Smartphone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                                <input 
                                    type="text" 
                                    value="+52 55 1234 5678"
                                    readOnly
                                    className="w-full pl-9 bg-bg-elevated border border-border-subtle rounded-lg px-3 py-2 text-sm text-text-muted cursor-not-allowed"
                                />
                            </div>
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-text-secondary">Email (Opcional)</label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                                <input 
                                    type="email" 
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="w-full pl-9 bg-bg-base border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-success focus:outline-none"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Preferences */}
            <div className="bg-bg-surface border border-border-default rounded-xl p-6 space-y-5">
                <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wide border-b border-border-subtle pb-3">Preferencias</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                     <div className="space-y-1.5">
                        <label className="text-xs font-medium text-text-secondary flex items-center gap-2">
                            <Moon className="w-3.5 h-3.5" /> Tema
                        </label>
                        <select 
                            value={theme}
                            onChange={(e) => {
                                const value = e.target.value;
                                if (value === 'light' || value === 'dark') setTheme(value);
                                else setThemeSetting('system');
                            }}
                            className="w-full bg-bg-base border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-success focus:outline-none"
                        >
                            <option value="light">Claro</option>
                            <option value="dark">Oscuro</option>
                            <option value="system">Sistema</option>
                        </select>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-text-secondary flex items-center gap-2">
                            <Globe className="w-3.5 h-3.5" /> Idioma
                        </label>
                        <select 
                            value={language}
                            onChange={(e) => setLanguage(e.target.value)}
                            className="w-full bg-bg-base border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-success focus:outline-none"
                        >
                            <option value="es">Español</option>
                            <option value="en">English</option>
                        </select>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-text-secondary flex items-center gap-2">
                            <Clock className="w-3.5 h-3.5" /> Zona Horaria
                        </label>
                        <select 
                            value={timezone}
                            onChange={(e) => setTimezone(e.target.value)}
                            className="w-full bg-bg-base border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-success focus:outline-none"
                        >
                            <option value="UTC-6">Ciudad de México (UTC-6)</option>
                            <option value="UTC-5">Bogotá (UTC-5)</option>
                            <option value="UTC-3">Buenos Aires (UTC-3)</option>
                            <option value="UTC+1">Madrid (UTC+1)</option>
                        </select>
                    </div>
                </div>
            </div>

            <div className="flex justify-end pt-2">
                <button
                    onClick={handleSave}
                    className="flex items-center gap-2 px-6 py-2.5 bg-accent-success hover:bg-accent-success-hover text-bg-base font-bold rounded-lg shadow-glow-success transition-all"
                >
                    <Save className="w-4 h-4" /> Guardar Cambios
                </button>
            </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;