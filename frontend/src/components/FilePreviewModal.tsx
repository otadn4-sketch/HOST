import { useEffect, useState } from 'react';
import { Download, ExternalLink, FileText, Loader2, X } from 'lucide-react';
import { FileItem, User } from '../types';
import { csrfToken } from '../services/api';
import { StorageService } from '../services/storageService';

interface FilePreviewModalProps {
  file: FileItem;
  currentUser: User;
  onClose: () => void;
  onDownload: (file: FileItem) => void;
}

function isImageType(mime: string, name: string) {
  return mime.startsWith('image/') || /\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(name);
}

function isPdfType(mime: string, name: string) {
  return mime.includes('pdf') || name.toLowerCase().endsWith('.pdf');
}

function isTextType(mime: string, name: string) {
  return (
    mime.startsWith('text/') ||
    mime.includes('json') ||
    mime.includes('xml') ||
    /\.(txt|csv|md|json|xml|log)$/i.test(name)
  );
}

export function FilePreviewModal({ file, currentUser, onClose, onDownload }: FilePreviewModalProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let revoked: string | null = null;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setBlobUrl(null);
    setTextContent(null);

    (async () => {
      try {
        const response = await fetch(`/api/files/${file.id}/preview`, {
          credentials: 'include',
          headers: { 'X-CSRF-Token': csrfToken() },
          signal: controller.signal,
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload.detail || 'پیش‌نمایش این فایل در دسترس نیست.');
        }
        const blob = await response.blob();
        if (isTextType(file.mimeType, file.originalName) && blob.size < 2_000_000) {
          setTextContent(await blob.text());
        } else {
          const url = URL.createObjectURL(blob);
          revoked = url;
          setBlobUrl(url);
        }
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'خطا در بارگذاری پیش‌نمایش');
      } finally {
        setLoading(false);
      }
    })();

    return () => {
      controller.abort();
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [file]);

  const canDownload = StorageService.canUserDownloadFile(currentUser, file);
  const showImage = Boolean(blobUrl) && isImageType(file.mimeType, file.originalName);
  const showPdf = Boolean(blobUrl) && isPdfType(file.mimeType, file.originalName);
  const officeLike = /\.(docx?|xlsx?|pptx?)$/i.test(file.originalName);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#3B2114]/40 p-4" onClick={onClose}>
      <div
        className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-[#E8D9C4] bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-[#E8D9C4] bg-[#F7F1E8] px-5 py-3">
          <div className="min-w-0">
            <p className="text-[10px] font-black text-[#8B5A2B]">پیش‌نمایش فایل</p>
            <h3 className="truncate text-sm font-black text-[#4A2C17]">{file.title}</h3>
            <p className="truncate font-mono text-[10px] text-[#6B5344]">{file.originalName}</p>
          </div>
          <div className="flex items-center gap-2">
            {canDownload && (
              <button
                type="button"
                onClick={() => onDownload(file)}
                className="inline-flex items-center gap-1 rounded-lg bg-[#4A2C17] px-3 py-1.5 text-[10px] font-black text-white"
              >
                <Download size={12} /> دانلود
              </button>
            )}
            <button type="button" onClick={onClose} className="rounded-lg p-2 text-[#6B5344] hover:bg-white">
              <X size={16} />
            </button>
          </div>
        </div>
        <div className="min-h-[360px] flex-1 overflow-auto bg-[#fbf7f0] p-4">
          {loading && (
            <div className="flex h-full min-h-[320px] flex-col items-center justify-center gap-2 text-[#6B5344]">
              <Loader2 className="animate-spin" size={28} />
              <p className="text-xs font-bold">در حال بارگذاری پیش‌نمایش…</p>
            </div>
          )}
          {!loading && error && (
            <div className="flex h-full min-h-[320px] flex-col items-center justify-center gap-3 text-center">
              <FileText className="text-[#8B5A2B]" size={36} />
              <p className="text-sm font-bold text-rose-700">{error}</p>
              {canDownload && (
                <button
                  type="button"
                  onClick={() => onDownload(file)}
                  className="inline-flex items-center gap-1 rounded-lg bg-[#4A2C17] px-4 py-2 text-xs font-black text-white"
                >
                  <Download size={14} /> دانلود فایل
                </button>
              )}
            </div>
          )}
          {!loading && !error && textContent !== null && (
            <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-xl border border-[#E8D9C4] bg-white p-4 text-xs leading-6 text-[#4A2C17]">
              {textContent}
            </pre>
          )}
          {!loading && !error && showImage && blobUrl && (
            <img src={blobUrl} alt={file.title} className="mx-auto max-h-[70vh] max-w-full rounded-xl object-contain" />
          )}
          {!loading && !error && showPdf && blobUrl && (
            <iframe title={file.title} src={blobUrl} className="h-[70vh] w-full rounded-xl border border-[#E8D9C4] bg-white" />
          )}
          {!loading && !error && !textContent && !showImage && !showPdf && (
            <div className="flex h-full min-h-[320px] flex-col items-center justify-center gap-3 text-center">
              <ExternalLink className="text-[#8B5A2B]" size={36} />
              <p className="text-sm font-bold text-[#4A2C17]">
                {officeLike
                  ? 'پیش‌نمایش آنلاین برای فایل‌های آفیس در این سامانه فعال نیست. فایل را دانلود کنید.'
                  : 'این نوع فایل در مرورگر پیش‌نمایش ندارد. می‌توانید آن را دانلود کنید.'}
              </p>
              {canDownload && (
                <button
                  type="button"
                  onClick={() => onDownload(file)}
                  className="inline-flex items-center gap-1 rounded-lg bg-[#4A2C17] px-4 py-2 text-xs font-black text-white"
                >
                  <Download size={14} /> دانلود فایل
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
