# Verity MVP - Frontend

React + Vite frontend for Verity document management and AI agent.

## Tech Stack

- **Framework**: React 19 + Vite 6
- **Language**: TypeScript 5.8
- **UI Components**: Lucide React (icons)
- **Charts**: Plotly.js
- **Routing**: React Router v7
- **AI**: Google Gemini API

## Prerequisites

- Node.js 18+ (recommended: 20 LTS)
- npm or pnpm
- Gemini API Key ([get one here](https://aistudio.google.com/app/apikey))

## Quick Start

### 1. Install dependencies

```bash
npm install
```

### 2. Configure environment

Copy `.env.example` to `.env.local`:

```bash
cp .env.example .env.local
```

Edit `.env.local` and set your Gemini API key:

```env
VITE_GEMINI_API_KEY=your-actual-api-key-here
VITE_API_URL=http://localhost:8001
```

### 3. Run development server

```bash
npm run dev
```

Frontend will be available at: `http://localhost:5173`

## Backend Connection

The frontend expects the Verity API backend running on `http://localhost:8001`.

To start the backend:

```bash
cd ..
python -m uvicorn verity.main:app --host 127.0.0.1 --port 8001 --reload
```

Or use the convenience script:

```bash
cd ..
.\start_verity.ps1  # Windows
./start_verity.sh   # Linux/Mac
```

## Available Scripts

- `npm run dev` - Start Vite dev server (hot reload)
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally

## Project Structure

```
frontend/
├── components/       # Reusable UI components
│   ├── Chart/       # Plotly chart wrapper
│   ├── FileDropzone.tsx
│   ├── Sidebar.tsx
│   └── Topbar.tsx
├── pages/           # Route pages
│   ├── LoginPage.tsx
│   ├── ChatPage.tsx
│   ├── FilesPage.tsx
│   └── ...
├── services/        # API client logic
├── constants.tsx    # App-wide constants
├── types.ts         # TypeScript types
└── App.tsx          # Main app component
```

## Design System

See [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) for color palette, typography, and component guidelines.

**Key points**:
- Dark mode by default (grays: `#0f0f12`, `#18181c`, `#1f1f24`)
- Accent colors: Emerald green (`#10b981`), Amber (`#f59e0b`), Red (`#ef4444`)
- **Prohibited**: Saturated blue, purple, indigo
- Icons: Lucide React
- Typography: Inter (sans), JetBrains Mono (mono)

## Troubleshooting

### Port 5173 already in use

Kill the process or use a different port:

```bash
npm run dev -- --port 3000
```

### API connection errors

1. Verify backend is running: `curl http://localhost:8001/health`
2. Check CORS settings in backend
3. Verify `VITE_API_URL` in `.env.local`

### Dependencies not installing

Try clearing cache:

```bash
rm -rf node_modules package-lock.json
npm install
```

## Performance Tips

- **Low-resource machines**: Use `npm run dev -- --host 0.0.0.0` to test on another device
- **Slow builds**: Increase Node memory: `NODE_OPTIONS=--max-old-space-size=4096 npm run build`
- **HMR issues**: Disable file watching exclusions in `vite.config.ts`

## Testing on Another PC

1. Clone repo on target machine
2. `cd verity-mvp/frontend`
3. `npm install`
4. Copy `.env.example` to `.env.local` and configure
5. `npm run dev`

For network access (test on phone/tablet):

```bash
npm run dev -- --host 0.0.0.0
```

Then access via: `http://<your-local-ip>:5173`
