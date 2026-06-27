"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, File, X, CheckCircle, AlertCircle, Loader2, Files, Sparkles } from "lucide-react";
import { clsx } from "clsx";
import toast from "react-hot-toast";
import { documents as docsApi } from "@/lib/api";
import type { Document } from "@/types";

const ACCEPTED_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/plain": [".txt"],
  "text/markdown": [".md"],
};

const STATUS_ICON: Record<Document["status"], React.ReactNode> = {
  pending: <Loader2 className="h-4 w-4 animate-spin text-gray-400" />,
  processing: <Loader2 className="h-4 w-4 animate-spin text-yellow-400" />,
  ready: <CheckCircle className="h-4 w-4 text-brand-300" />,
  failed: <AlertCircle className="h-4 w-4 text-red-400" />,
};

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface Props {
  onDocumentUploaded?: (doc: Document) => void;
  existingDocs?: Document[];
}

export function DocumentUpload({ onDocumentUploaded, existingDocs = [] }: Props) {
  const [uploading, setUploading] = useState(false);
  const [docs, setDocs] = useState<Document[]>(existingDocs);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;
      setUploading(true);

      for (const file of acceptedFiles) {
        try {
          const doc = await docsApi.upload(file);
          setDocs((prev) => [doc, ...prev]);
          onDocumentUploaded?.(doc);
          toast.success(`"${file.name}" uploaded - processing...`);
        } catch (err: any) {
          toast.error(err.response?.data?.detail ?? `Failed to upload ${file.name}`);
        }
      }
      setUploading(false);
    },
    [onDocumentUploaded]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: 50 * 1024 * 1024,
    disabled: uploading,
  });

  const handleDelete = async (id: string) => {
    try {
      await docsApi.delete(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
      toast.success("Document deleted");
    } catch {
      toast.error("Failed to delete document");
    }
  };

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={clsx(
          "slime-surface cursor-pointer rounded-xl p-6 text-center transition duration-300 focus:outline-none focus:ring-2 focus:ring-brand-400/30",
          isDragActive
            ? "scale-[1.01] border-brand-300/60 bg-brand-500/15"
            : "hover:-translate-y-0.5 hover:border-brand-300/35",
          uploading && "pointer-events-none opacity-60"
        )}
      >
        <input {...getInputProps()} />
        <div className="mx-auto flex h-12 w-12 items-center justify-center slime-mark">
          {uploading ? (
            <Loader2 className="h-6 w-6 animate-spin text-gray-950" />
          ) : isDragActive ? (
            <Sparkles className="h-6 w-6 text-gray-950" />
          ) : (
            <Upload className="h-6 w-6 text-gray-950" />
          )}
        </div>
        <p className="mt-3 text-sm font-semibold text-gray-100">
          {isDragActive ? "Release to feed SLIME AI" : "Drop files or click to upload"}
        </p>
        <p className="mt-1 text-xs leading-5 text-gray-500">PDF, DOCX, TXT, MD - Max 50MB each</p>
      </div>

      {docs.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-wide text-gray-600">
            <Files className="h-3.5 w-3.5" />
            Knowledge files
          </div>
          <ul className="space-y-2">
            {docs.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2.5 transition duration-300 hover:-translate-y-0.5 hover:bg-white/[0.075]"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gray-950/60">
                  <File className="h-4 w-4 text-gray-400" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-200">{doc.original_filename}</p>
                  <p className="text-xs text-gray-500">
                    {formatBytes(doc.file_size_bytes)} -{" "}
                    {doc.chunk_count > 0 ? `${doc.chunk_count} chunks` : doc.status}
                  </p>
                </div>
                {STATUS_ICON[doc.status]}
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="shrink-0 rounded-lg p-1.5 text-gray-600 transition hover:bg-red-500/10 hover:text-red-300"
                  aria-label={`Delete ${doc.original_filename}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
