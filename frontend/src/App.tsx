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
import { UserPortal } from './components/UserPortal';
import { AiSummarizeModal } from './components/AiSummarizeModal';
import { PwaInstallHint } from './components/PwaInstallHint';
import { TransactionLogView } from './components/TransactionLogView';
import { MeetingLogView } from './components/MeetingLogView';
import { RecipientProfilesView } from './components/RecipientProfilesView';
import { SharingAccessView } from './components/SharingAccessView';
import { RelationshipGraphView } from './components/RelationshipGraphView';
import { FilePreviewModal } from './components/FilePreviewModal';
import { AuthApi, DataApi, mapFile, mapGroup, mapLog, mapPolicy, mapUser } from './services/api';
import { User, Department, FileItem, AuditLog, SystemSecurityPolicy } from './types';
import { Lock } from 'lucide-react';
import { COPYRIGHT_TEXT } from './branding';

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
  const [portalSummarize, setPortalSummarize] = useState<FileItem | null>(null);
  const [openFileId, setOpenFileId] = useState<string | null>(null);
  const [logFileId, setLogFileId] = useState<string | null>(null);
  const [previewFile, setPreviewFile] = useState<FileItem | null>(null);
  const [navOpen, setNavOpen] = useState(false);
  const [features, setFeatures] = useState({ sms: false, graph: false, sharing: false });

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
      const mapped = mapUser(me.user);
      setCurrentUser(mapped);
      if (mapped.role === 'user' || mapped.role === 'viewer') {
        setCurrentView('user_portal');
      }
      await refreshData();
      try {
        const phases = await DataApi.phases();
        const flags = Object.fromEntries((phases.phases || []).map((item: any) => [item.flag, item.enabled]));
        const host = window.location.hostname;
        const localHost = host === 'localhost' || host === '127.0.0.1';
        setFeatures({
          sms: !!phases.sms_outbound_allowed,
          graph: !!flags.phase_5_security_graph_enabled && localHost,
          sharing: !!flags.phase_4_sharing_enabled,
        });
      } catch {
        setFeatures({ sms: false, graph: false, sharing: false });
      }
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
    return (
      <>
        <LoginView onLoggedIn={bootstrap} />
        <PwaInstallHint />
      </>
    );
  }

  const handleOpenUploadModal = () => {
    if (currentUser.role === 'viewer') return;
    setIsUploadModalOpen(true);
  };

  return (
    <div className="min-h-dvh bg-[#F7F1E8] text-[#3B2114] flex flex-col font-sans overflow-x-hidden" dir="rtl">
      <Navbar
        currentUser={currentUser}
        onSearch={setSearchQuery}
        searchQuery={searchQuery}
        onNavigate={(view) => {
          setNavOpen(false);
          setCurrentView(view);
        }}
        onOpenMenu={() => setNavOpen(true)}
        onLogout={async () => {
          await AuthApi.logout();
          setCurrentUser(null);
        }}
      />
      <div className="flex-1 flex max-w-7xl w-full mx-auto min-w-0">
        {navOpen && (
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/40 lg:hidden"
            aria-label="بستن منو"
            onClick={() => setNavOpen(false)}
          />
        )}
        <Sidebar
          currentView={currentView}
          onNavigate={setCurrentView}
          currentUser={currentUser}
          onOpenUploadModal={handleOpenUploadModal}
          mobileOpen={navOpen}
          onMobileClose={() => setNavOpen(false)}
          features={features}
        />
        <main className="flex-1 p-3 sm:p-6 lg:p-8 overflow-y-auto min-w-0 max-w-5xl pb-24 lg:pb-8">
          {currentView === 'user_portal' && (
            <UserPortal
              currentUser={currentUser}
              files={files}
              onNavigate={setCurrentView}
              onOpenFile={(f) => setPreviewFile(f)}
              onSummarize={setPortalSummarize}
            />
          )}
          {currentView === 'files' && (currentUser.role === 'system_admin' || currentUser.role === 'group_admin') && (
            <FileRepository
              files={files}
              currentUser={currentUser}
              departments={departments}
              users={users}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              onRefresh={refreshData}
              initialFileId={openFileId}
              onInitialFileHandled={() => setOpenFileId(null)}
              onLogDelivery={(file) => {
                setLogFileId(file.id);
                setCurrentView('transactions');
              }}
            />
          )}
          {currentView === 'transactions' && (
            <TransactionLogView
              currentUser={currentUser}
              files={files}
              initialFileId={logFileId}
              onInitialFileHandled={() => setLogFileId(null)}
            />
          )}
          {currentView === 'meetings' && (
            <MeetingLogView currentUser={currentUser} enabled />
          )}
          {currentView === 'recipients' && <RecipientProfilesView enabled />}
          {currentView === 'files' && currentUser.role !== 'system_admin' && currentUser.role !== 'group_admin' && (
            <Locked title="مخزن فایل‌ها و گزارش‌ها" text="این بخش فقط برای مدیران سامانه قابل مشاهده است." />
          )}
          {currentView === 'sharing' && (
            <SharingAccessView enabled={features.sharing} currentUser={currentUser} files={files} />
          )}
          {currentView === 'graph' && currentUser.role === 'system_admin' && features.graph ? (
            <RelationshipGraphView enabled />
          ) : currentView === 'graph' ? (
            <Locked title="گراف تعاملات" text="گراف فقط روی localhost و پس از فعال‌سازی فاز ۵ در دسترس است؛ در production عمومی غیرفعال است." />
          ) : null}
          {currentView === 'sms' ? (
            <Locked title="پیامک" text="ارسال پیامک و هر ارتباط خروجی تا تصمیم کتبی جدید در production غیرفعال است. برای تحویل فایل از ثبت دستی استفاده کنید." />
          ) : null}
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
              <Locked title="عدم دسترسی به لاگ‌های امنیتی" text="سیاهه رخدادها برای مدیران قابل دسترسی است." />
            )
          )}
        </main>
      </div>
      <footer className="bg-white border-t border-[#E8D9C4] px-6 py-3.5 text-center text-[11px] text-[#6B5344]">
        <div>{COPYRIGHT_TEXT}</div>
      </footer>
      <FileUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        currentUser={currentUser}
        departments={departments}
        onUploadSuccess={() => {
          refreshData();
          if (currentUser.role === 'system_admin' || currentUser.role === 'group_admin') {
            setCurrentView('files');
          } else {
            setCurrentView('user_portal');
          }
        }}
      />
      {portalSummarize && (
        <AiSummarizeModal file={portalSummarize} currentUser={currentUser} onClose={() => setPortalSummarize(null)} />
      )}
      {previewFile && (
        <FilePreviewModal
          file={previewFile}
          currentUser={currentUser}
          onClose={() => setPreviewFile(null)}
        />
      )}
      <PwaInstallHint />
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
