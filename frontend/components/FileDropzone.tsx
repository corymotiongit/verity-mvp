import React, { useCallback, useState } from 'react';
import { UploadCloud, File as FileIcon, Loader2, X, Tag, Folder, Plus } from 'lucide-react';
import { formatBytes } from '../constants';

// Categorias predefinidas
const CATEGORIES = [
  { id: 'contrato', label: 'Contratos', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
  { id: 'rrhh', label: 'RRHH', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  { id: 'finanzas', label: 'Finanzas', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  { id: 'legal', label: 'Legal', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  { id: 'operaciones', label: 'Operaciones', color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
];

export interface FileMetadata {
  category?: string;
  project?: string;
  tags?: string[];
}

interface FileDropzoneProps {
  onFilesAccepted: (files: File[], metadata: FileMetadata) => void;
}

const FileDropzone: React.FC<FileDropzoneProps> = ({ onFilesAccepted }) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [uploadingFiles, setUploadingFiles] = useState<File[]>([]);

  // Metadata state
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [project, setProject] = useState<string>('');
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState<string>('');

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files);
      setPendingFiles(prev => [...prev, ...newFiles]);
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setPendingFiles(prev => [...prev, ...newFiles]);
    }
  };

  const addTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags(prev => [...prev, newTag.trim()]);
      setNewTag('');
    }
  };

  const removeTag = (tag: string) => {
    setTags(prev => prev.filter(t => t !== tag));
  };

  const removePendingFile = (index: number) => {
    setPendingFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = () => {
    if (pendingFiles.length === 0) return;

    const metadata: FileMetadata = {
      category: selectedCategory || undefined,
      project: project || undefined,
      tags: tags.length > 0 ? tags : undefined,
    };

    setUploadingFiles(pendingFiles);
    setPendingFiles([]);

    // Call parent with metadata
    onFilesAccepted(pendingFiles, metadata);

    // Clear uploading state after delay (parent handles actual upload)
    setTimeout(() => {
      setUploadingFiles([]);
      // Reset metadata for next upload
      setSelectedCategory('');
      setProject('');
      setTags([]);
    }, 2000);
  };

  return (
    <div className="w-full space-y-4">
      {/* Drop Area */}
      <div
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 cursor-pointer group
          ${isDragActive
            ? 'border-accent-success bg-accent-success/5 shadow-glow-success'
            : 'border-border-default bg-bg-surface hover:bg-bg-hover hover:border-text-muted'}
        `}
      >
        <input
          type="file"
          multiple
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
          onChange={handleFileInput}
        />

        <div className="flex flex-col items-center justify-center space-y-3 pointer-events-none">
          <div className={`p-3 rounded-full ${isDragActive ? 'bg-accent-success/20 text-accent-success' : 'bg-bg-elevated text-text-muted'}`}>
            <UploadCloud className="w-6 h-6" />
          </div>
          <div>
            <p className="text-text-primary font-medium">
              {isDragActive ? "Suelta los archivos aquí" : "Haz clic o arrastra archivos aquí"}
            </p>
            <p className="text-text-muted text-xs mt-1">
              PDF, DOCX, XLSX, TXT, o Imágenes (max 10MB)
            </p>
          </div>
        </div>
      </div>

      {/* Pending Files - Show metadata form */}
      {pendingFiles.length > 0 && (
        <div className="bg-bg-surface border border-border-default rounded-xl p-4 space-y-4">
          {/* Files List */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
              Archivos seleccionados ({pendingFiles.length})
            </h4>
            {pendingFiles.map((file, idx) => (
              <div key={`${file.name}-${idx}`} className="flex items-center justify-between p-2 bg-bg-elevated rounded-lg">
                <div className="flex items-center gap-2">
                  <FileIcon className="w-4 h-4 text-accent-info" />
                  <span className="text-sm text-text-primary truncate max-w-[200px]">{file.name}</span>
                  <span className="text-xs text-text-muted">{formatBytes(file.size)}</span>
                </div>
                <button
                  onClick={() => removePendingFile(idx)}
                  className="p-1 hover:bg-bg-hover rounded text-text-muted hover:text-red-400"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>

          {/* Category Selection */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wider flex items-center gap-1">
              <Tag className="w-3 h-3" /> Categoría
            </label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map(cat => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(selectedCategory === cat.id ? '' : cat.id)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-all ${selectedCategory === cat.id
                      ? cat.color
                      : 'bg-bg-elevated text-text-muted border-border-default hover:border-text-muted'
                    }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* Project Input */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wider flex items-center gap-1">
              <Folder className="w-3 h-3" /> Proyecto (opcional)
            </label>
            <input
              type="text"
              value={project}
              onChange={e => setProject(e.target.value)}
              placeholder="Nombre del proyecto..."
              className="w-full px-3 py-2 bg-bg-elevated border border-border-default rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:border-accent-info focus:outline-none"
            />
          </div>

          {/* Tags Input */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wider">
              Etiquetas (opcional)
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {tags.map(tag => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-bg-active text-text-primary text-xs rounded-full"
                >
                  {tag}
                  <button onClick={() => removeTag(tag)} className="hover:text-red-400">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={newTag}
                onChange={e => setNewTag(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addTag())}
                placeholder="Agregar etiqueta..."
                className="flex-1 px-3 py-2 bg-bg-elevated border border-border-default rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:border-accent-info focus:outline-none"
              />
              <button
                onClick={addTag}
                className="px-3 py-2 bg-bg-elevated border border-border-default rounded-lg text-text-muted hover:text-text-primary hover:border-text-muted transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            className="w-full py-2.5 bg-accent-success text-bg-base font-medium rounded-lg hover:shadow-glow-success transition-all flex items-center justify-center gap-2"
          >
            <UploadCloud className="w-4 h-4" />
            Subir {pendingFiles.length} archivo{pendingFiles.length > 1 ? 's' : ''}
          </button>
        </div>
      )}

      {/* Uploading State */}
      {uploadingFiles.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">Subiendo</h4>
          {uploadingFiles.map((file, idx) => (
            <div key={`${file.name}-${idx}`} className="flex items-center justify-between p-3 bg-bg-surface border border-border-default rounded-lg">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-bg-elevated rounded">
                  <FileIcon className="w-4 h-4 text-accent-info" />
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-text-primary">{file.name}</span>
                  <span className="text-xs text-text-muted">{formatBytes(file.size)}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-24 h-1 bg-bg-elevated rounded-full overflow-hidden">
                  <div className="h-full bg-cyan-400 w-2/3 animate-pulse"></div>
                </div>
                <Loader2 className="w-4 h-4 animate-spin text-text-muted" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FileDropzone;