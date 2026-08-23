import React, { useState } from 'react';
import {
  ShieldCheck,
  User as UserIcon,
  Search,
  Bell,
  Lock,
  LogOut,
  Users,
  Menu,
} from 'lucide-react';
import { User, UserRole } from '../types';
import { APP_NAME, APP_SHORT_NAME } from '../branding';

interface NavbarProps {
  currentUser: User;
  onSearch: (query: string) => void;
  searchQuery: string;
  onNavigate: (view: string) => void;
  onLogout: () => void;
  onOpenMenu: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentUser,
  onSearch,
  searchQuery,
  onNavigate,
  onLogout,
  onOpenMenu,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const isAdmin = currentUser.role === 'system_admin';

  const getRoleBadge = (role: UserRole) => {
    switch (role) {
      case 'system_admin':
        return { label: 'مدیر سامانه', bg: 'bg-[#4A2C17] text-white', icon: ShieldCheck };
      case 'group_admin':
        return { label: 'مدیر گروه', bg: 'bg-[#8B5A2B] text-white', icon: Users };
      case 'user':
        return { label: 'کاربر سازمانی', bg: 'bg-[#EFE6D6] text-[#4A2C17] border border-[#8B5A2B]/20', icon: UserIcon };
      case 'viewer':
        return { label: 'مشاهده‌گر (فقط‌خواندنی)', bg: 'bg-[#FFF5D6] text-[#896B17] border border-[#896B17]/20', icon: Lock };
      default:
        return { label: currentUser.orgRoleName || role, bg: 'bg-slate-100 text-slate-700', icon: UserIcon };
    }
  };

  const badge = getRoleBadge(currentUser.role);
  const BadgeIcon = badge.icon;

  return (
    <header className="bg-white border-b border-[#E8D9C4] sticky top-0 z-30 pt-[env(safe-area-inset-top)]">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14 lg:h-16 gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <button
              type="button"
              onClick={onOpenMenu}
              className="lg:hidden w-10 h-10 shrink-0 flex items-center justify-center rounded-xl border border-[#EFE6D6] bg-[#F7F1E8] text-[#4A2C17]"
              aria-label="باز کردن منو"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 min-w-0 cursor-pointer" onClick={() => onNavigate(currentUser.role === 'user' || currentUser.role === 'viewer' ? 'user_portal' : 'files')}>
              <div className="w-9 h-9 rounded-lg bg-[#4A2C17] flex items-center justify-center text-white font-bold text-base shrink-0">E</div>
              <div className="min-w-0">
                <span className="font-bold text-sm text-[#4A2C17] tracking-tight leading-snug block truncate lg:hidden">{APP_SHORT_NAME}</span>
                <span className="hidden lg:block font-bold text-xs sm:text-sm text-[#4A2C17] tracking-tight leading-snug">{APP_NAME}</span>
                <p className="hidden sm:block text-[11px] text-[#6B5344] mt-0.5 truncate">پرتال سازمانی شبکه کانون‌های تفکر ایران «ایتان»</p>
              </div>
            </div>
          </div>

          <div className="hidden md:flex items-center flex-1 max-w-md mx-6">
            <div className="relative w-full">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => onSearch(e.target.value)}
                placeholder="جست‌وجوی فایل، موضوع یا منبع..."
                className="w-full bg-[#F7F1E8] text-sm text-[#1F2937] placeholder-[#5B6573] pr-10 pl-4 py-2 rounded-full border border-[#EFE6D6] focus:border-[#8B5A2B] focus:bg-white focus:outline-hidden"
              />
              <Search className="w-4 h-4 text-[#5B6573] absolute right-3.5 top-3" />
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <div className="relative">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="w-10 h-10 flex items-center justify-center bg-[#F7F1E8] rounded-full border border-[#EFE6D6] text-[#4A2C17]"
              >
                <Bell className="w-4 h-4" />
              </button>
              {showNotifications && (
                <div className="absolute left-0 mt-2 w-[min(20rem,calc(100vw-2rem))] bg-white rounded-2xl shadow-xl border border-[#EFE6D6] p-4 z-50">
                  <p className="text-xs font-bold text-[#4A2C17] mb-2">
                    {isAdmin ? 'اعلان‌ها از رخدادهای سامانه خوانده می‌شوند.' : 'اعلان‌های مربوط به پرونده‌های در دسترس شما.'}
                  </p>
                  <button
                    onClick={() => {
                      setShowNotifications(false);
                      onNavigate(isAdmin || currentUser.role === 'group_admin' ? 'audit_logs' : 'user_portal');
                    }}
                    className="text-xs text-[#8B5A2B] font-bold"
                  >
                    {isAdmin || currentUser.role === 'group_admin' ? 'مشاهده رخدادها' : 'بازگشت به پرتال'}
                  </button>
                </div>
              )}
            </div>

            <div className="relative">
              <button onClick={() => setShowMenu(!showMenu)} className="flex items-center gap-2 px-2 sm:px-3 py-1.5 rounded-xl border border-[#EFE6D6] bg-white">
                <div className="w-8 h-8 rounded-full bg-[#4A2C17] text-white flex items-center justify-center font-bold text-xs">
                  {currentUser.fullName.split(' ')[0][0]}
                </div>
                <div className="text-right hidden md:block">
                  <p className="text-xs font-bold text-[#1F2937]">{currentUser.fullName}</p>
                  <p className="text-[10px] text-[#5B6573]">{currentUser.orgRoleName || currentUser.departmentName}</p>
                </div>
                <span className={`hidden sm:flex text-[10px] font-bold px-2 py-0.5 rounded-md items-center gap-1 ${badge.bg}`}>
                  <BadgeIcon className="w-3 h-3" />
                  {currentUser.orgRoleName || badge.label}
                </span>
              </button>
              {showMenu && (
                <div className="absolute left-0 mt-2 w-64 max-w-[calc(100vw-2rem)] bg-white rounded-2xl shadow-xl border border-[#EFE6D6] p-3 z-50">
                  <button
                    onClick={() => { setShowMenu(false); onNavigate('user_portal'); }}
                    className="w-full text-right text-xs text-[#4A2C17] hover:bg-[#F7F1E8] p-2 rounded-lg mb-1"
                  >
                    پرتال کاربری
                  </button>
                  <button onClick={onLogout} className="w-full flex items-center gap-2 text-xs text-red-700 hover:bg-[#FDEBEC] p-2 rounded-lg">
                    <LogOut className="w-4 h-4" />
                    خروج امن
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="md:hidden pb-3">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearch(e.target.value)}
              placeholder="جست‌وجوی فایل..."
              className="w-full bg-[#F7F1E8] text-sm text-[#1F2937] placeholder-[#5B6573] pr-10 pl-4 py-2.5 rounded-full border border-[#EFE6D6] focus:border-[#8B5A2B] focus:bg-white focus:outline-hidden"
            />
            <Search className="w-4 h-4 text-[#5B6573] absolute right-3.5 top-3" />
          </div>
        </div>
      </div>
    </header>
  );
};
