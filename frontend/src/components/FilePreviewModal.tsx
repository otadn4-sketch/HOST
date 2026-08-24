import React, { useEffect, useState } from 'react';
import { ExternalLink, FileText, Loader2, X } from 'lucide-react';
import { FileItem, User } from '../types';
import { csrfToken, DataApi } from '../services/api';

interface FilePreviewModalProps {
  file: FileItem;
  currentUser: User;
  onClose: () => void;
  onDownload?: (file: FileItem) => void;
}

function isOfficeType(mime: string, name: string) {
  const m = (mime || '').toLowerCase();
  const n = (name || '').toLowerCase();
  if (
    m.includes('officedocument') ||
    m.includes('msword') ||
    m.includes('ms-excel') ||
    m.includes('ms-powerpoint') ||
    m.includes('opendocument')
  ) {
    return true;
  }
  return /\.(docx?|xlsx?|pptx?|odt|ods|odp)$/i.test(n);
}

function isImageType(mime: string, name: string) {
  return mime.startsWith('image/') || /\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(name);
}

function isPdfType(mime: string, name: string) {
  return mime.includes('pdf') || name.toLowerCase().endsWith('.pdf');
}

function isTextType(mime: string, name: string) {
  if (isOfficeType(mime, name)) return false;
  return (
    mime.startsWith('text/') ||
    mime.includes('json') ||
    (mime.includes('xml') && !mime.includes('openxml')) ||
    /\.(txt|csv|md|json|xml|log)$/i.test(name)
  );
}

function looksLikeZipGarbage(text: string) {
  return text.startsWith('PK') && text.includes('[Content_Types].xml');
}

function blockCopy(event: React.ClipboardEvent | React.MouseEvent | KeyboardEvent) {
  event.preventDefault();
  event.stopPropagation();
}

export function FilePreviewModal({ file, onClose }: FilePreviewModalProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [extracted, setExtracted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let revoked: string | null = null;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setBlobUrl(null);
    setTextContent(null);
    setExtracted(false);

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
        const previewKind = (response.headers.get('x-eytan-preview') || '').toLowerCase();
        const contentType = (response.headers.get('content-type') || '').toLowerCase();
        const blob = await response.blob();
        const treatAsText =
          previewKind === 'extracted-text' ||
          contentType.includes('text/plain') ||
          (isTextType(file.mimeType, file.originalName) && blob.size < 2_000_000);
        if (treatAsText) {
          const text = await blob.text();
          if (looksLikeZipGarbage(text)) {
            return;
          }
          setExtracted(previewKind === 'extracted-text');
          setTextContent(text);
          return;
        }
        if (isOfficeType(file.mimeType, file.originalName)) {
          return;
        }
        const url = URL.createObjectURL(blob);
        revoked = url;
        setBlobUrl(url);
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

  useEffect(() => {
    const sessionId = `${file.id}-${Date.now()}`;
    const beat = () => {
      DataApi.previewHeartbeat(file.id, sessionId).catch(() => undefined);
    };
    beat();
    const timer = window.setInterval(beat, 15000);
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && ['c', 'C', 'x', 'X', 's', 'S', 'p', 'P'].includes(event.key)) {
        event.preventDefault();
      }
    };
    document.addEventListener('keydown', onKey, true);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('keydown', onKey, true);
    };
  }, [file.id]);

  const showImage = Boolean(blobUrl) && isImageType(file.mimeType, file.originalName);
  const showPdf = Boolean(blobUrl) && isPdfType(file.mimeType, file.originalName);
  const officeLike = isOfficeType(file.mimeType, file.originalName);

  return (
    <div className="fixed inset-0 z-50 flex items-stretch sm:items-center justify-center bg-[#3B2114]/40 p-0 sm:p-4" onClick={onClose}>
      <div
        className="preview-irzar flex h-full sm:h-auto max-h-none sm:max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-none sm:rounded-2xl border-0 sm:border border-[#E8D9C4] bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
        onCopy={blockCopy}
        onCut={blockCopy}
        onContextMenu={blockCopy}
      >
        <div className="flex items-center justify-between border-b border-[#E8D9C4] bg-[#F7F1E8] px-5 py-3">
          <div className="min-w-0">
            <p className="text-[10px] font-black text-[#8B5A2B]">پیش‌نمایش فایل</p>
            <h3 className="truncate text-sm font-black text-[#4A2C17]">{file.title}</h3>
            <p className="truncate font-mono text-[10px] text-[#6B5344]">{file.originalName}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-[#6B5344] hover:bg-white">
            <X size={16} />
          </button>
        </div>
        <div
          className="min-h-[360px] flex-1 overflow-auto bg-[#fbf7f0] p-4"
          onCopy={blockCopy}
          onCut={blockCopy}
          onContextMenu={blockCopy}
          style={{ userSelect: 'none', WebkitUserSelect: 'none' }}
        >
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
            </div>
          )}
          {!loading && !error && textContent !== null && (
            <div className="space-y-2">
              {extracted && (
                <p className="text-[11px] font-bold text-[#8B5A2B]">متن استخراج‌شده از فایل آفیس (پیش‌نمایش — کپی غیرفعال است)</p>
              )}
              <pre
                className="preview-irzar max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-xl border border-[#E8D9C4] bg-white p-4 text-sm leading-8 text-[#4A2C17]"
                onCopy={blockCopy}
                onCut={blockCopy}
                onContextMenu={blockCopy}
              >
                {textContent}
              </pre>
            </div>
          )}
          {!loading && !error && showImage && blobUrl && (
            <img src={blobUrl} alt={file.title} draggable={false} className="mx-auto max-h-[70vh] max-w-full rounded-xl object-contain" />
          )}
          {!loading && !error && showPdf && blobUrl && (
            <div className="relative h-[70vh] w-full" onContextMenu={blockCopy}>
              <iframe
                title={file.title}
                src={`${blobUrl}#toolbar=0&navpanes=0&scrollbar=0&download=0`}
                className="h-full w-full rounded-xl border border-[#E8D9C4] bg-white"
              />
              <p className="mt-2 text-center text-[11px] text-[#6B5344]">دانلود از پیش‌نمایش پی‌دی‌اف غیرفعال است. فقط مجوزهای سامانه اعمال می‌شود.</p>
            </div>
          )}
          {!loading && !error && !textContent && !showImage && !showPdf && (
            <div className="flex h-full min-h-[320px] flex-col items-center justify-center gap-3 text-center">
              <ExternalLink className="text-[#8B5A2B]" size={36} />
              <p className="text-sm font-bold text-[#4A2C17]">
                {officeLike
                  ? 'متن قابل‌استخراج در این فایل آفیس پیدا نشد. دانلود از پیش‌نمایش مجاز نیست.'
                  : 'این نوع فایل در مرورگر پیش‌نمایش ندارد. دانلود فقط از مسیر مجاز سامانه انجام می‌شود.'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
