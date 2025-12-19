# Verity Design System

Este documento describe los principios de diseño, tokens (variables), componentes y estructura del proyecto **Verity MVP**. El sistema está diseñado para evocar una estética de "Startup moderna", priorizando el modo oscuro, el minimalismo y el alto contraste funcional.

---

## 1. Design Tokens (CSS Variables & Tailwind Config)

El sistema utiliza **Tailwind CSS** con una configuración extendida definida en `index.html`.

### 🎨 Paleta de Colores

#### Backgrounds (Capas de profundidad)
| Token Tailwind | Valor Hex | Uso |
|----------------|-----------|-----|
| `bg-bg-base` | `#0f0f12` | Fondo principal de la aplicación (body). |
| `bg-bg-surface` | `#18181c` | Tarjetas, paneles laterales, inputs. |
| `bg-bg-elevated` | `#1f1f24` | Modales, dropdowns, elementos flotantes. |
| `bg-bg-hover` | `#27272c` | Estado hover de elementos interactivos. |
| `bg-bg-active` | `#2f2f35` | Estado activo/seleccionado de navegación o tabs. |

#### Bordes
| Token Tailwind | Valor RGBA | Uso |
|----------------|------------|-----|
| `border-border-subtle` | `rgba(255, 255, 255, 0.06)` | Separadores internos sutiles. |
| `border-border-default` | `rgba(255, 255, 255, 0.10)` | Bordes de tarjetas y paneles estándar. |
| `border-border-strong` | `rgba(255, 255, 255, 0.16)` | Entradas de usuario o estados de foco. |

#### Tipografía (Texto)
| Token Tailwind | Valor Hex | Uso |
|----------------|-----------|-----|
| `text-text-primary` | `#fafafa` | Títulos, cuerpo de texto principal. |
| `text-text-secondary` | `#a1a1aa` | Metadatos, etiquetas secundarias. |
| `text-text-muted` | `#71717a` | Texto deshabilitado, placeholders, íconos inactivos. |

#### Acentos (Acciones y Estados)
| Token Tailwind | Valor Hex | Semántica |
|----------------|-----------|-----------|
| `text-accent-success` | `#10b981` (Emerald) | Confirmaciones, subidas exitosas, botones primarios. |
| `text-accent-warning` | `#f59e0b` (Amber) | Alertas, estados pendientes, atención requerida. |
| `text-accent-danger` | `#ef4444` (Red) | Errores, acciones destructivas. |
| `text-accent-info` | `#67e8f9` (Cyan) | Enlaces, estados de procesamiento, IA. |

### ✒️ Tipografía

| Familia | Fuente | Uso |
|---------|--------|-----|
| **Sans** | `Inter`, sans-serif | UI General, textos, navegación. |
| **Mono** | `JetBrains Mono`, monospace | IDs, Datos numéricos tabulares, Código, Logs. |

### 🌑 Sombras (Glow Effects)

Se utilizan sombras de color (glows) sutiles para indicar interactividad o éxito.

- **Success Glow**: `shadow-glow-success` (`0 0 12px rgba(16, 185, 129, 0.25)`)
- **Hover Glow**: `shadow-glow-hover` (`0 0 20px rgba(16, 185, 129, 0.15)`)

---

## 2. Componentes Atómicos

Estos son los bloques de construcción básicos de la interfaz. Actualmente implementados mediante clases de utilidad en línea o funciones auxiliares.

### Button
Botones interactivos con estados hover y active.

**Variantes:**
- **Primary**: `bg-accent-success text-white hover:bg-accent-success/90 shadow-glow-success`
- **Secondary/Outline**: `bg-bg-surface border border-border-default hover:bg-bg-hover`
- **Ghost**: `text-text-muted hover:text-text-primary hover:bg-bg-elevated`
- **Danger**: `text-red-500 bg-red-500/10 hover:bg-red-500/20`

### Input (Text & Search)
Campos de entrada con estilos consistentes.

**Clases Base:**
```css
bg-bg-surface border border-border-default rounded-lg text-text-primary
focus:outline-none focus:border-accent-success/50 focus:ring-1 focus:ring-accent-success/50
```

### StatusPill
Indicador visual de estado. Utiliza fondos transparentes con bordes y texto de color.

**Props:**
- `status`: string ('ready' | 'processing' | 'failed' | 'pending')

**Variantes Visuales:**
- **Ready/Approved**: `bg-emerald-500/10 text-emerald-500 border-emerald-500/20`
- **Processing/Info**: `bg-cyan-500/10 text-cyan-400 border-cyan-500/20`
- **Failed/Rejected**: `bg-red-500/10 text-red-500 border-red-500/20`
- **Pending/Warning**: `bg-amber-500/10 text-amber-500 border-amber-500/20`

### Iconography
Se utiliza la librería **Lucide React**.
- Tamaño estándar: `w-4 h-4` o `w-5 h-5`.
- Colores: Heredan del texto padre o usan clases de utilidad específicas (ej. `text-accent-info`).

---

## 3. Componentes Compuestos

Componentes de mayor nivel ubicados en `src/components/`.

### Sidebar
Navegación lateral izquierda persistente.
- **Ubicación**: `components/Sidebar.tsx`
- **Características**:
  - Logo de marca con glow.
  - Links de navegación con estado activo (`NavLink`).
  - Perfil de usuario minimizado en la parte inferior.
- **Variantes**: Colapsable en móvil (actualmente oculta en breakpoint `md`).

### Topbar
Barra superior global.
- **Ubicación**: `components/Topbar.tsx`
- **Características**:
  - Barra de búsqueda global con atajo `Cmd+K`.
  - Botón de acción rápida "Upload" (+).
  - Toggle de tema (Sol/Luna).
  - Notificaciones.
- **Behavior**: `sticky top-0` con `backdrop-blur` para efecto de cristal.

### FileDropzone
Área de carga de archivos con soporte Drag & Drop.
- **Ubicación**: `components/FileDropzone.tsx`
- **Props**:
  - `onFilesAccepted`: `(files: File[]) => void`
- **Estados**:
  - **Idle**: Borde dashed gris.
  - **DragOver**: Borde y fondo verde (`accent-success`) con glow.
  - **Uploading**: Muestra lista de archivos con barra de progreso simulada.

### Drawer (Panel Lateral)
Utilizado para mostrar detalles de archivos o aprobaciones sin salir del contexto.
- **Implementación**: En línea en `FilesPage.tsx` y `ApprovalsPage.tsx`.
- **Animación**: `animate-in slide-in-from-right duration-300`.
- **Estructura**: Header con botón cerrar, cuerpo con scroll, footer con acciones.

### Chat Message Bubble
Componente de mensaje en la interfaz de chat.
- **Implementación**: En línea en `ChatPage.tsx`.
- **Variantes**:
  - **User**: Alineado derecha, `bg-bg-active`, borde `rounded-tr-sm`.
  - **Assistant**: Alineado izquierda, `bg-bg-surface`, borde `rounded-tl-sm`. Incluye sección de fuentes (Source Cards) y acciones (Copy, Thumbs up/down).

---

## 4. Estructura del Proyecto

```
/
├── index.html              # Entry point, Tailwind Config, Fonts
├── index.tsx               # React Mount
├── App.tsx                 # Router & Layout definitions
├── types.ts                # TypeScript Interfaces (Domain Models)
├── constants.tsx           # Mock Data & Configurations
├── DESIGN_SYSTEM.md        # Documentación de diseño
│
├── components/             # Componentes Reutilizables
│   ├── Sidebar.tsx         # Navegación Principal
│   ├── Topbar.tsx          # Header Global
│   └── FileDropzone.tsx    # Uploader
│
├── pages/                  # Vistas Principales (Rutas)
│   ├── FilesPage.tsx       # Gestión de Documentos
│   ├── ChatPage.tsx        # Interfaz Agente Veri
│   ├── ApprovalsPage.tsx   # Flujo de Aprobaciones
│   ├── ReportsPage.tsx     # Visualización de Reportes
│   ├── AuditPage.tsx       # Timeline de Auditoría
│   └── SettingsPage.tsx    # Configuración de Org
│
└── services/
    └── geminiService.ts    # Integración con Google GenAI SDK
```

## 5. Patrones de UX

1.  **Feedback Inmediato**: Todos los botones interactivos tienen estados hover claros.
2.  **Densidad de Información**: Uso extensivo de tablas y listas compactas para datos.
3.  **Fuentes Citadas**: La IA (Veri) siempre muestra tarjetas de fuentes clickables para generar confianza.
4.  **Navegación Contextual**: Uso de Drawers (paneles laterales) para ver detalles mantiene al usuario en la lista principal sin recargar la página.
5.  **Skeleton/Loading**: Se utilizan indicadores de carga (`Loader2` spin) para acciones asíncronas.
