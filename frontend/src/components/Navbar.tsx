import React, { useState } from 'react';
import {
  ShieldCheck,
  User as UserIcon,
  Search,
  Bell,
  Lock,
  LogOut,
  Users,
} from 'lucide-react';
import { User, UserRole } from '../types';

interface NavbarProps {
  currentUser: User;
  onSearch: (query: string) => void;
  searchQuery: string;
  onNavigate: (view: string) => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentUser,
  onSearch,
  searchQuery,
  onNavigate,
  onLogout,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  const getRoleBadge = (role: UserRole) => {
    switch (role) {
      case 'system_admin':
        return { label: 'مدیر سامانه', bg: 'bg-[#12345B] text-white', icon: ShieldCheck };
      case 'group_admin':
        return { label: 'مدیر گروه', bg: 'bg-[#2E5E8C] text-white', icon: Users };
      case 'user':
        return { label: 'کاربر سازمانی', bg: 'bg-[#E8EEF5] text-[#12345B] border border-[#2E5E8C]/20', icon: UserIcon };
      case 'viewer':
        return { label: 'مشاهده‌گر (فقط‌خواندنی)', bg: 'bg-[#FFF5D6] text-[#896B17] border border-[#896B17]/20', icon: Lock };
      default:
        return { label: role, bg: 'bg-slate-100 text-slate-700', icon: UserIcon };
    }
  };

  const badge = getRoleBadge(currentUser.role);
  const BadgeIcon = badge.icon;

  return (
    <header className="bg-white border-b border-[#E8EEF5] sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-reverse space-x-3 cursor-pointer" onClick={() => onNavigate('files')}>
            <div className="w-9 h-9 rounded-lg bg-[#12345B] flex items-center justify-center text-white font-bold text-base">E</div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base text-[#12345B] tracking-tight">سامانه اشتراک‌گذاری امن فایل</span>
                <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-[#E8EEF5] text-[#12345B] border border-[#E8EEF5] hidden sm:inline-block">شبکه ایتان</span>
              </div>
              <p className="text-[11px] text-[#5B6573] flex items-center gap-1.5 mt-0.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>HTTPS • نشست امن سمت سرور</span>
              </p>
            </div>
          </div>

          <div className="hidden md:flex items-center flex-1 max-w-md mx-6">
            <div className="relative w-full">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => onSearch(e.target.value)}
                placeholder="جست‌وجوی فایل، موضوع یا هش..."
                className="w-full bg-[#F2F4F7] text-sm text-[#1F2937] placeholder-[#5B6573] pr-10 pl-4 py-2 rounded-full border border-[#E8EEF5] focus:border-[#2E5E8C] focus:bg-white focus:outline-hidden"
              />
              <Search className="w-4 h-4 text-[#5B6573] absolute right-3.5 top-3" />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="w-10 h-10 flex items-center justify-center bg-[#F2F4F7] rounded-full border border-[#E8EEF5] text-[#12345B]"
              >
                <Bell className="w-4 h-4" />
              </button>
              {showNotifications && (
                <div className="absolute left-0 mt-2 w-80 bg-white rounded-2xl shadow-xl border border-[#E8EEF5] p-4 z-50">
                  <p className="text-xs font-bold text-[#12345B] mb-2">اعلان‌ها از لاگ امنیتی واقعی سامانه خوانده می‌شوند.</p>
                  <button onClick={() => { setShowNotifications(false); onNavigate('audit_logs'); }} className="text-xs text-[#2E5E8C] font-bold">
                    مشاهده رخدادها
                  </button>
                </div>
              )}
            </div>

            <div className="relative">
              <button onClick={() => setShowMenu(!showMenu)} className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-[#E8EEF5] bg-white">
                <div className="w-8 h-8 rounded-full bg-[#12345B] text-white flex items-center justify-center font-bold text-xs">
                  {currentUser.fullName.split(' ')[0][0]}
                </div>
                <div className="text-right hidden sm:block">
                  <p className="text-xs font-bold text-[#1F2937]">{currentUser.fullName}</p>
                  <p className="text-[10px] text-[#5B6573]">{currentUser.departmentName}</p>
                </div>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md flex items-center gap-1 ${badge.bg}`}>
                  <BadgeIcon className="w-3 h-3" />
                  {badge.label}
                </span>
              </button>
              {showMenu && (
                <div className="absolute left-0 mt-2 w-64 bg-white rounded-2xl shadow-xl border border-[#E8EEF5] p-3 z-50">
                  <p className="text-xs text-[#5B6573] px-2 mb-2">نقش از سمت سرور کنترل می‌شود و در مرورگر قابل تغییر نیست.</p>
                  <button onClick={onLogout} className="w-full flex items-center gap-2 text-xs text-red-700 hover:bg-[#FDEBEC] p-2 rounded-lg">
                    <LogOut className="w-4 h-4" />
                    خروج امن
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
