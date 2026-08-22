import React, { useEffect, useState } from 'react';
import { 
  ShieldCheck, 
  Lock, 
  Key, 
  HardDrive, 
  AlertTriangle, 
  Check, 
  Save, 
  Server, 
  FileCheck2, 
  Sliders, 
  Cpu, 
  Globe, 
  Clock,
  RotateCcw
} from 'lucide-react';
import { SystemSecurityPolicy, User } from '../types';
import { DataApi } from '../services/api';

interface SecurityPolicyPanelProps {
  policy: SystemSecurityPolicy;
  currentUser: User;
  onRefresh: () => void;
}

export const SecurityPolicyPanel: React.FC<SecurityPolicyPanelProps> = ({
  policy,
  currentUser,
  onRefresh,
}) => {
  const [maxSizeMB, setMaxSizeMB] = useState(Math.round(policy.maxFileSizeBytes / (1024 * 1024)));
  const [clamAvEnabled, setClamAvEnabled] = useState(policy.clamAvScanEnabled);
  const [quarantineStrict, setQuarantineStrict] = useState(policy.quarantineDangerousFiles);
  const [sessionTimeout, setSessionTimeout] = useState(policy.sessionTimeoutMinutes);
  const [maxAttempts, setMaxAttempts] = useState(policy.maxFailedLoginAttempts);
  const [allowedExt, setAllowedExt] = useState((policy.allowedExtensions || []).join(', '));
  const [lockoutMin, setLockoutMin] = useState(policy.lockoutDurationMinutes);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [infra, setInfra] = useState<{ host: string; vault: string; scanner: string } | null>(null);
  const [chatPrompt, setChatPrompt] = useState('');
  const [summarizePrompt, setSummarizePrompt] = useState('');
  const [promptSaved, setPromptSaved] = useState(false);

  useEffect(() => {
    DataApi.infrastructure().then((r) => setInfra(r.infrastructure)).catch(() => setInfra(null));
    DataApi.aiPrompts().then((r) => {
      setChatPrompt(r.prompts.chat_prompt);
      setSummarizePrompt(r.prompts.summarize_prompt);
    }).catch(() => undefined);
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    await DataApi.savePolicy({
      max_file_size_bytes: maxSizeMB * 1024 * 1024,
      clamav_scan_enabled: clamAvEnabled,
      quarantine_dangerous_files: quarantineStrict,
      session_timeout_minutes: Number(sessionTimeout),
      max_failed_login_attempts: Number(maxAttempts),
      lockout_duration_minutes: Number(lockoutMin),
      allowed_extensions: allowedExt.split(/[,\s]+/).map((x) => x.trim().toLowerCase()).filter(Boolean),
    });
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
    onRefresh();
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-blue-600" />
            <span>پیکربندی سیاست‌های امنیتی و ماتریس دسترسی</span>
          </h1>
        </div>

        {savedSuccess && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-xl text-xs font-bold border border-emerald-300 animate-in fade-in">
            <Check className="w-4 h-4" />
            <span>تنظیمات امنیتی با موفقیت اعمال شد</span>
          </div>
        )}
      </div>

      {infra && (
        <div className="bg-white rounded-2xl p-5 border border-slate-200 space-y-3">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Server className="w-4 h-4 text-blue-600" />
            وضعیت زیرساخت
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border">میزبان: <strong>{infra.host}</strong></div>
            <div className="p-3 bg-slate-50 rounded-xl border">والت: <strong>{infra.vault}</strong></div>
            <div className="p-3 bg-slate-50 rounded-xl border">پویش: <strong>{infra.scanner}</strong></div>
          </div>
        </div>
      )}

      <form
        onSubmit={async (e) => {
          e.preventDefault();
          await DataApi.saveAiPrompts({ chat_prompt: chatPrompt, summarize_prompt: summarizePrompt });
          setPromptSaved(true);
          setTimeout(() => setPromptSaved(false), 2500);
        }}
        className="bg-white rounded-2xl p-6 border border-slate-200 space-y-4"
      >
        <h2 className="text-sm font-bold text-slate-900">پرامپت‌های هوش مصنوعی</h2>
        <p className="text-[11px] text-slate-500">دو پرامپت سازمانی: گفت‌وگو با منابع و خلاصه‌سازی هر فایل.</p>
        {promptSaved && <p className="text-xs text-emerald-700">پرامپت‌ها ذخیره شد.</p>}
        <label className="block text-xs font-bold">پرامپت گفت‌وگو با منابع
          <textarea className="mt-1 w-full bg-slate-100 p-3 rounded-xl border min-h-40 text-[11px] leading-6" value={chatPrompt} onChange={(e) => setChatPrompt(e.target.value)} />
        </label>
        <label className="block text-xs font-bold">پرامپت خلاصه‌سازی فایل
          <textarea className="mt-1 w-full bg-slate-100 p-3 rounded-xl border min-h-40 text-[11px] leading-6" value={summarizePrompt} onChange={(e) => setSummarizePrompt(e.target.value)} />
        </label>
        <div className="flex justify-end">
          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-bold flex items-center gap-1">
            <Save className="w-4 h-4" /> ذخیره پرامپت‌ها
          </button>
        </div>
      </form>

      {/* Security Architecture Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Card 1: Password Encryption */}
        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-xs space-y-2">
          <div className="w-9 h-9 rounded-xl bg-slate-100 text-slate-900 flex items-center justify-center">
            <Key className="w-5 h-5" />
          </div>
          <h3 className="font-bold text-xs text-slate-900">الگوریتم رمزنگاری کلمه عبور</h3>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            استفاده از الگوریتم مقاوم <strong>Argon2id</strong> و <strong>Bcrypt</strong> با پارامترهای حافظه‌محور جهت خنثی‌سازی حملات Brute-force و Rainbow Tables.
          </p>
          <div className="pt-2 border-t border-slate-100 text-[10px] font-mono text-emerald-700 font-bold">
            Status: Argon2id (Cost=19, Mem=64MB)
          </div>
        </div>

        {/* Card 2: ClamAV / Defender Antivirus Scanner */}
        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-xs space-y-2">
          <div className="w-9 h-9 rounded-xl bg-slate-100 text-slate-900 flex items-center justify-center">
            <Cpu className="w-5 h-5" />
          </div>
          <h3 className="font-bold text-xs text-slate-900">پویشگر آنتی‌ویروس سرور ویندوز</h3>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            اسکن خودکار کلیه فایل‌های ورودی از طریق سرویس محلی <strong>Windows Defender / ClamAV Service</strong> در ویندوز سرور بدون ارسال داده به ابر.
          </p>
          <div className="pt-2 border-t border-slate-100 text-[10px] font-mono text-emerald-700 font-bold">
            Engine: Windows Service / Defender API (Live)
          </div>
        </div>

        {/* Card 3: Storage Vault Isolation */}
        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-xs space-y-2">
          <div className="w-9 h-9 rounded-xl bg-slate-100 text-slate-900 flex items-center justify-center">
            <HardDrive className="w-5 h-5" />
          </div>
          <h3 className="font-bold text-xs text-slate-900">ایزولاسیون مخزن در درایو سرور</h3>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            ذخیره فیزیکی فایل‌ها با شناسه‌های غیرقابل حدس (UUID) و سطوح دسترسی NTFS خارج از وب‌روت IIS/Kestrel و بدون امکان دسترسی مستقیم با URL.
          </p>
          <div className="pt-2 border-t border-slate-100 text-[10px] font-mono text-emerald-700 font-bold">
            Isolation: Active (NTFS ACLs Enforced)
          </div>
        </div>

      </div>

      {/* Policy Edit Form */}
      <form onSubmit={handleSave} className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6 text-xs">
        
        <h2 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3 flex items-center gap-2">
          <Sliders className="w-4 h-4 text-blue-600" />
          <span>پیکربندی پارامترهای حفاظتی سامانه</span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Max File Size */}
          <div className="space-y-2">
            <label className="block font-medium text-slate-700">
              حداکثر سقف مجاز حجم هر فایل در سامانه (مگابایت):
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="10"
                max="200"
                step="5"
                value={maxSizeMB}
                onChange={(e) => setMaxSizeMB(Number(e.target.value))}
                className="flex-1 accent-blue-600"
              />
              <span className="font-mono font-bold text-sm bg-slate-100 text-slate-900 px-3 py-1 rounded-lg border border-slate-200">
                {maxSizeMB} MB
              </span>
            </div>
            <p className="text-[11px] text-slate-500">
              فایل‌های با حجم بالاتر در مرحله اعتبارسنجی اولیه به صورت خودکار رد خواهند شد.
            </p>
          </div>

          {/* Vault Storage Path */}
          <div className="space-y-2">
            <label className="block font-medium text-slate-700">فرمت‌های مجاز (با کاما):</label>
            <input
              type="text"
              value={allowedExt}
              onChange={(e) => setAllowedExt(e.target.value)}
              className="w-full bg-slate-100 text-slate-800 p-2.5 rounded-xl border border-slate-200 font-mono text-[11px]"
            />
            <p className="text-[11px] text-slate-500">مسیر فیزیکی والت از رابط کاربری قابل ویرایش نیست و هرگز در پاسخ API افشا نمی‌شود.</p>
          </div>

          {/* Session Timeout */}
          <div className="space-y-2">
            <label className="block font-medium text-slate-700">
              مدت زمان انقضای نشست بدون فعالیت (دقیقه):
            </label>
            <input
              type="number"
              min="5"
              max="120"
              value={sessionTimeout}
              onChange={(e) => setSessionTimeout(Number(e.target.value))}
              className="w-full bg-slate-100 text-slate-800 p-2.5 rounded-xl border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden font-mono"
            />
          </div>

          {/* Failed Login Lockout */}
          <div className="space-y-2">
            <label className="block font-medium text-slate-700">
              تعداد مجاز تلاش ناموفق برای ورود تا قفل حساب:
            </label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                min="3"
                max="10"
                value={maxAttempts}
                onChange={(e) => setMaxAttempts(Number(e.target.value))}
                className="w-full bg-slate-100 text-slate-800 p-2.5 rounded-xl border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden font-mono"
              />
              <span className="text-[11px] text-slate-500 flex items-center">
                تلاش ناموفق مجاز
              </span>
            </div>
          </div>

        </div>

        {/* Toggles */}
        <div className="pt-4 border-t border-slate-100 space-y-3">
          
          <label className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl cursor-pointer hover:bg-slate-100 border border-slate-200 transition-colors">
            <input
              type="checkbox"
              checked={clamAvEnabled}
              onChange={(e) => setClamAvEnabled(e.target.checked)}
              className="w-4 h-4 accent-blue-600"
            />
            <div>
              <p className="font-bold text-slate-800">فعال بودن پویشگر آنتی‌ویروس ClamAV در لحظه آپلود</p>
              <p className="text-[11px] text-slate-500">پویش مستقیم امضای بدافزارها و کدهای مخرب قبل از ذخیره در والت</p>
            </div>
          </label>

          <label className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl cursor-pointer hover:bg-slate-100 border border-slate-200 transition-colors">
            <input
              type="checkbox"
              checked={quarantineStrict}
              onChange={(e) => setQuarantineStrict(e.target.checked)}
              className="w-4 h-4 accent-blue-600"
            />
            <div>
              <p className="font-bold text-slate-800">قرنطینه و مسدودسازی خودکار اسکریپت‌ها و فایل‌های اجرایی (.exe, .sh, .bat, .dll)</p>
              <p className="text-[11px] text-slate-500">ممانعت کامل از اجرای اسکریپت‌های ناشناس و ثبت در فهرست قرنطینه امنیتی</p>
            </div>
          </label>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <p className="font-bold text-slate-800">HTTPS / HSTS در لایه Nginx اجباری است</p>
            <p className="text-[11px] text-slate-500">این مورد از رابط کاربری قابل خاموش‌کردن نیست.</p>
          </div>

        </div>

        {/* Submit */}
        <div className="pt-4 border-t border-slate-100 flex justify-end">
          <button
            type="submit"
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold flex items-center gap-2 shadow-xs transition-all"
          >
            <Save className="w-4 h-4" />
            <span>ذخیره و اعمال سیاست‌های امنیتی</span>
          </button>
        </div>

      </form>

      {/* RBAC Matrix Reference Card */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs space-y-4">
        <h2 className="text-xs font-bold text-slate-900 flex items-center gap-2">
          <Lock className="w-4 h-4 text-blue-600" />
          <span>ماتریس کنترل دسترسی نقش‌محور (Role-Based Access Control - RBAC)</span>
        </h2>

        <div className="overflow-x-auto border border-slate-200 rounded-xl">
          <table className="w-full text-right text-xs">
            <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
              <tr>
                <th className="p-3">نقش سازمانی</th>
                <th className="p-3">مشاهده متادیتا</th>
                <th className="p-3">دریافت فایل‌های مجاز</th>
                <th className="p-3">بارگذاری سند</th>
                <th className="p-3">مدیریت کاربران/گروه</th>
                <th className="p-3">داشبورد و لاگ‌ها</th>
                <th className="p-3">تنظیمات امنیتی سرور</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              <tr className="hover:bg-slate-50">
                <td className="p-3 font-bold text-slate-900">مدیر سامانه (System Admin)</td>
                <td className="p-3 text-emerald-700 font-bold">✓ کامل</td>
                <td className="p-3 text-emerald-700 font-bold">✓ کامل (تمام فایل‌ها)</td>
                <td className="p-3 text-emerald-700 font-bold">✓ بله</td>
                <td className="p-3 text-emerald-700 font-bold">✓ کامل</td>
                <td className="p-3 text-emerald-700 font-bold">✓ کامل</td>
                <td className="p-3 text-emerald-700 font-bold">✓ کامل</td>
              </tr>
              <tr className="hover:bg-slate-50">
                <td className="p-3 font-bold text-blue-700">مدیر گروه (Group Admin)</td>
                <td className="p-3 text-emerald-700 font-bold">✓ مجاز</td>
                <td className="p-3 text-emerald-700 font-bold">✓ فایل‌های گروه و عمومی</td>
                <td className="p-3 text-emerald-700 font-bold">✓ بله (واحد مربوطه)</td>
                <td className="p-3 text-amber-700 font-bold">✓ محدود به اعضای گروه</td>
                <td className="p-3 text-amber-700 font-bold">✓ گزارش‌های گروه</td>
                <td className="p-3 text-red-600 font-bold">✗ عدم دسترسی</td>
              </tr>
              <tr className="hover:bg-slate-50">
                <td className="p-3 font-bold">کاربر عادی (User)</td>
                <td className="p-3 text-emerald-700 font-bold">✓ مجاز</td>
                <td className="p-3 text-emerald-700 font-bold">✓ اسناد واحد و عمومی</td>
                <td className="p-3 text-emerald-700 font-bold">✓ بله (واحد خود)</td>
                <td className="p-3 text-red-600 font-bold">✗ عدم دسترسی</td>
                <td className="p-3 text-red-600 font-bold">✗ عدم دسترسی</td>
                <td className="p-3 text-red-600 font-bold">✗ عدم دسترسی</td>
              </tr>
              <tr className="hover:bg-slate-50 bg-amber-50/40">
                <td className="p-3 font-bold text-amber-800">مشاهده‌گر (Viewer)</td>
                <td className="p-3 text-emerald-700 font-bold">✓ متادیتا مجاز</td>
                <td className="p-3 text-amber-700 font-bold">✓ صرفاً اسناد عمومی</td>
                <td className="p-3 text-red-600 font-bold">✗ فقط‌خواندنی</td>
                <td className="p-3 text-red-600 font-bold">✗ عدم دسترسی</td>
                <td className="p-3 text-red-600 font-bold">✗ عدم دسترسی</td>
                <td className="p-3 text-red-600 font-bold">✗ عدم دسترسی</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
