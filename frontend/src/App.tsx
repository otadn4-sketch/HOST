import React, { useCallback, useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { FileRepository } from './components/FileRepository';
import { FileUploadModal } from './components/FileUploadModal';
import { Dashboard } from './components/Dashboard';
import { UserGroupManagement } from './components/UserGroupManagement';
import { SecurityPolicyPanel } from './components/SecurityPolicyPanel';
import { AuditLogsView } from './components/AuditLogsView';
import { LoginView } from './components/LoginView';
import { SystemUpdatePanel } from './components/SystemUpdatePanel';
import { AuthApi, DataApi, mapFile, mapGroup, mapLog, mapPolicy, mapUser } from './services/api';
import { User, Department, FileItem, AuditLog, SystemSecurityPolicy } from './types';
import { Lock } from 'lucide-react';

export default function App() {
  const [ready, setReady] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [securityPolicy, setSecurityPolicy] = useState<SystemSecurityPolicy | null>(null);
  const [currentView, setCurrentView] = useState<string>('files');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const refreshData = useCallback(async () => {
    const [g, f, p] = await Promise.all([DataApi.groups(), DataApi.files(searchQuery), DataApi.policy()]);
    setDepartments(g.groups.map(mapGroup));
    setFiles(f.files.map(mapFile));
    setSecurityPolicy(mapPolicy(p.policy));
    try {
      const u = await DataApi.users();
      setUsers(u.users.map(mapUser));
    } catch {
      setUsers([]);
    }
    try {
      const l = await DataApi.logs();
      setAuditLogs(l.logs.map(mapLog));
    } catch {
      setAuditLogs([]);
    }
  }, [searchQuery]);

  const bootstrap = useCallback(async () => {
    try {
      const me = await AuthApi.me();
      setCurrentUser(mapUser(me.user));
      await refreshData();
    } catch {
      setCurrentUser(null);
    } finally {
      setReady(true);
    }
  }, [refreshData]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  if (!ready) {
    return <div className="min-h-screen flex items-center justify-center text-sm text-[#5B6573]">در حال بارگذاری...</div>;
  }

  if (!currentUser) {
    return <LoginView onLoggedIn={bootstrap} />;
  }

  const handleOpenUploadModal = () => {
    if (currentUser.role === 'viewer') return;
    setIsUploadModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-[#F2F4F7] text-[#1F2937] flex flex-col font-sans" dir="rtl">
      <Navbar
        currentUser={currentUser}
        onSearch={setSearchQuery}
        searchQuery={searchQuery}
        onNavigate={setCurrentView}
        onLogout={async () => {
          await AuthApi.logout();
          setCurrentUser(null);
        }}
      />
      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <Sidebar
          currentView={currentView}
          onNavigate={setCurrentView}
          currentUser={currentUser}
          onOpenUploadModal={handleOpenUploadModal}
        />
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-5xl">
          {currentView === 'files' && (
            <FileRepository
              files={files}
              currentUser={currentUser}
              departments={departments}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              onRefresh={refreshData}
            />
          )}
          {currentView === 'dashboard' && (
            currentUser.role === 'system_admin' ? (
              <Dashboard
                currentUser={currentUser}
                users={users}
                files={files}
                departments={departments}
                auditLogs={auditLogs}
                onOpenFileDetails={() => setCurrentView('files')}
              />
            ) : (
              <Locked title="عدم دسترسی به داشبورد مدیریتی" text="این بخش فقط برای مدیر سامانه است." />
            )
          )}
          {currentView === 'users_groups' && (
            currentUser.role === 'system_admin' || currentUser.role === 'group_admin' ? (
              <UserGroupManagement
                users={users}
                departments={departments}
                currentUser={currentUser}
                onRefresh={refreshData}
              />
            ) : (
              <Locked title="عدم دسترسی به مدیریت کاربران" text="تعریف کاربران و گروه‌ها نیازمند دسترسی مدیریتی است." />
            )
          )}
          {currentView === 'security_policies' && (
            currentUser.role === 'system_admin' && securityPolicy ? (
              <SecurityPolicyPanel policy={securityPolicy} currentUser={currentUser} onRefresh={refreshData} />
            ) : (
              <Locked title="دسترسی اختصاصی مدیر ارشد سامانه" text="تغییر سیاست‌های امنیتی تنها در حیطه مدیر سامانه است." />
            )
          )}
          {currentView === 'system_update' && (
            currentUser.role === 'system_admin' ? (
              <SystemUpdatePanel />
            ) : (
              <Locked title="به‌روزرسانی سامانه" text="فقط مدیر سامانه می‌تواند بسته امضاشده را نصب کند." />
            )
          )}
          {currentView === 'audit_logs' && (
            currentUser.role === 'system_admin' || currentUser.role === 'group_admin' ? (
              <AuditLogsView logs={auditLogs} currentUser={currentUser} />
            ) : (
              <Locked title="عدم دسترسی به لاگ‌های امنیتی" text="سیاهه رخدادها برای مدیران قابل دسترسی است و از رابط کاربری قابل ویرایش نیست." />
            )
          )}
        </main>
      </div>
      <footer className="bg-white border-t border-[#E8EEF5] px-6 py-3.5 flex flex-col sm:flex-row justify-between items-center text-[11px] text-[#5B6573] gap-2">
        <div>تمامی حقوق محفوظ است © شبکه ایتان</div>
        <div>سامانه خودمیزبان • FastAPI / PostgreSQL / Nginx • بدون سرویس ابری جانبی</div>
      </footer>
      <FileUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        currentUser={currentUser}
        departments={departments}
        onUploadSuccess={() => {
          refreshData();
          setCurrentView('files');
        }}
      />
    </div>
  );
}

function Locked({ title, text }: { title: string; text: string }) {
  return (
    <div className="bg-white rounded-2xl p-8 border border-slate-200 shadow-sm text-center space-y-3">
      <Lock className="w-10 h-10 text-amber-600 mx-auto" />
      <h3 className="text-base font-bold text-slate-900">{title}</h3>
      <p className="text-xs text-slate-500">{text}</p>
    </div>
  );
}
