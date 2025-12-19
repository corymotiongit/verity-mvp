import React from 'react';
import { Search, Plus, Bell, Sun, Moon } from 'lucide-react';
import { toggleTheme } from '../services/themeStore';
import { useTheme } from '../services/useTheme';

const Topbar: React.FC = () => {
  const theme = useTheme();
  const isDark = theme === 'dark';

  return (
    <header className="h-16 bg-bg-base/80 backdrop-blur-md border-b border-border-default flex items-center justify-between px-6 sticky top-0 z-10">
      {/* Search Bar */}
      <div className="flex-1 max-w-xl">
        <div className="relative group">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-text-muted group-focus-within:text-accent-success transition-colors" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-2 border border-border-default rounded-lg leading-5 bg-bg-surface text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-success/50 focus:ring-1 focus:ring-accent-success/50 sm:text-sm transition-all shadow-sm"
            placeholder="Buscar documentos, entidades o preguntar a Veri... (Cmd+K)"
          />
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <span className="text-bg-elevated text-xs border border-border-default px-1.5 py-0.5 rounded">⌘K</span>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center space-x-4 ml-4">
        <button 
            className="hidden md:flex items-center gap-2 bg-text-primary text-bg-base px-3 py-1.5 rounded-md text-sm font-medium hover:bg-white hover:shadow-[0_0_15px_rgba(255,255,255,0.3)] transition-all"
            onClick={() => console.log('Upload modal')}
        >
            <Plus className="h-4 w-4" />
            <span>Subir</span>
        </button>

        <div className="h-6 w-px bg-border-default mx-2"></div>

        <button 
            onClick={() => toggleTheme()}
            className="text-text-muted hover:text-text-primary transition-colors p-1 rounded-md hover:bg-bg-hover"
        >
          {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>

        <button className="text-text-muted hover:text-text-primary transition-colors p-1 rounded-md hover:bg-bg-hover relative">
          <Bell className="h-5 w-5" />
          <span className="absolute top-1 right-1 h-2 w-2 bg-accent-warning rounded-full border border-bg-base"></span>
        </button>
      </div>
    </header>
  );
};

export default Topbar;