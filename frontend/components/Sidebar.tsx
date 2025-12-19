import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { NAV_ITEMS } from '../constants';
import { computeInitials } from '../services/profileStore';
import { useProfile } from '../services/useProfile';

const Sidebar: React.FC = () => {
  const profile = useProfile();

  return (
    <aside className="w-64 h-full bg-bg-surface border-r border-border-default flex flex-col transition-all duration-300">
      {/* Brand */}
      <div className="h-16 flex items-center px-6 border-b border-border-default">
        <img src="/verity-logo.svg" alt="Verity Logo" className="h-8 w-auto" />
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 group ${isActive
                  ? 'bg-bg-active text-text-primary shadow-sm'
                  : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={`mr-3 h-5 w-5 transition-colors ${isActive ? 'text-accent-success' : 'text-text-muted group-hover:text-text-primary'
                      }`}
                  />
                  {item.label}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* User / Org profile */}
      <div className="p-4 border-t border-border-default">
        <Link to="/profile" className="flex items-center gap-3 p-2 rounded-lg hover:bg-bg-elevated transition-colors group">
          <div className="w-8 h-8 rounded-full bg-bg-elevated border border-border-default flex items-center justify-center group-hover:border-accent-info transition-colors">
            <span className="text-xs font-bold text-text-muted group-hover:text-text-primary">{computeInitials(profile.displayName)}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-medium text-text-primary group-hover:text-accent-info">{profile.displayName}</span>
            <span className="text-[10px] text-text-muted">{profile.organizationName}</span>
          </div>
        </Link>
      </div>
    </aside>
  );
};

export default Sidebar;