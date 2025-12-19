import { 
  Home, 
  Files, 
  MessageSquare, 
  CheckSquare, 
  BarChart2, 
  ShieldAlert, 
  Settings,
  FileText
} from 'lucide-react';
import { NavItem, VerityDocument, ApprovalRequest, Report, AuditLog, Conversation, ChatMessage, TeamMember } from './types';

// --- MOCK FILES ---
export const MOCK_DOCUMENTS: VerityDocument[] = [
  {
    id: '1',
    display_name: 'Contrato_Servicios_2024.pdf',
    mime_type: 'application/pdf',
    size_bytes: 1258291,
    status: 'ready',
    created_at: '2024-01-15T10:30:00Z',
    metadata: { category: 'legal' }
  },
  {
    id: '2',
    display_name: 'Presupuesto_Q4.xlsx',
    mime_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    size_bytes: 45056,
    status: 'processing',
    created_at: '2024-01-16T15:20:00Z',
    metadata: { category: 'finanzas' }
  },
  {
    id: '3',
    display_name: 'Minuta_Reunion_Estrategia.docx',
    mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    size_bytes: 12048,
    status: 'ready',
    created_at: '2024-01-16T09:00:00Z',
    metadata: { category: 'internal' }
  },
  {
    id: '4',
    display_name: 'Brand_Kit_Logo.png',
    mime_type: 'image/png',
    size_bytes: 2500000,
    status: 'ready',
    created_at: '2024-01-10T11:00:00Z',
  },
  {
    id: '5',
    display_name: 'Archivo_Corrupto_Scan.pdf',
    mime_type: 'application/pdf',
    size_bytes: 0,
    status: 'failed',
    created_at: '2024-01-05T14:00:00Z',
  },
  {
    id: '6',
    display_name: 'Politica_Vacaciones_2024.pdf',
    mime_type: 'application/pdf',
    size_bytes: 540200,
    status: 'ready',
    created_at: '2024-01-02T10:00:00Z',
  },
  {
    id: '7',
    display_name: 'Lista_Empleados_Enero.csv',
    mime_type: 'text/csv',
    size_bytes: 8500,
    status: 'ready',
    created_at: '2024-01-15T09:30:00Z',
  },
  {
    id: '8',
    display_name: 'Especificaciones_Proyecto_X.docx',
    mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    size_bytes: 125000,
    status: 'processing',
    created_at: '2024-01-16T16:00:00Z',
  }
];

// --- MOCK CHAT ---
export const MOCK_CONVERSATIONS: Conversation[] = [
  { id: 'c1', title: 'Dudas sobre Contratos', last_message: 'Gracias por la información', updated_at: '2024-01-16T10:30:00Z' },
  { id: 'c2', title: 'Análisis Financiero Q4', last_message: '¿Cuál fue el gasto mayor?', updated_at: '2024-01-15T14:20:00Z' },
  { id: 'c3', title: 'Política de RRHH', last_message: 'Generando resumen...', updated_at: '2024-01-14T09:00:00Z' },
];

export const MOCK_INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 'm1',
    role: 'user',
    content: '¿Cuál es la política de vacaciones actual?',
    timestamp: '2024-01-16T10:00:00Z'
  },
  {
    id: 'm2',
    role: 'assistant',
    content: 'Según el documento "Politica_Vacaciones_2024.pdf", los empleados tienen derecho a 20 días hábiles de vacaciones después del primer año de servicio. Las solicitudes deben realizarse con al menos 2 semanas de anticipación.',
    timestamp: '2024-01-16T10:00:05Z',
    request_id: 'req_123456789',
    sources: [
      {
        type: 'document',
        id: '6',
        title: 'Politica_Vacaciones_2024.pdf',
        snippet: '...los empleados gozarán de 20 días hábiles de vacaciones remuneradas tras cumplir un año...',
        relevance: 0.98
      }
    ]
  },
  {
    id: 'm3',
    role: 'user',
    content: '¿Quién debe aprobar estas solicitudes?',
    timestamp: '2024-01-16T10:01:00Z'
  },
  {
    id: 'm4',
    role: 'assistant',
    content: 'Las solicitudes de vacaciones deben ser aprobadas por el gerente directo del empleado y notificadas al departamento de Recursos Humanos para su registro.',
    timestamp: '2024-01-16T10:01:10Z',
    request_id: 'req_987654321',
    sources: [
      {
        type: 'document',
        id: '6',
        title: 'Politica_Vacaciones_2024.pdf',
        snippet: '...aprobación requerida por gerente directo y notificación a RRHH...',
        relevance: 0.95
      }
    ]
  }
];

// --- MOCK APPROVALS ---
export const MOCK_APPROVALS: ApprovalRequest[] = [
  {
    id: 'a1',
    entity_type: 'Empleado',
    entity_id: 'emp_001',
    entity_name: 'Juan Pérez',
    requested_by: 'sistema@verity.ai',
    created_at: '2024-01-16T08:30:00Z',
    reason: 'Actualización automática por antigüedad',
    status: 'pending',
    changes: [
      { field_name: 'dias_vacaciones', old_value: 15, new_value: 20, status: 'pending' }
    ]
  },
  {
    id: 'a2',
    entity_type: 'Contrato',
    entity_id: 'ctr_2024_055',
    entity_name: 'Servicios Acme S.A.',
    requested_by: 'maria.gonzalez@empresa.com',
    created_at: '2024-01-15T16:45:00Z',
    reason: 'Corrección de monto total',
    status: 'pending',
    changes: [
      { field_name: 'monto_total', old_value: 50000, new_value: 55000, status: 'pending' },
      { field_name: 'moneda', old_value: 'MXN', new_value: 'USD', status: 'pending' }
    ]
  },
  {
    id: 'a3',
    entity_type: 'Presupuesto',
    entity_id: 'budget_mkting',
    entity_name: 'Marketing Q1',
    requested_by: 'carlos.ruiz@empresa.com',
    created_at: '2024-01-14T11:20:00Z',
    reason: 'Ajuste inflacionario',
    status: 'pending',
    changes: [
      { field_name: 'limite_gastos', old_value: 120000, new_value: 135000, status: 'pending' }
    ]
  }
];

// --- MOCK REPORTS ---
export const MOCK_REPORTS: Report[] = [
  {
    id: 'r1',
    title: 'Resumen Financiero Q4 2023',
    type: 'financial',
    author: 'Ana Martínez',
    created_at: '2024-01-10T14:00:00Z',
    content: '### Resumen Ejecutivo\nEl cuarto trimestre mostró un crecimiento del 15% respecto al año anterior.\n\n### Puntos Clave\n- Ingresos aumentaron en sector servicios.\n- Gastos operativos se mantuvieron estables.\n- La contratación de personal aumentó un 5%.',
    chart_data: { type: 'bar', values: [ {x: 'Oct', y: 120}, {x: 'Nov', y: 150}, {x: 'Dic', y: 180} ] }
  },
  {
    id: 'r2',
    title: 'Análisis de Riesgos 2024',
    type: 'analysis',
    author: 'Carlos Ruiz',
    created_at: '2024-01-12T09:30:00Z',
    content: 'Se han identificado 3 riesgos principales para la operación del próximo año fiscal...',
  },
  {
    id: 'r3',
    title: 'Reporte de Conformidad Legal',
    type: 'compliance',
    author: 'Departamento Legal',
    created_at: '2024-01-15T11:00:00Z',
    content: 'Todos los contratos vigentes han sido revisados y cumplen con la nueva normativa...',
  },
  {
    id: 'r4',
    title: 'Resumen de Contrataciones',
    type: 'analysis',
    author: 'Recursos Humanos',
    created_at: '2024-01-05T16:20:00Z',
    content: 'Durante el último semestre se han incorporado 12 nuevos talentos a las áreas de TI y Ventas.',
  }
];

// --- MOCK AUDIT ---
export const MOCK_AUDIT_LOGS: AuditLog[] = [
  { id: 'l1', action: 'upload', actor: 'juan.perez@empresa.com', entity: 'Contrato_Servicios_2024.pdf', details: 'Nuevo documento subido', timestamp: '2024-01-16T10:30:00Z' },
  { id: 'l2', action: 'search', actor: 'maria.g@empresa.com', entity: 'n/a', details: 'Búsqueda: "cláusulas de rescisión"', timestamp: '2024-01-16T10:15:00Z' },
  { id: 'l3', action: 'approve', actor: 'admin@empresa.com', entity: 'Empleado: Emp_044', details: 'Aprobado cambio de salario', timestamp: '2024-01-16T09:45:00Z' },
  { id: 'l4', action: 'login', actor: 'carlos.ruiz@empresa.com', entity: 'Session', details: 'Inicio de sesión exitoso', timestamp: '2024-01-16T09:00:00Z' },
  { id: 'l5', action: 'reject', actor: 'admin@empresa.com', entity: 'Presupuesto IT', details: 'Rechazado por falta de fondos', timestamp: '2024-01-15T16:30:00Z' },
  { id: 'l6', action: 'update', actor: 'sistema', entity: 'Indice Búsqueda', details: 'Reindexación completada', timestamp: '2024-01-15T14:00:00Z' },
  { id: 'l7', action: 'upload', actor: 'ana.m@empresa.com', entity: 'Reporte_Q3.pdf', details: 'Documento subido', timestamp: '2024-01-15T11:20:00Z' },
  { id: 'l8', action: 'search', actor: 'juan.perez@empresa.com', entity: 'n/a', details: 'Búsqueda: "vacaciones"', timestamp: '2024-01-15T10:05:00Z' },
  { id: 'l9', action: 'login', actor: 'ana.m@empresa.com', entity: 'Session', details: 'Inicio de sesión', timestamp: '2024-01-15T09:00:00Z' },
  { id: 'l10', action: 'update', actor: 'admin@empresa.com', entity: 'Configuración', details: 'Cambio de nombre de organización', timestamp: '2024-01-14T17:00:00Z' },
];

// --- MOCK TEAM MEMBERS ---
export const MOCK_TEAM_MEMBERS: TeamMember[] = [
  {
    id: 'u1',
    name: 'John Doe',
    email: 'john@acme.com',
    roles: ['admin', 'approver'],
    status: 'active',
    joined_at: '2023-11-01T10:00:00Z'
  },
  {
    id: 'u2',
    name: 'Maria Garcia',
    email: 'maria@acme.com',
    roles: ['user'],
    status: 'active',
    joined_at: '2023-12-15T09:00:00Z'
  },
  {
    id: 'u3',
    name: 'Carlos López',
    email: 'carlos@acme.com',
    roles: ['auditor'],
    status: 'invited',
    joined_at: '2024-01-10T14:30:00Z'
  },
  {
    id: 'u4',
    name: 'Ana Martínez',
    email: 'ana@acme.com',
    roles: ['user', 'approver'],
    status: 'active',
    joined_at: '2023-11-20T11:00:00Z'
  }
];

export const NAV_ITEMS: NavItem[] = [
  { label: 'Inicio', path: '/', icon: Home },
  { label: 'Archivos', path: '/files', icon: Files },
  { label: 'Chat (Veri)', path: '/chat', icon: MessageSquare },
  { label: 'Aprobaciones', path: '/approvals', icon: CheckSquare, roles: ['approver', 'admin'] },
  { label: 'Reportes', path: '/reports', icon: BarChart2 },
  { label: 'Auditoría', path: '/audit', icon: ShieldAlert, roles: ['admin', 'auditor'] },
  { label: 'Configuración', path: '/settings', icon: Settings },
];

export const formatBytes = (bytes: number, decimals = 2) => {
  if (!+bytes) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
};