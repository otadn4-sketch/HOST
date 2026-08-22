import React, { useState, useMemo, useEffect } from 'react';
import { 
  FileText, 
  Download, 
  Eye, 
  Trash2, 
  ShieldAlert, 
  ShieldCheck, 
  Lock, 
  Filter, 
  Search, 
  Grid, 
  List, 
  Check, 
  Copy, 
  Info, 
  Clock, 
  User as UserIcon, 
  Building2, 
  Tag, 
  AlertCircle,
  FileCode,
  FileSpreadsheet,
  FileArchive,
  FileCheck2,
  FileWarning,
  ExternalLink,
  ChevronLeft,
  X,
  Sparkles,
  Pencil
} from 'lucide-react';
import { FileItem, User, Department, FileClassification } from '../types';
import { StorageService, formatFileSize, formatDateTimeFa } from '../services/storageService';
import { DataApi, downloadFile, mapFile } from '../services/api';
import { AiSummarizeModal } from './AiSummarizeModal';
import { FileAccessEditor } from './FileAccessEditor';

interface FileRepositoryProps {
  files: FileItem[];
  currentUser: User;
  departments: Department[];
  users?: User[];
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onRefresh: () => void;
  initialFileId?: string | null;
}

export const FileRepository: React.FC<FileRepositoryProps> = ({
  files,
  currentUser,
  departments,
  users = [],
  searchQuery,
  onSearchChange,
  onRefresh,
  initialFileId,
}) => {
  const isAdmin = currentUser.role === 'system_admin';
  const [selectedDept, setSelectedDept] = useState<string>('all');
  const [selectedTopic, setSelectedTopic] = useState<string>('all');
  const [selectedClassification, setSelectedClassification] = useState<string>('all');
  const [selectedScanStatus, setSelectedScanStatus] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [summarizingFile, setSummarizingFile] = useState<FileItem | null>(null);
  const [editingFile, setEditingFile] = useState<FileItem | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (!initialFileId) return;
    const found = files.find((f) => f.id === initialFileId);
    if (found) {
      setSelectedFile(found);
    }
  }, [initialFileId, files]);

  // Extract unique topics
  const topics = useMemo(() => {
    const set = new Set<string>();
    files.forEach(f => {
      if (f.topic) set.add(f.topic);
    });
    return Array.from(set);
  }, [files]);

  // Filter files
  const filteredFiles = useMemo(() => {
    return files.filter(file => {
      // Role permission filter: Viewers and users only see files they are authorized for
      const canView = StorageService.canUserViewFile(currentUser, file);
      if (!canView) return false;

      // Text search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matches = 
          file.title.toLowerCase().includes(q) ||
          file.originalName.toLowerCase().includes(q) ||
          file.topic.toLowerCase().includes(q) ||
          file.uploaderName.toLowerCase().includes(q) ||
          (isAdmin && file.checksumSha256.toLowerCase().includes(q)) ||
          (file.tags && file.tags.some(t => t.toLowerCase().includes(q)));
        if (!matches) return false;
      }

      // Department filter
      if (selectedDept !== 'all' && file.departmentId !== selectedDept) return false;

      // Topic filter
      if (selectedTopic !== 'all' && file.topic !== selectedTopic) return false;

      // Classification filter
      if (selectedClassification !== 'all' && file.classification !== selectedClassification) return false;

      // Scan status filter
      if (selectedScanStatus !== 'all' && file.scanStatus !== selectedScanStatus) return false;

      return true;
    });
  }, [files, currentUser, searchQuery, selectedDept, selectedTopic, selectedClassification, selectedScanStatus, isAdmin]);

  const handleDownload = async (file: FileItem, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      await downloadFile(file.id, file.originalName);
      setFeedbackMessage({ type: 'success', text: `فایل «${file.title}» دریافت شد.` });
      onRefresh();
    } catch {
      setFeedbackMessage({ type: 'error', text: 'دریافت فایل مجاز نیست یا فایل قرنطینه است.' });
    }
    setTimeout(() => setFeedbackMessage(null), 4000);
  };

  const handleDelete = async (file: FileItem, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!window.confirm(`آیا از حذف دائمی فایل «${file.title}» از والت اطمینان دارید؟`)) return;
    try {
      await DataApi.deleteFile(file.id);
      setFeedbackMessage({ type: 'success', text: 'فایل حذف شد.' });
      if (selectedFile?.id === file.id) setSelectedFile(null);
      onRefresh();
    } catch {
      setFeedbackMessage({ type: 'error', text: 'حذف فایل مجاز نیست.' });
    }
    setTimeout(() => setFeedbackMessage(null), 4000);
  };

  const handleToggleQuarantine = (_file: FileItem) => {
    setFeedbackMessage({ type: 'error', text: 'خروج دستی از قرنطینه پس از اسکن آلوده مجاز نیست؛ فایل مشکوک قابل دریافت نیست.' });
    setTimeout(() => setFeedbackMessage(null), 4000);
  };

  const handleOpenFileDetails = async (file: FileItem) => {
    try {
      const res = await DataApi.file(file.id);
      setSelectedFile(mapFile(res.file));
    } catch {
      setSelectedFile(file);
    }
    onRefresh();
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const getFileIcon = (ext: string, isQuarantined: boolean) => {
    if (isQuarantined) return FileWarning;
    const lower = ext.toLowerCase();
    if (lower === 'pdf') return FileText;
    if (['xlsx', 'xls', 'csv'].includes(lower)) return FileSpreadsheet;
    if (['docx', 'doc', 'txt'].includes(lower)) return FileText;
    if (['zip', 'rar', 'tar', 'gz'].includes(lower)) return FileArchive;
    if (['sh', 'bat', 'exe'].includes(lower)) return FileCode;
    return FileText;
  };

  const getClassificationBadge = (c: FileClassification) => {
    switch (c) {
      case 'public':
        return { label: 'عمومی', class: 'bg-slate-100 text-slate-700 border-slate-200' };
      case 'internal':
        return { label: 'سازمانی داخلی', class: 'bg-blue-50 text-blue-800 border-blue-200' };
      case 'confidential':
        return { label: 'محرمانه', class: 'bg-amber-50 text-amber-800 border-amber-200' };
      case 'secret':
        return { label: 'به‌کلی سری', class: 'bg-red-50 text-red-800 border-red-200' };
      default:
        return { label: c, class: 'bg-slate-100 text-slate-700' };
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Toast Feedback Notification */}
      {feedbackMessage && (
        <div className={`p-4 rounded-xl text-xs font-medium flex items-center justify-between shadow-xs transition-all ${
          feedbackMessage.type === 'success' 
            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' 
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          <div className="flex items-center gap-2">
            {feedbackMessage.type === 'success' ? <FileCheck2 className="w-4 h-4 text-emerald-600" /> : <AlertCircle className="w-4 h-4 text-red-600" />}
            <span>{feedbackMessage.text}</span>
          </div>
          <button onClick={() => setFeedbackMessage(null)} className="text-xs hover:opacity-75">✕</button>
        </div>
      )}

      {/* Header & Filter Toolbar */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              <span>مخزن فایل‌ها، گزارش‌ها و اسناد امن</span>
            </h1>
          </div>

          {/* View Mode Toggle & Result Count */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
              تعداد فایل‌های در دسترس: <strong className="text-slate-900 font-bold">{filteredFiles.length}</strong>
            </span>
            <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200">
              <button
                onClick={() => setViewMode('table')}
                className={`p-1.5 rounded-md transition-colors ${viewMode === 'table' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'}`}
                title="نمایش جدولی"
              >
                <List className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded-md transition-colors ${viewMode === 'grid' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'}`}
                title="نمایش کارتی"
              >
                <Grid className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Filter Dropdowns Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 pt-3 border-t border-slate-100">
          
          {/* Department Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-500 mb-1">واحد سازمانی / گروه:</label>
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="w-full bg-slate-100 text-xs text-slate-800 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden"
            >
              <option value="all">همه واحدها</option>
              {departments.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>

          {/* Topic Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-500 mb-1">موضوع / دسته‌بندی:</label>
            <select
              value={selectedTopic}
              onChange={(e) => setSelectedTopic(e.target.value)}
              className="w-full bg-slate-100 text-xs text-slate-800 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden"
            >
              <option value="all">همه موضوعات</option>
              {topics.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {/* Classification Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-500 mb-1">سطح محرمانگی:</label>
            <select
              value={selectedClassification}
              onChange={(e) => setSelectedClassification(e.target.value)}
              className="w-full bg-slate-100 text-xs text-slate-800 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden"
            >
              <option value="all">همه سطوح</option>
              <option value="public">عمومی</option>
              <option value="internal">سازمانی داخلی</option>
              <option value="confidential">محرمانه</option>
              <option value="secret">به‌کلی سری</option>
            </select>
          </div>

          {/* Antivirus Scan Filter — admin only */}
          {isAdmin && (
          <div>
            <label className="block text-[11px] font-medium text-slate-500 mb-1">وضعیت پویش و سلامت:</label>
            <select
              value={selectedScanStatus}
              onChange={(e) => setSelectedScanStatus(e.target.value)}
              className="w-full bg-slate-100 text-xs text-slate-800 p-2 rounded-lg border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden"
            >
              <option value="all">همه وضعیت‌ها</option>
              <option value="clean">سالم و تأییدشده (Clean)</option>
              <option value="quarantined">قرنطینه / مسدود (Quarantined)</option>
            </select>
          </div>
          )}

        </div>

      </div>

      {/* Main Content Area: Table View or Grid View */}
      {filteredFiles.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 border border-slate-200 text-center space-y-3 shadow-sm">
          <FileText className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="text-sm font-bold text-slate-900">هیچ فایلی مطابق با فیلترهای انتخابی یافت نشد</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            لطفاً عبارت جست‌وجو یا فیلترهای واحد سازمانی و موضوع را تغییر دهید یا فایل جدیدی بارگذاری نمایید.
          </p>
        </div>
      ) : viewMode === 'table' ? (
        
        /* Table Layout */
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-right text-xs">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200 font-medium">
                <tr>
                  <th className="p-3.5 pr-6 font-medium">عنوان سند و گزارش</th>
                  <th className="p-3.5 font-medium">موضوع</th>
                  <th className="p-3.5 font-medium">واحد سازمانی</th>
                  <th className="p-3.5 font-medium">حجم / نوع</th>
                  <th className="p-3.5 font-medium">سطح محرمانگی</th>
                  {isAdmin && <th className="p-3.5 font-medium">پویش ClamAV</th>}
                  <th className="p-3.5 font-medium">تاریخ و کاربر</th>
                  <th className="p-3.5 pl-6 text-center font-medium">عملیات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredFiles.map((file) => {
                  const isQuarantined = file.scanStatus === 'quarantined';
                  const Icon = getFileIcon(file.extension, isQuarantined);
                  const classBadge = getClassificationBadge(file.classification);
                  const canDownload = StorageService.canUserDownloadFile(currentUser, file);
                  const canManage = StorageService.canUserManageFile(currentUser, file);

                  return (
                    <tr
                      key={file.id}
                      onClick={() => handleOpenFileDetails(file)}
                      className={`hover:bg-slate-50 cursor-pointer transition-colors ${
                        isQuarantined ? 'bg-red-50/40' : ''
                      }`}
                    >
                      <td className="p-3.5 pr-6">
                        <div className="flex items-center gap-3">
                          <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                            isQuarantined ? 'bg-red-100 text-red-700' : 'bg-blue-50 text-blue-700'
                          }`}>
                            <Icon className="w-5 h-5" />
                          </div>
                          <div className="max-w-xs">
                            <p className="font-bold text-slate-900 hover:text-blue-600 line-clamp-1">
                              {file.title}
                            </p>
                            <p className="text-[10px] text-slate-400 font-mono mt-0.5 line-clamp-1">
                              {file.originalName}
                            </p>
                          </div>
                        </div>
                      </td>

                      <td className="p-3.5">
                        <span className="text-[11px] font-medium text-slate-700 bg-slate-100 px-2.5 py-0.5 rounded-md">
                          {file.topic}
                        </span>
                      </td>

                      <td className="p-3.5 text-slate-600">
                        {file.departmentName}
                      </td>

                      <td className="p-3.5 text-slate-600 font-mono text-[11px]">
                        <span>{formatFileSize(file.sizeBytes)}</span>
                        <span className="text-[10px] text-slate-400 mr-1.5 uppercase">({file.extension})</span>
                      </td>

                      <td className="p-3.5">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${classBadge.class}`}>
                          {classBadge.label}
                        </span>
                      </td>

                      {isAdmin && (
                      <td className="p-3.5">
                        {isQuarantined ? (
                          <span className="text-[10px] bg-red-100 text-red-700 border border-red-200 px-2 py-0.5 rounded-full font-bold flex items-center gap-1 w-fit">
                            <ShieldAlert className="w-3 h-3" />
                            <span>قرنطینه بدافزار</span>
                          </span>
                        ) : (
                          <span className="text-[10px] bg-green-100 text-green-700 border border-green-200 px-2 py-0.5 rounded-full font-medium flex items-center gap-1 w-fit">
                            <ShieldCheck className="w-3 h-3" />
                            <span>سالم و ایمن</span>
                          </span>
                        )}
                      </td>
                      )}

                      <td className="p-3.5 text-[11px] text-slate-500">
                        <p>{formatDateTimeFa(file.createdAt)}</p>
                        <p className="text-[10px] text-slate-400">{file.uploaderName}</p>
                      </td>

                      <td className="p-3.5 pl-6 text-center">
                        <div className="flex items-center justify-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={(e) => { e.stopPropagation(); setSummarizingFile(file); }}
                            className="p-1.5 text-blue-700 bg-blue-50 hover:bg-blue-600 hover:text-white rounded-lg border border-blue-200/60"
                            title="خلاصه‌سازی هوشمند"
                          >
                            <Sparkles className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleOpenFileDetails(file)}
                            className="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-slate-100 rounded-lg transition-colors"
                            title="مشاهده جزئیات"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {canManage && (
                            <button
                              onClick={(e) => { e.stopPropagation(); setEditingFile(file); }}
                              className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-lg"
                              title="ویرایش و سطوح دسترسی"
                            >
                              <Pencil className="w-4 h-4" />
                            </button>
                          )}

                          {/* Download Button */}
                          {canDownload && !isQuarantined ? (
                            <button
                              onClick={(e) => handleDownload(file, e)}
                              className="p-1.5 text-blue-600 hover:text-white hover:bg-blue-600 rounded-lg transition-colors"
                              title="دریافت امن با بررسی توکن"
                            >
                              <Download className="w-4 h-4" />
                            </button>
                          ) : (
                            <span 
                              className="p-1.5 text-slate-300 cursor-not-allowed" 
                              title={isQuarantined ? 'فایل در قرنطینه است' : 'عدم دسترسی به دریافت'}
                            >
                              <Lock className="w-4 h-4" />
                            </span>
                          )}

                          {/* Admin delete */}
                          {canManage && (
                            <button
                              onClick={(e) => handleDelete(file, e)}
                              className="p-1.5 text-red-500 hover:text-white hover:bg-red-600 rounded-lg transition-colors"
                              title="حذف دائمی فایل"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}

                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

      ) : (

        /* Grid Layout */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredFiles.map((file) => {
            const isQuarantined = file.scanStatus === 'quarantined';
            const Icon = getFileIcon(file.extension, isQuarantined);
            const classBadge = getClassificationBadge(file.classification);
            const canDownload = StorageService.canUserDownloadFile(currentUser, file);
            const canManage = StorageService.canUserManageFile(currentUser, file);

            return (
              <div
                key={file.id}
                onClick={() => handleOpenFileDetails(file)}
                className={`bg-white rounded-2xl p-5 border border-slate-200 hover:border-slate-300 shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col justify-between space-y-4 ${
                  isQuarantined ? 'border-red-200 bg-red-50/20' : ''
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      isQuarantined ? 'bg-red-100 text-red-700' : 'bg-blue-50 text-blue-700'
                    }`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${classBadge.class}`}>
                      {classBadge.label}
                    </span>
                  </div>

                  <div>
                    <h3 className="font-bold text-sm text-slate-900 line-clamp-1 hover:text-blue-600">
                      {file.title}
                    </h3>
                    <p className="text-[11px] text-slate-400 font-mono mt-0.5 line-clamp-1">
                      {file.originalName}
                    </p>
                  </div>

                  <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
                    {file.description || 'گزارش رسمی با ثبت یکپارچگی داده و بررسی‌های امنیتی.'}
                  </p>

                  <div className="flex flex-wrap gap-1">
                    {file.tags && file.tags.map(t => (
                      <span key={t} className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md">
                        #{t}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                  <div>
                    <p className="font-semibold text-slate-900 text-[11px]">{file.departmentName}</p>
                    <p className="text-[10px] font-mono text-slate-400">{formatFileSize(file.sizeBytes)}</p>
                  </div>

                  <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={(e) => { e.stopPropagation(); setSummarizingFile(file); }}
                      className="px-2.5 py-1.5 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded-lg flex items-center gap-1"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      خلاصه
                    </button>
                    {canManage && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setEditingFile(file); }}
                        className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-lg"
                        title="ویرایش"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                    )}
                    {canDownload && !isQuarantined ? (
                      <button
                        onClick={(e) => handleDownload(file, e)}
                        className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-1 transition-colors font-medium shadow-xs"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>دریافت</span>
                      </button>
                    ) : (
                      <span className="text-[10px] text-slate-400 flex items-center gap-1 bg-slate-100 px-2 py-1 rounded-lg">
                        <Lock className="w-3 h-3" />
                        <span>محدود</span>
                      </span>
                    )}

                    {canManage && (
                      <button
                        onClick={(e) => handleDelete(file, e)}
                        className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        title="حذف فایل"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>

              </div>
            );
          })}
        </div>
      )}

      {/* File Details Drawer / Modal */}
      {selectedFile && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 shadow-2xl p-6 space-y-5">
            
            {/* Header */}
            <div className="flex items-start justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
                  selectedFile.scanStatus === 'quarantined' ? 'bg-red-100 text-red-700' : 'bg-blue-50 text-blue-700'
                }`}>
                  {React.createElement(getFileIcon(selectedFile.extension, selectedFile.scanStatus === 'quarantined'), { className: 'w-6 h-6' })}
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900 leading-tight">
                    {selectedFile.title}
                  </h2>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">
                    {selectedFile.originalName} • نسخه {selectedFile.version}
                  </p>
                </div>
              </div>

              <button
                onClick={() => setSelectedFile(null)}
                className="p-1.5 text-slate-400 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Antivirus Scan Alert — admin only */}
            {isAdmin && (
              selectedFile.scanStatus === 'quarantined' ? (
              <div className="p-3.5 bg-red-50 rounded-xl border border-red-200 text-xs text-red-800 flex items-start gap-3">
                <ShieldAlert className="w-5 h-5 shrink-0 text-red-600 mt-0.5" />
                <div>
                  <p className="font-bold text-red-900">هشدار امنیتی: فایل در قرنطینه است</p>
                  <p className="mt-1 leading-relaxed">{selectedFile.quarantineReason}</p>
                </div>
              </div>
            ) : (
              <div className="p-3.5 bg-emerald-50 rounded-xl border border-emerald-200 text-xs text-emerald-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-600" />
                  <div>
                    <p className="font-bold">تأییدیه پویش امنیتی ClamAV</p>
                    <p className="text-[11px] text-emerald-700">بررسی کامل امضای بدافزار و اعتبارسنجی فرمت فایل انجام شد.</p>
                  </div>
                </div>
                <span className="text-[10px] font-mono bg-white px-2 py-1 rounded text-emerald-800 border border-emerald-200">
                  وضعیت: Clean
                </span>
              </div>
            )
            )}
            {!isAdmin && selectedFile.scanStatus === 'quarantined' && (
              <div className="p-3.5 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-800">
                این فایل در حال حاضر قابل دریافت نیست.
              </div>
            )}

            {/* Description */}
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">شرح و خلاصه سند:</label>
              <p className="text-xs text-slate-800 bg-slate-50 p-3.5 rounded-xl border border-slate-100 leading-relaxed">
                {selectedFile.description || 'توضیحات تکمیلی برای این سند ثبت نشده است.'}
              </p>
            </div>

            {/* Metadata Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block text-[10px]">موضوع گزارش:</span>
                <span className="font-bold text-slate-900 mt-0.5 block">{selectedFile.topic}</span>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block text-[10px]">واحد سازمانی:</span>
                <span className="font-bold text-slate-900 mt-0.5 block">{selectedFile.departmentName}</span>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block text-[10px]">سطح محرمانگی:</span>
                <span className="font-bold text-slate-900 mt-0.5 block">{getClassificationBadge(selectedFile.classification).label}</span>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block text-[10px]">حجم واقعی فایل:</span>
                <span className="font-bold text-slate-900 mt-0.5 block font-mono">{formatFileSize(selectedFile.sizeBytes)}</span>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block text-[10px]">بارگذاری‌کننده:</span>
                <span className="font-bold text-slate-900 mt-0.5 block">{selectedFile.uploaderName}</span>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block text-[10px]">آمار استفاده:</span>
                <span className="font-bold text-slate-900 mt-0.5 block font-mono">
                  {selectedFile.viewCount} مشاهده • {selectedFile.downloadCount} دریافت
                </span>
              </div>

            </div>

            {isAdmin && (
            <div className="space-y-2 p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-blue-600" />
                  <span>مسیر فیزیکی ایزوله در ویندوز سرور (Non-Guessable Vault Path):</span>
                </span>
              </div>
              <p className="font-mono text-[11px] text-slate-800 bg-white p-2.5 rounded-lg break-all border border-slate-200">
                {selectedFile.storedVaultName}
              </p>
              <div className="pt-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 text-[11px]">هش یکپارچگی داده (SHA-256 Checksum):</span>
                  <button
                    onClick={() => copyToClipboard(selectedFile.checksumSha256)}
                    className="text-[10px] text-blue-600 hover:underline flex items-center gap-1 font-medium"
                  >
                    {copiedHash ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedHash ? 'کپی شد' : 'کپی هش'}</span>
                  </button>
                </div>
                <p className="font-mono text-[10px] text-slate-500 bg-white p-2.5 rounded-lg break-all border border-slate-200 mt-1">
                  {selectedFile.checksumSha256}
                </p>
              </div>
            </div>
            )}

            {/* Actions Footer */}
            <div className="pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
              
              {/* Admin Quarantine Toggle */}
              {currentUser.role === 'system_admin' ? (
                <button
                  onClick={() => handleToggleQuarantine(selectedFile)}
                  className={`px-3 py-2 text-xs rounded-xl font-medium transition-colors ${
                    selectedFile.scanStatus === 'quarantined'
                      ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200'
                      : 'bg-amber-100 text-amber-900 hover:bg-amber-200'
                  }`}
                >
                  {selectedFile.scanStatus === 'quarantined' ? 'آزادسازی از قرنطینه' : 'انتقال به قرنطینه امنیتی'}
                </button>
              ) : (
                <span className="text-[11px] text-slate-500">
                  سطح دسترسی شما: <strong className="text-slate-900">{StorageService.getRoleTitle(currentUser.role)}</strong>
                </span>
              )}

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSummarizingFile(selectedFile)}
                  className="px-3.5 py-2 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded-xl flex items-center gap-1.5 font-bold"
                >
                  <Sparkles className="w-4 h-4" />
                  خلاصه هوشمند
                </button>
                {StorageService.canUserManageFile(currentUser, selectedFile) && (
                  <button
                    onClick={() => setEditingFile(selectedFile)}
                    className="px-3.5 py-2 text-xs bg-slate-100 text-slate-800 rounded-xl flex items-center gap-1.5 font-bold"
                  >
                    <Pencil className="w-4 h-4" />
                    ویرایش و دسترسی
                  </button>
                )}
                <button
                  onClick={() => setSelectedFile(null)}
                  className="px-4 py-2 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition-colors font-medium"
                >
                  بستن
                </button>

                {StorageService.canUserDownloadFile(currentUser, selectedFile) && selectedFile.scanStatus !== 'quarantined' && (
                  <button
                    onClick={() => handleDownload(selectedFile)}
                    className="px-4 py-2 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-xl flex items-center gap-1.5 transition-colors font-medium shadow-xs"
                  >
                    <Download className="w-4 h-4" />
                    <span>دریافت امن فایل</span>
                  </button>
                )}
              </div>

            </div>

          </div>
        </div>
      )}

      {summarizingFile && (
        <AiSummarizeModal
          file={summarizingFile}
          currentUser={currentUser}
          onClose={() => setSummarizingFile(null)}
        />
      )}
      {editingFile && (
        <FileAccessEditor
          file={editingFile}
          currentUser={currentUser}
          users={users}
          departments={departments}
          onClose={() => setEditingFile(null)}
          onSaved={() => { onRefresh(); setSelectedFile(null); }}
        />
      )}

    </div>
  );
};
