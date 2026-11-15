
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import {
  FileText,
  Upload,
  RefreshCw,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

type DocumentItem = {
  name: string;
  source: string;
  pages: number;
  size_bytes: number;
};

type DocumentManagerProps = {
  onCountChange: (count: number) => void;
};

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function DocumentManager({
  onCountChange,
}: DocumentManagerProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load documents for refresh and after upload.
  const loadDocuments = useCallback(async () => {
    try {
      const response = await fetch("/api/documents", {
        method: "GET",
        cache: "no-store",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load documents.");
      }

      if (!Array.isArray(data)) {
        throw new Error("Unexpected document list response.");
      }

      setDocuments(data);
      onCountChange(data.length);
      setError("");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load documents."
      );
    } finally {
      setLoading(false);
    }
  }, [onCountChange]);

  // Initial document loading.
  // State updates happen after the asynchronous request completes.
  useEffect(() => {
    let cancelled = false;

    fetch("/api/documents", {
      method: "GET",
      cache: "no-store",
    })
      .then(async (response) => {
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Unable to load documents.");
        }

        if (!Array.isArray(data)) {
          throw new Error("Unexpected document list response.");
        }

        return data as DocumentItem[];
      })
      .then((data) => {
        if (cancelled) return;

        setDocuments(data);
        onCountChange(data.length);
      })
      .catch((err: unknown) => {
        if (cancelled) return;

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load documents."
        );
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [onCountChange]);

  // Refresh document list.
  const handleRefresh = () => {
    setLoading(true);
    setError("");
    void loadDocuments();
  };

  // Upload PDF.
  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!selectedFile) {
      setError("Please select a PDF file.");
      return;
    }

    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("The PDF must be 10 MB or smaller.");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    setUploading(true);

    try {
      const response = await fetch("/api/documents", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Document upload failed.");
      }

      setSuccess(
        data.message || "Document uploaded successfully."
      );

      setSelectedFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      await loadDocuments();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Document upload failed."
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      {/* PDF upload form */}
      <form
        onSubmit={handleUpload}
        className="border-b border-slate-100 p-5"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            disabled={uploading}
            onChange={(event) =>
              setSelectedFile(event.target.files?.[0] || null)
            }
            className="min-w-0 flex-1 text-xs text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:text-xs file:font-semibold file:text-blue-700 hover:file:bg-blue-100"
          />

          <button
            type="submit"
            disabled={!selectedFile || uploading}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? (
              <Loader2 size={15} className="animate-spin" />
            ) : (
              <Upload size={15} />
            )}

            {uploading ? "Uploading..." : "Upload PDF"}
          </button>
        </div>

        <p className="mt-2 text-xs text-slate-500">
          PDF files only · Maximum file size: 10 MB
        </p>

        {error && (
          <p className="mt-3 flex items-center gap-2 text-xs text-red-600">
            <AlertCircle size={15} />
            {error}
          </p>
        )}

        {success && (
          <p className="mt-3 flex items-center gap-2 text-xs text-emerald-700">
            <CheckCircle2 size={15} />
            {success}
          </p>
        )}
      </form>

      {/* Document list header */}
      <div className="flex items-center justify-between px-5 py-3">
        <p className="text-xs font-medium text-slate-500">
          Indexed documents
        </p>

        <button
          type="button"
          onClick={handleRefresh}
          disabled={loading || uploading}
          className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-100 disabled:opacity-50"
        >
          <RefreshCw
            size={14}
            className={loading ? "animate-spin" : ""}
          />
          Refresh
        </button>
      </div>

      {/* Loading state */}
      {loading ? (
        <div className="flex items-center justify-center gap-2 px-5 py-10 text-sm text-slate-500">
          <Loader2 size={18} className="animate-spin" />
          Loading documents...
        </div>
      ) : error && documents.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-red-600">
          {error}
        </div>
      ) : documents.length === 0 ? (
        <div className="px-5 py-10 text-center text-sm text-slate-500">
          No documents found. Upload your first PDF.
        </div>
      ) : (
        <div className="divide-y divide-slate-100 px-5">
          {documents.map((doc) => (
            <div
              key={`${doc.source}-${doc.name}`}
              className="flex items-center gap-3 rounded-lg py-4"
            >
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                <FileText size={19} />
              </div>

              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-slate-800">
                  {doc.name}
                </p>

                <p className="mt-1 text-xs text-slate-500">
                  {doc.pages} {doc.pages === 1 ? "page" : "pages"}
                  {" · "}
                  {formatFileSize(doc.size_bytes)}
                </p>
              </div>

              <span
                className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${
                  doc.source === "uploaded"
                    ? "bg-violet-50 text-violet-700"
                    : "bg-emerald-50 text-emerald-700"
                }`}
              >
                {doc.source === "uploaded" ? "Uploaded" : "Sample"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
