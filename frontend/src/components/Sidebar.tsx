import React, { useState } from 'react';
import {
  X,
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
  RefreshCw,
  MessageSquareText,
  LayoutDashboard,
} from 'lucide-react';
import { User } from '../types';

interface SidebarProps {
  currentView: string;
  onNavigate: (view: string) => void;
  currentUser: User;
  onOpenUploadModal: () => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onNavigate,
  currentUser,
  onOpenUploadModal,
  mobileOpen = false,
  onMobileClose,
}) => {
  const isAdmin = currentUser.role === 'system_admin';
  const isGroupAdmin = currentUser.role === 'group_admin';
  const isViewer = currentUser.role === 'viewer';
  const [isSettingsOpen, setIsSettingsOpen] = useState(true);
  const isSettingsActive = ['security_policies', 'audit_logs', 'system_update'].includes(currentView);

  const mainMenuItems = [
    { id: 'user_portal', label: 'پرتال کاربری', icon: LayoutDashboard, visible: true },
    { id: 'files', label: 'مخزن فایل‌ها و گزارش‌ها', icon: FolderLock, visible: true },
    { id: 'ai_chat', label: 'گفت‌وگو با منابع', icon: MessageSquareText, visible: true },
    { id: 'dashboard', label: 'داشبورد مدیریتی و آمار', icon: BarChart3, visible: isAdmin },
    { id: 'users_groups', label: 'مدیریت کاربران، واحدها و نقش‌ها', icon: Users, visible: isAdmin || isGroupAdmin },
  ];

  const settingsMenuItems = [
    { id: 'security_policies', label: 'سیاست‌ها، زیرساخت و پرامپت هوش', icon: ShieldCheck, visible: isAdmin },
    { id: 'system_update', label: 'به‌روزرسانی سامانه', icon: RefreshCw, visible: isAdmin },
    { id: 'audit_logs', label: 'لاگ رخدادها و ردگیری', icon: ScrollText, visible: isAdmin || isGroupAdmin },
  ];

  const go = (view: string) => {
    onNavigate(view);
    onMobileClose?.();
  };

  return (
    <aside
      className={`bg-[#4A2C17] text-white flex flex-col justify-between p-4 overflow-y-auto
        fixed z-50 top-0 bottom-0 right-0 w-[min(19rem,88vw)] pt-[max(1rem,env(safe-area-inset-top))] transition-transform duration-200
        lg:static lg:z-auto lg:w-64 lg:min-h-[calc(100dvh-4rem)] lg:shrink-0 lg:translate-x-0 lg:border-l lg:border-[#3B2114] lg:pt-4
        ${mobileOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'}`}
    >
      <div className="space-y-5">
        <div className="flex items-center justify-between lg:hidden mb-1">
          <p className="text-sm font-bold">منو</p>
          <button type="button" onClick={onMobileClose} className="w-9 h-9 rounded-lg bg-white/10 flex items-center justify-center" aria-label="بستن منو">
            <X className="w-4 h-4" />
          </button>
        </div>
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
              onClick={() => {
                onOpenUploadModal();
                onMobileClose?.();
              }}
              className="w-full flex items-center justify-center gap-2 bg-[#8B5A2B] hover:bg-[#A67C52] text-white font-bold py-2.5 px-4 rounded-xl text-sm min-h-11"
            >
              <UploadCloud className="w-4 h-4" />
              بارگذاری فایل جدید
            </button>
          )}
        </div>

        <nav className="space-y-1.5">
          <p className="px-3 text-[11px] font-bold text-[#EFE6D6]/70 mb-2">بخش‌های سامانه</p>
          {mainMenuItems.filter((i) => i.visible).map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => go(item.id)}
                className={`w-full flex items-center justify-between p-3 rounded-lg text-xs font-medium min-h-11 ${
                  isActive ? 'bg-[#8B5A2B] text-white font-bold' : 'text-[#EFE6D6] hover:bg-white/10'
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
                  isSettingsActive && !isSettingsOpen ? 'bg-white/10 text-white' : 'text-[#EFE6D6] hover:bg-white/10'
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
                        onClick={() => go(item.id)}
                        className={`w-full flex items-center gap-2.5 p-2.5 rounded-lg text-xs ${
                          isActive ? 'bg-[#8B5A2B] text-white font-bold' : 'text-[#EFE6D6] hover:bg-white/10'
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
      </div>

      <div className="mt-4 pt-4 border-t border-white/10">
        <p className="text-xs font-bold truncate">{currentUser.fullName}</p>
        <p className="text-[10px] text-[#EFE6D6]/70 truncate">
          {currentUser.orgRoleName || currentUser.departmentName}
        </p>
      </div>
    </aside>
  );
};
