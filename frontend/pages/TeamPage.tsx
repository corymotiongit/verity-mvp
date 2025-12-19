import React, { useState } from 'react';
import { MOCK_TEAM_MEMBERS } from '../constants';
import { TeamMember, UserRole, MemberStatus } from '../types';
import { MoreVertical, UserPlus, X, Trash2 } from 'lucide-react';

interface TeamPageProps {
    embedded?: boolean;
}

const TeamPage: React.FC<TeamPageProps> = ({ embedded = false }) => {
  const [users, setUsers] = useState<TeamMember[]>(MOCK_TEAM_MEMBERS);
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<TeamMember | null>(null);

  const getStatusBadge = (status: MemberStatus) => {
    switch (status) {
      case 'active':
        return <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 text-[10px] font-medium uppercase tracking-wide">Activo</span>;
      case 'invited':
        return <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20 text-[10px] font-medium uppercase tracking-wide">Invitado</span>;
      case 'disabled':
        return <span className="px-2 py-0.5 rounded-full bg-gray-500/10 text-gray-500 border border-gray-500/20 text-[10px] font-medium uppercase tracking-wide">Desactivado</span>;
    }
  };

  const getRoleBadge = (role: UserRole) => {
      const colors: Record<string, string> = {
          admin: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
          approver: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
          auditor: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
          user: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
          owner: 'bg-accent-success/10 text-accent-success border-accent-success/20'
      };
      return (
          <span className={`px-1.5 py-0.5 rounded border text-[10px] font-medium uppercase ${colors[role] || colors.user}`}>
              {role}
          </span>
      );
  };

  // Adjust container classes based on embedded prop
  const containerClasses = embedded 
    ? "space-y-6 animate-in fade-in duration-300 relative min-h-full"
    : "p-8 max-w-6xl mx-auto space-y-8 animate-in fade-in duration-300 relative min-h-full";

  return (
    <div className={containerClasses}>
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col gap-2">
            <h1 className="text-2xl font-bold text-text-primary">Gestión de Equipo</h1>
            <p className="text-text-muted">Administra los accesos y roles de tu organización.</p>
        </div>
        <button 
            onClick={() => setIsInviteOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-accent-success hover:bg-accent-success-hover text-bg-base font-bold rounded-lg shadow-glow-success transition-all"
        >
            <UserPlus className="w-4 h-4" /> Invitar Usuario
        </button>
      </div>

      {/* Team List */}
      <div className="bg-bg-surface border border-border-default rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
            <thead>
                <tr className="border-b border-border-default bg-bg-elevated/50">
                    <th className="py-3 px-6 text-xs font-semibold text-text-secondary uppercase tracking-wider">Usuario</th>
                    <th className="py-3 px-6 text-xs font-semibold text-text-secondary uppercase tracking-wider">Roles</th>
                    <th className="py-3 px-6 text-xs font-semibold text-text-secondary uppercase tracking-wider">Estado</th>
                    <th className="py-3 px-6 text-xs font-semibold text-text-secondary uppercase tracking-wider">Unido</th>
                    <th className="py-3 px-6 w-12"></th>
                </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
                {users.map((user) => (
                    <tr key={user.id} className="group hover:bg-bg-hover transition-colors">
                        <td className="py-4 px-6">
                            <div className="flex items-center gap-3">
                                <div className="w-9 h-9 rounded-full bg-bg-elevated border border-border-subtle flex items-center justify-center font-bold text-text-secondary">
                                    {user.avatar_url ? <img src={user.avatar_url} className="w-full h-full rounded-full" alt={user.name} /> : user.name.charAt(0)}
                                </div>
                                <div className="flex flex-col">
                                    <span className="font-medium text-text-primary text-sm">{user.name}</span>
                                    <span className="text-xs text-text-muted">{user.email || user.phone}</span>
                                </div>
                            </div>
                        </td>
                        <td className="py-4 px-6">
                            <div className="flex flex-wrap gap-1.5">
                                {user.roles.map(r => <div key={r}>{getRoleBadge(r)}</div>)}
                            </div>
                        </td>
                        <td className="py-4 px-6">
                            {getStatusBadge(user.status)}
                        </td>
                        <td className="py-4 px-6 text-sm text-text-muted">
                            {new Date(user.joined_at).toLocaleDateString()}
                        </td>
                        <td className="py-4 px-6 text-center">
                            <button 
                                onClick={() => setEditingUser(user)}
                                className="text-text-muted hover:text-text-primary p-1.5 rounded-lg hover:bg-bg-active transition-colors"
                            >
                                <MoreVertical className="w-4 h-4" />
                            </button>
                        </td>
                    </tr>
                ))}
            </tbody>
        </table>
      </div>

      {/* Invite Modal */}
      {isInviteOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
              <div className="bg-bg-surface border border-border-default rounded-xl w-full max-w-md shadow-2xl overflow-hidden">
                  <div className="p-4 border-b border-border-default flex justify-between items-center bg-bg-elevated/50">
                      <h3 className="font-bold text-text-primary">Invitar Usuario</h3>
                      <button onClick={() => setIsInviteOpen(false)} className="text-text-muted hover:text-text-primary p-1 rounded hover:bg-bg-hover"><X className="w-4 h-4"/></button>
                  </div>
                  <div className="p-6 space-y-4">
                      <div className="space-y-1.5">
                          <label className="text-xs font-medium text-text-secondary">Email o Teléfono</label>
                          <input type="text" placeholder="nombre@empresa.com" className="w-full bg-bg-base border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-success focus:outline-none" />
                      </div>
                      
                      <div className="space-y-2">
                          <label className="text-xs font-medium text-text-secondary">Roles Iniciales</label>
                          <div className="flex flex-wrap gap-2">
                              {['user', 'approver', 'auditor', 'admin'].map(role => (
                                  <label key={role} className="flex items-center gap-2 p-2 bg-bg-base border border-border-default rounded-lg cursor-pointer hover:border-text-muted">
                                      <input type="checkbox" className="rounded border-border-default bg-bg-surface text-accent-success focus:ring-accent-success/50" defaultChecked={role === 'user'} />
                                      <span className="text-sm capitalize">{role}</span>
                                  </label>
                              ))}
                          </div>
                      </div>

                      <div className="space-y-1.5">
                          <label className="text-xs font-medium text-text-secondary">Mensaje (Opcional)</label>
                          <textarea className="w-full bg-bg-base border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-success focus:outline-none resize-none h-20" placeholder="Te invito a unirte a nuestra organización en Verity..."></textarea>
                      </div>
                  </div>
                  <div className="p-4 border-t border-border-default bg-bg-elevated/30 flex justify-end gap-3">
                      <button onClick={() => setIsInviteOpen(false)} className="px-4 py-2 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-bg-hover">Cancelar</button>
                      <button onClick={() => setIsInviteOpen(false)} className="px-4 py-2 rounded-lg text-sm font-bold bg-accent-success text-bg-base hover:bg-accent-success-hover shadow-glow-success">Enviar Invitación</button>
                  </div>
              </div>
          </div>
      )}

      {/* Manage User Modal */}
      {editingUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
              <div className="bg-bg-surface border border-border-default rounded-xl w-full max-w-md shadow-2xl overflow-hidden">
                  <div className="p-4 border-b border-border-default flex justify-between items-center bg-bg-elevated/50">
                      <h3 className="font-bold text-text-primary">Administrar Usuario</h3>
                      <button onClick={() => setEditingUser(null)} className="text-text-muted hover:text-text-primary p-1 rounded hover:bg-bg-hover"><X className="w-4 h-4"/></button>
                  </div>
                  <div className="p-6 space-y-5">
                      <div className="flex items-center gap-4 mb-2">
                            <div className="w-12 h-12 rounded-full bg-bg-elevated border border-border-default flex items-center justify-center text-lg font-bold">
                                {editingUser.name.charAt(0)}
                            </div>
                            <div>
                                <h4 className="font-bold text-text-primary">{editingUser.name}</h4>
                                <p className="text-xs text-text-muted">{editingUser.email}</p>
                            </div>
                      </div>

                      <div className="space-y-1.5">
                          <label className="text-xs font-medium text-text-secondary">Nombre Completo</label>
                          <input type="text" defaultValue={editingUser.name} className="w-full bg-bg-base border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-success focus:outline-none" />
                      </div>

                      <div className="space-y-2">
                          <label className="text-xs font-medium text-text-secondary">Roles</label>
                          <div className="grid grid-cols-2 gap-2">
                              {['user', 'approver', 'auditor', 'admin'].map(role => (
                                  <label key={role} className={`flex items-center gap-2 p-2 border rounded-lg cursor-pointer transition-colors ${editingUser.roles.includes(role as UserRole) ? 'bg-accent-success/5 border-accent-success/30' : 'bg-bg-base border-border-default'}`}>
                                      <input type="checkbox" className="rounded border-border-default bg-bg-surface text-accent-success focus:ring-accent-success/50" defaultChecked={editingUser.roles.includes(role as UserRole)} />
                                      <span className="text-sm capitalize">{role}</span>
                                  </label>
                              ))}
                          </div>
                      </div>

                      <div className="space-y-1.5">
                          <label className="text-xs font-medium text-text-secondary">Estado</label>
                          <select defaultValue={editingUser.status} className="w-full bg-bg-base border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-success focus:outline-none">
                              <option value="active">Activo</option>
                              <option value="invited">Invitado</option>
                              <option value="disabled">Desactivado</option>
                          </select>
                      </div>
                  </div>
                  <div className="p-4 border-t border-border-default bg-bg-elevated/30 flex justify-between items-center gap-3">
                      <button className="flex items-center gap-1.5 text-xs text-red-500 hover:text-red-400 font-medium px-2 py-1.5 rounded hover:bg-red-500/10 transition-colors">
                          <Trash2 className="w-3.5 h-3.5" /> Remover de Org
                      </button>
                      <div className="flex gap-2">
                        <button onClick={() => setEditingUser(null)} className="px-3 py-1.5 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-bg-hover">Cancelar</button>
                        <button onClick={() => setEditingUser(null)} className="px-3 py-1.5 rounded-lg text-sm font-bold bg-accent-success text-bg-base hover:bg-accent-success-hover shadow-glow-success">Guardar</button>
                      </div>
                  </div>
              </div>
          </div>
      )}
    </div>
  );
};

export default TeamPage;