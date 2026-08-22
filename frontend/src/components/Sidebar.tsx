import React, { useState } from 'react';
import {
  FolderLock,
  UploadCloud,
  BarChart3,
  Users,
  ShieldCheck,
  ScrollText,
  Settings,
  ChevronDown,
  ChevronUp,
  Lock,
  Server,
  HardDrive,
  RefreshCw,
} from 'lucide-react';
import { User } from '../types';

interface SidebarProps {
  currentView: string;
  onNavigate: (view: string) => void;
  currentUser: User;
  onOpenUploadModal: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onNavigate,
  currentUser,
  onOpenUploadModal,
}) => {
  const isAdmin = currentUser.role === 'system_admin';
  const isGroupAdmin = currentUser.role === 'group_admin';
  const isViewer = currentUser.role === 'viewer';
  const [isSettingsOpen, setIsSettingsOpen] = useState(true);
  const isSettingsActive = ['security_policies', 'audit_logs', 'system_update'].includes(currentView);

  const mainMenuItems = [
    { id: 'files', label: 'مخزن فایل‌ها و گزارش‌ها', icon: FolderLock, badge: 'اصلی', visible: true },
    { id: 'dashboard', label: 'داشبورد مدیریتی و آمار', icon: BarChart3, badge: 'مدیر کل', visible: isAdmin },
    { id: 'users_groups', label: 'مدیریت کاربران و گروه‌ها', icon: Users, visible: isAdmin || isGroupAdmin },
  ];

  const settingsMenuItems = [
    { id: 'security_policies', label: 'سیاست‌های امنیتی و سهمیه', icon: ShieldCheck, badge: 'مدیر کل', visible: isAdmin },
    { id: 'system_update', label: 'به‌روزرسانی سامانه', icon: RefreshCw, badge: 'مدیر کل', visible: isAdmin },
    { id: 'audit_logs', label: 'لاگ رخدادها و ردگیری', icon: ScrollText, badge: 'امنیت', visible: isAdmin || isGroupAdmin },
  ];

  return (
    <aside className="w-64 bg-[#12345B] text-white border-l border-[#0d2744] flex flex-col justify-between shrink-0 min-h-[calc(100vh-4rem)] p-4">
      <div className="space-y-5">
        <div>
          {isViewer ? (
            <div className="p-3 bg-amber-950/40 rounded-xl border border-amber-800/60 text-xs text-amber-300 flex items-start gap-2">
              <Lock className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">حالت مشاهده‌گر (فقط‌خواندنی)</p>
                <p className="text-[11px] text-amber-400/80 mt-0.5">مجوز بارگذاری ندارید.</p>
              </div>
            </div>
          ) : (
            <button
              onClick={onOpenUploadModal}
              className="w-full flex items-center justify-center gap-2 bg-[#2E5E8C] hover:bg-[#3a6fa3] text-white font-bold py-2.5 px-4 rounded-xl text-sm"
            >
              <UploadCloud className="w-4 h-4" />
              بارگذاری فایل جدید
            </button>
          )}
        </div>

        <nav className="space-y-1.5">
          <p className="px-3 text-[11px] font-bold text-[#E8EEF5]/70 mb-2">بخش‌های سامانه</p>
          {mainMenuItems.filter((i) => i.visible).map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center justify-between p-3 rounded-lg text-xs font-medium ${
                  isActive ? 'bg-[#2E5E8C] text-white font-bold' : 'text-[#E8EEF5] hover:bg-white/10'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </div>
              </button>
            );
          })}

          {settingsMenuItems.some((i) => i.visible) && (
            <div className="pt-2">
              <button
                onClick={() => setIsSettingsOpen(!isSettingsOpen)}
                className={`w-full flex items-center justify-between p-3 rounded-lg text-xs ${
                  isSettingsActive && !isSettingsOpen ? 'bg-white/10 text-white' : 'text-[#E8EEF5] hover:bg-white/10'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Settings className="w-4 h-4" />
                  <span className="font-bold">تنظیمات</span>
                </div>
                {isSettingsOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
              {isSettingsOpen && (
                <div className="mt-1 mr-3 pr-2 border-r border-white/20 space-y-1">
                  {settingsMenuItems.filter((i) => i.visible).map((item) => {
                    const Icon = item.icon;
                    const isActive = currentView === item.id;
                    return (
                      <button
                        key={item.id}
                        onClick={() => onNavigate(item.id)}
                        className={`w-full flex items-center gap-2.5 p-2.5 rounded-lg text-xs ${
                          isActive ? 'bg-[#2E5E8C] text-white font-bold' : 'text-[#E8EEF5] hover:bg-white/10'
                        }`}
                      >
                        <Icon className="w-3.5 h-3.5" />
                        <span>{item.label}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </nav>

        <div className="pt-3 border-t border-white/10">
          <p className="px-3 text-[11px] font-bold text-[#E8EEF5]/70 mb-2">وضعیت زیرساخت</p>
          <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-xs space-y-2">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[#E8EEF5]/80 flex items-center gap-1.5"><Server className="w-3.5 h-3.5" />میزبان</span>
              <span>Linux / Docker</span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[#E8EEF5]/80 flex items-center gap-1.5"><HardDrive className="w-3.5 h-3.5" />والت</span>
              <span className="font-mono text-[10px] text-emerald-300">volume محلی</span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[#E8EEF5]/80 flex items-center gap-1.5"><ShieldCheck className="w-3.5 h-3.5" />پویش</span>
              <span className="text-emerald-300">ClamAV محلی</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-white/10">
        <p className="text-xs font-bold truncate">{currentUser.fullName}</p>
        <p className="text-[10px] text-[#E8EEF5]/70 truncate">{currentUser.departmentName}</p>
      </div>
    </aside>
  );
};
