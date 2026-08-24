import React from 'react';
import { FolderLock, MessageSquareText, Download, Sparkles, User as UserIcon, ClipboardList } from 'lucide-react';
import { FileItem, User } from '../types';
import { formatFileSize } from '../services/storageService';
import { StorageService } from '../services/storageService';

interface UserPortalProps {
  currentUser: User;
  files: FileItem[];
  onNavigate: (view: string) => void;
  onOpenFile: (file: FileItem) => void;
  onSummarize: (file: FileItem) => void;
}

export const UserPortal: React.FC<UserPortalProps> = ({
  currentUser,
  files,
  onNavigate,
  onOpenFile,
  onSummarize,
}) => {
  const mine = files.filter((f) => f.uploaderId === currentUser.id).slice(0, 6);
  const recent = files.slice(0, 6);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-6 border border-[#EFE6D6]">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-[#4A2C17] text-white flex items-center justify-center font-bold">
            {currentUser.fullName[0]}
          </div>
          <div>
            <h1 className="text-lg font-bold text-[#4A2C17]">پرتال کاربری</h1>
            <p className="text-xs text-[#5B6573] mt-1">
              خوش آمدید {currentUser.fullName} • {currentUser.orgRoleName || StorageService.getRoleTitle(currentUser.role)} • {currentUser.departmentName}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <button onClick={() => onNavigate('files')} className="bg-white rounded-2xl p-4 border border-[#EFE6D6] text-right hover:border-[#8B5A2B]">
          <FolderLock className="w-5 h-5 text-[#8B5A2B] mb-2" />
          <p className="text-xs font-bold text-[#4A2C17]">مخزن منابع</p>
          <p className="text-[11px] text-[#5B6573] mt-1">{files.length} فایل در دسترس شما</p>
        </button>
        <button onClick={() => onNavigate('transactions')} className="bg-white rounded-2xl p-4 border border-[#EFE6D6] text-right hover:border-[#8B5A2B]">
          <ClipboardList className="w-5 h-5 text-[#8B5A2B] mb-2" />
          <p className="text-xs font-bold text-[#4A2C17]">ثبت دستی تحویل</p>
          <p className="text-[11px] text-[#5B6573] mt-1">ثبت اینکه کدام فایل، به چه کسی، در چه تاریخی و برای چه هدفی تحویل شد</p>
        </button>
        <button onClick={() => onNavigate('ai_chat')} className="bg-white rounded-2xl p-4 border border-[#EFE6D6] text-right hover:border-[#8B5A2B]">
          <MessageSquareText className="w-5 h-5 text-[#8B5A2B] mb-2" />
          <p className="text-xs font-bold text-[#4A2C17]">گفت‌وگو با منابع</p>
          <p className="text-[11px] text-[#5B6573] mt-1">پرسش از اسناد مجاز با پرامپت سازمانی</p>
        </button>
        <div className="bg-white rounded-2xl p-4 border border-[#EFE6D6]">
          <UserIcon className="w-5 h-5 text-[#8B5A2B] mb-2" />
          <p className="text-xs font-bold text-[#4A2C17]">حساب کاربری</p>
          <p className="text-[11px] text-[#5B6573] mt-1">{currentUser.email}</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-[#EFE6D6] overflow-hidden">
        <div className="p-4 border-b border-[#EFE6D6] flex items-center justify-between">
          <h2 className="text-sm font-bold text-[#4A2C17]">منابع اخیر در دسترس</h2>
          <button onClick={() => onNavigate('files')} className="text-[11px] text-[#8B5A2B] font-bold">همه منابع</button>
        </div>
        <div className="divide-y divide-slate-100">
          {(mine.length ? mine : recent).map((file) => (
            <div key={file.id} className="p-3.5 flex items-center justify-between gap-3">
              <button onClick={() => onOpenFile(file)} className="text-right min-w-0">
                <p className="text-xs font-bold text-[#4A2C17] truncate">{file.title}</p>
                <p className="text-[10px] text-[#5B6573]">{file.topic} • {formatFileSize(file.sizeBytes)}</p>
              </button>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => onSummarize(file)}
                  className="p-1.5 text-[#8B5A2B] hover:bg-[#EFE6D6] rounded-lg"
                  title="خلاصه‌سازی هوشمند"
                >
                  <Sparkles className="w-4 h-4" />
                </button>
                {StorageService.canUserDownloadFile(currentUser, file) && (
                  <Download className="w-4 h-4 text-slate-400" />
                )}
              </div>
            </div>
          ))}
          {files.length === 0 && (
            <p className="p-6 text-xs text-[#5B6573] text-center">هنوز منبعی در دسترس شما نیست.</p>
          )}
        </div>
      </div>
    </div>
  );
};
