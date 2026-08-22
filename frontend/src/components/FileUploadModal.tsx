import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  X, 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldAlert, 
  ShieldCheck, 
  Loader2, 
  Lock,
  Tag,
  Building2,
  FileCode,
  Info
} from 'lucide-react';
import { User, Department, FileClassification } from '../types';
import { formatFileSize } from '../services/storageService';
import { uploadFile } from '../services/api';

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: User;
  departments: Department[];
  onUploadSuccess: () => void;
}

export const FileUploadModal: React.FC<FileUploadModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  departments,
  onUploadSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [topic, setTopic] = useState('');
  const [departmentId, setDepartmentId] = useState(currentUser.departmentId || departments[0]?.id || '');
  const [classification, setClassification] = useState<FileClassification>('internal');
  const [tagsString, setTagsString] = useState('');
  const [description, setDescription] = useState('');

  // Scanning simulation state
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState<number>(0);
  const [scanError, setScanError] = useState<string | null>(null);
  const [isQuarantinedAlert, setIsQuarantinedAlert] = useState<string | null>(null);

  const isAdmin = currentUser.role === 'system_admin';
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const currentDept = departments.find(d => d.id === departmentId) || departments[0];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (!title) {
        setTitle(selected.name.replace(/\.[^/.]+$/, ''));
      }
      setScanError(null);
      setIsQuarantinedAlert(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0];
      setFile(selected);
      if (!title) {
        setTitle(selected.name.replace(/\.[^/.]+$/, ''));
      }
      setScanError(null);
      setIsQuarantinedAlert(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title.trim()) {
      setScanError('لطفاً فایل و عنوان سند را مشخص نمایید.');
      return;
    }

    setIsScanning(true);
    setScanStep(1);
    setScanError(null);
    setIsQuarantinedAlert(null);

    try {
      const form = new FormData();
      form.append('file', file);
      form.append('title', title.trim());
      form.append('topic', topic.trim() || 'عمومی و سازمانی');
      form.append('group_id', departmentId);
      form.append('classification', classification);
      form.append('description', description.trim());
      form.append('tags', tagsString);
      setScanStep(2);
      const result = await uploadFile(form);
      setScanStep(3);
      setIsScanning(false);
      if (result.file.scan_status === 'quarantined') {
        setIsQuarantinedAlert(result.file.quarantine_reason || 'فایل در قرنطینه قرار گرفت.');
        onUploadSuccess();
      } else {
        onUploadSuccess();
        onClose();
      }
    } catch (err: any) {
      setIsScanning(false);
      setScanError(err.message || 'خطا در بارگذاری فایل');
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
      <div className="bg-white rounded-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 shadow-2xl p-6 space-y-5">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">بارگذاری امن سند و گزارش</h2>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isScanning}
            className="p-1.5 text-slate-400 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Quarantined Warning Alert (If uploaded a dangerous/executable file) */}
        {isQuarantinedAlert && (
          <div className="p-3.5 bg-red-50 rounded-xl border border-red-200 text-xs text-red-800 space-y-2">
            <div className="flex items-center gap-2 font-bold text-red-900">
              <ShieldAlert className="w-4 h-4 text-red-600" />
              <span>فایل به دلیل ریسک امنیتی در وضعیت قرنطینه ثبت شد:</span>
            </div>
            <p className="text-[11px] leading-relaxed">{isQuarantinedAlert}</p>
            <div className="flex justify-end pt-1">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1 bg-red-700 text-white rounded-lg text-xs font-medium hover:bg-red-800"
              >
                متوجه شدم و بستن
              </button>
            </div>
          </div>
        )}

        {/* Scan Error Message */}
        {scanError && (
          <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-900 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{scanError}</span>
          </div>
        )}

        {/* Scanning Progress Overlay / Box */}
        {isScanning && (
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-slate-900">
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                <span>در حال پردازش و ارزیابی امنیتی فایل...</span>
              </span>
              <span className="font-mono text-slate-500">گام {scanStep} از ۳</span>
            </div>

            <div className="space-y-1.5 text-[11px] text-slate-600">
              <div className={`flex items-center gap-2 ${scanStep >= 1 ? 'text-blue-700 font-semibold' : ''}`}>
                <span className={`w-2 h-2 rounded-full ${scanStep >= 1 ? 'bg-blue-600' : 'bg-slate-300'}`}></span>
                <span>۱. اعتبارسنجی نوع فایل و سقف حجم مجاز</span>
              </div>
              <div className={`flex items-center gap-2 ${scanStep >= 2 ? 'text-blue-700 font-semibold' : ''}`}>
                <span className={`w-2 h-2 rounded-full ${scanStep >= 2 ? 'bg-blue-600' : 'bg-slate-300'}`}></span>
                <span>{isAdmin ? '۲. پویش امضای بدافزار با موتور آنتی‌ویروس محلی ClamAV' : '۲. بررسی سلامت فایل'}</span>
              </div>
              <div className={`flex items-center gap-2 ${scanStep >= 3 ? 'text-blue-700 font-semibold' : ''}`}>
                <span className={`w-2 h-2 rounded-full ${scanStep >= 3 ? 'bg-blue-600' : 'bg-slate-300'}`}></span>
                <span>{isAdmin ? '۳. رمزنگاری و ذخیره‌سازی با شناسه تصادفی در والت خارج از وب‌روت' : '۳. ذخیره در مخزن سازمانی'}</span>
              </div>
            </div>
          </div>
        )}

        {/* Main Upload Form */}
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          
          {/* Drag and Drop Zone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
              file 
                ? 'border-blue-600 bg-blue-50/50' 
                : 'border-slate-200 hover:border-blue-600 hover:bg-slate-50'
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
            />
            {file ? (
              <div className="space-y-1">
                <FileText className="w-8 h-8 text-blue-600 mx-auto" />
                <p className="font-bold text-sm text-slate-900">{file.name}</p>
                <p className="text-[11px] text-slate-400 font-mono">{formatFileSize(file.size)}</p>
                <p className="text-[10px] text-blue-600 font-medium pt-1">برای تغییر فایل کلیک کنید</p>
              </div>
            ) : (
              <div className="space-y-1.5">
                <UploadCloud className="w-10 h-10 text-slate-400 mx-auto" />
                <p className="font-bold text-slate-800 text-xs">فایل را به اینجا بکشید یا برای انتخاب کلیک کنید</p>
                <p className="text-[10px] text-slate-400">
                  فرمت‌های مجاز طبق سیاست سامانه (پیشنهاد: PDF, DOCX, XLSX, PPTX, TXT) — سقف: {currentDept?.maxFileSizeMB || 50} مگابایت
                </p>
              </div>
            )}
          </div>

          {/* Title & Topic Inputs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-medium text-slate-600 mb-1">
                عنوان سند / گزارش <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="مثال: صورت وضعیت مالی سه‌ماهه دوم"
                className="w-full bg-slate-100 text-xs text-slate-900 p-2.5 rounded-xl border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden"
              />
            </div>

            <div>
              <label className="block font-medium text-slate-600 mb-1">
                موضوع / دسته‌بندی <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="مثال: گزارش مالی و بودجه"
                className="w-full bg-slate-100 text-xs text-slate-900 p-2.5 rounded-xl border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden"
              />
            </div>
          </div>

          {/* Department & Classification */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-medium text-slate-600 mb-1">واحد سازمانی مربوطه:</label>
              <select
                value={departmentId}
                onChange={(e) => setDepartmentId(e.target.value)}
                className="w-full bg-slate-100 text-xs text-slate-900 p-2.5 rounded-xl border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden"
              >
                {departments.map(d => (
                  <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-medium text-slate-600 mb-1">سطح محرمانگی سند:</label>
              <select
                value={classification}
                onChange={(e) => setClassification(e.target.value as FileClassification)}
                className="w-full bg-slate-100 text-xs text-slate-900 p-2.5 rounded-xl border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden"
              >
                <option value="public">عمومی (قابل مشاهده برای تمام نقش‌ها)</option>
                <option value="internal">سازمانی داخلی (پرسنل داخلی)</option>
                <option value="confidential">محرمانه (مدیران و افراد مجاز)</option>
                <option value="secret">به‌کلی سری (فقط مدیران ارشد)</option>
              </select>
            </div>
          </div>

          {/* Tags */}
          <div>
            <label className="block font-medium text-slate-600 mb-1">برچسب‌ها (با کاما یا فاصله جدا کنید):</label>
            <input
              type="text"
              value={tagsString}
              onChange={(e) => setTagsString(e.target.value)}
              placeholder="مثال: بودجه، صورت مالی، شبکه ایتان، ۱۴۰۵"
              className="w-full bg-slate-100 text-xs text-slate-900 p-2.5 rounded-xl border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block font-medium text-slate-600 mb-1">خلاصه و توضیحات تکمیلی:</label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="توضیحات کوتاه پیرامون محتوای فایل یا گزارش..."
              className="w-full bg-slate-100 text-xs text-slate-900 p-2.5 rounded-xl border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden resize-none"
            />
          </div>

          {/* Footer Actions */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
              <Lock className="w-3.5 h-3.5 text-emerald-600" />
              <span>نگهداری در مخزن سازمانی</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isScanning}
                className="px-4 py-2 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition-colors font-medium"
              >
                انصراف
              </button>

              <button
                type="submit"
                disabled={isScanning || !file}
                className={`px-5 py-2 text-xs text-white rounded-xl font-bold flex items-center gap-2 transition-all shadow-xs ${
                  isScanning || !file 
                    ? 'bg-slate-300 text-slate-500 cursor-not-allowed' 
                    : 'bg-blue-600 hover:bg-blue-700 hover:shadow-md'
                }`}
              >
                {isScanning ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>در حال پویش و ذخیره‌سازی...</span>
                  </>
                ) : (
                  <>
                    <UploadCloud className="w-4 h-4" />
                    <span>بارگذاری و ذخیره امن</span>
                  </>
                )}
              </button>
            </div>
          </div>

        </form>

      </div>
    </div>
  );
};
