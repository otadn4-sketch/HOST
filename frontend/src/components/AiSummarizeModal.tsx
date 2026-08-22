import React, { useEffect, useState } from 'react';
import { X, Sparkles, Bot, Copy, Check, Download, RefreshCw, AlertCircle } from 'lucide-react';
import { FileItem, User } from '../types';
import { formatFileSize } from '../services/storageService';
import { DataApi } from '../services/api';
import { MarkdownView } from './MarkdownView';

interface AiSummarizeModalProps {
  file: FileItem;
  currentUser: User;
  onClose: () => void;
}

export const AiSummarizeModal: React.FC<AiSummarizeModalProps> = ({ file, currentUser, onClose }) => {
  const [mode, setMode] = useState<'executive' | 'technical'>('executive');
  const [summary, setSummary] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const isAdmin = currentUser.role === 'system_admin';

  const fetchSummary = async (selectedMode: 'executive' | 'technical') => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await DataApi.aiSummarize({ file_id: file.id, mode: selectedMode });
      setSummary(data.summary || 'خلاصه‌ای بازگردانده نشد.');
    } catch {
      setError('در تولید خلاصه هوشمند خطایی رخ داد.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary(mode);
  }, [file.id, mode]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60">
      <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                خلاصه‌سازی هوشمند سند
                <span className="text-[10px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Bot className="w-3 h-3" /> طبق پرامپت سازمانی
                </span>
              </h2>
              <p className="text-xs text-slate-500 mt-1">{file.title}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:bg-slate-100 rounded-full"><X className="w-5 h-5" /></button>
        </div>
        <div className="px-6 py-3 bg-slate-50 border-b border-slate-100 flex items-center justify-between text-xs">
          <span>{file.departmentName} • {formatFileSize(file.sizeBytes)}</span>
          <div className="flex bg-white p-1 rounded-xl border border-slate-200">
            <button onClick={() => setMode('executive')} className={`px-3 py-1 rounded-lg ${mode === 'executive' ? 'bg-blue-600 text-white' : ''}`}>چکیده مدیریتی</button>
            <button onClick={() => setMode('technical')} className={`px-3 py-1 rounded-lg ${mode === 'technical' ? 'bg-blue-600 text-white' : ''}`}>تحلیل فنی</button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="py-16 text-center text-sm text-slate-500 flex flex-col items-center gap-2">
              <RefreshCw className="w-6 h-6 animate-spin" />
              در حال نگارش خلاصه...
            </div>
          ) : error ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex gap-2">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          ) : (
            <MarkdownView content={summary} className="text-sm space-y-2" />
          )}
        </div>
        <div className="p-4 border-t border-slate-100 flex justify-end gap-2">
          <button
            onClick={() => { navigator.clipboard.writeText(summary); setCopied(true); }}
            disabled={isLoading || !summary}
            className="px-4 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold flex items-center gap-1"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            کپی
          </button>
          <button
            onClick={() => {
              const extra = isAdmin && file.checksumSha256 ? `\nشناسه یکپارچگی (فقط مدیر): ${file.checksumSha256}` : '';
              const blob = new Blob([`خلاصه سند: ${file.title}\n\n${summary}${extra}`], { type: 'text/plain;charset=utf-8' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `summary_${file.originalName}.txt`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            disabled={isLoading || !summary}
            className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-bold flex items-center gap-1"
          >
            <Download className="w-4 h-4" /> دریافت خلاصه
          </button>
        </div>
      </div>
    </div>
  );
};
