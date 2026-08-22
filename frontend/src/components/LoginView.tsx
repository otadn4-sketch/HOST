import React, { useState } from 'react';
import { Lock, ShieldCheck } from 'lucide-react';
import { ApiError, AuthApi } from '../services/api';
import { APP_NAME } from '../branding';

interface LoginViewProps {
  onLoggedIn: () => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onLoggedIn }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [mode, setMode] = useState<'login' | 'recovery' | 'confirm'>('login');
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [busy, setBusy] = useState(false);

  const submitLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await AuthApi.login(username.trim(), password);
      onLoggedIn();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'ورود ناموفق بود.');
    } finally {
      setBusy(false);
    }
  };

  const submitRecovery = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const res: any = await AuthApi.recoveryRequest(username.trim());
      setInfo(res.message || 'درخواست ثبت شد.');
      setMode('confirm');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'درخواست ناموفق بود.');
    } finally {
      setBusy(false);
    }
  };

  const submitConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await AuthApi.recoveryConfirm(token.trim(), newPassword);
      setInfo('گذرواژه به‌روزرسانی شد. اکنون وارد شوید.');
      setMode('login');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'بازیابی ناموفق بود.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F1E8] flex items-center justify-center p-4" dir="rtl">
      <div className="w-full max-w-md bg-white rounded-2xl border border-[#EFE6D6] shadow-sm p-8 space-y-6">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-[#4A2C17] text-white flex items-center justify-center font-bold">E</div>
          <div>
            <h1 className="text-sm font-bold text-[#4A2C17] leading-6">{APP_NAME}</h1>
            <p className="text-[11px] text-[#6B5344]">ورود محلی روی سرور اختصاصی</p>
          </div>
        </div>

        {error && <div className="text-xs bg-[#FDEBEC] text-[#991B1B] rounded-xl p-3">{error}</div>}
        {info && <div className="text-xs bg-[#E4F4EA] text-[#166534] rounded-xl p-3">{info}</div>}

        {mode === 'login' && (
          <form onSubmit={submitLogin} className="space-y-3 text-xs">
            <label className="block">
              <span className="font-medium text-[#5B6573]">نام کاربری</span>
              <input value={username} onChange={(e) => setUsername(e.target.value)} className="mt-1 w-full p-2.5 rounded-xl bg-[#F7F1E8] border border-[#EFE6D6] focus:border-[#8B5A2B] outline-none" />
            </label>
            <label className="block">
              <span className="font-medium text-[#5B6573]">گذرواژه</span>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 w-full p-2.5 rounded-xl bg-[#F7F1E8] border border-[#EFE6D6] focus:border-[#8B5A2B] outline-none" />
            </label>
            <button disabled={busy} className="w-full py-2.5 rounded-xl bg-[#4A2C17] text-white font-bold flex items-center justify-center gap-2">
              <Lock className="w-4 h-4" />
              ورود امن
            </button>
            <button type="button" onClick={() => setMode('recovery')} className="w-full text-[#8B5A2B] font-medium">
              بازیابی دسترسی
            </button>
          </form>
        )}

        {mode === 'recovery' && (
          <form onSubmit={submitRecovery} className="space-y-3 text-xs">
            <p className="text-[#5B6573] leading-6">
              درخواست بازیابی برای مدیر سامانه ثبت می‌شود. توکن یک‌بارمصرف فقط از مسیر برون‌خط (تماس با مدیر) دریافت می‌گردد.
            </p>
            <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="نام کاربری" className="w-full p-2.5 rounded-xl bg-[#F7F1E8] border border-[#EFE6D6]" />
            <button disabled={busy} className="w-full py-2.5 rounded-xl bg-[#4A2C17] text-white font-bold">ارسال درخواست</button>
            <button type="button" onClick={() => setMode('login')} className="w-full text-[#8B5A2B]">بازگشت به ورود</button>
          </form>
        )}

        {mode === 'confirm' && (
          <form onSubmit={submitConfirm} className="space-y-3 text-xs">
            <input value={token} onChange={(e) => setToken(e.target.value)} placeholder="توکن بازیابی صادرشده توسط مدیر" className="w-full p-2.5 rounded-xl bg-[#F7F1E8] border border-[#EFE6D6]" />
            <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="گذرواژه جدید" className="w-full p-2.5 rounded-xl bg-[#F7F1E8] border border-[#EFE6D6]" />
            <button disabled={busy} className="w-full py-2.5 rounded-xl bg-[#4A2C17] text-white font-bold">ثبت گذرواژه جدید</button>
            <button type="button" onClick={() => setMode('login')} className="w-full text-[#8B5A2B]">بازگشت به ورود</button>
          </form>
        )}

        <p className="text-[10px] text-[#5B6573] flex items-center gap-1">
          <ShieldCheck className="w-3.5 h-3.5 text-[#4A2C17]" />
          نشست HttpOnly، حفاظت CSRF و قفل موقت پس از تلاش ناموفق
        </p>
      </div>
    </div>
  );
};
