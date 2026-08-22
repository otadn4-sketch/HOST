import React, { useState } from 'react';
import { RefreshCw, ShieldCheck, UploadCloud } from 'lucide-react';
import { DataApi, uploadUpdateBundle } from '../services/api';
import { SystemUpdateItem } from '../types';

export const SystemUpdatePanel: React.FC = () => {
  const [items, setItems] = useState<SystemUpdateItem[]>([]);
  const [current, setCurrent] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const data = await DataApi.updates();
    setCurrent(data.current_version);
    setItems(data.updates || []);
  };

  React.useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  const onUpload = async (file: File) => {
    setBusy(true);
    setError('');
    setInfo('');
    try {
      const res = await uploadUpdateBundle(file);
      setInfo(`بسته نسخه ${res.update.version} بررسی شد. وضعیت: ${res.update.status}`);
      await load();
    } catch (e: any) {
      setError(e.message || 'بارگذاری بسته ناموفق بود.');
    } finally {
      setBusy(false);
    }
  };

  const confirm = async (id: string) => {
    if (!window.confirm('نصب این بسته باعث ورود به حالت نگهداری، تهیه بکاپ و تعویض اتمیک نسخه می‌شود. ادامه می‌دهید؟')) return;
    setBusy(true);
    try {
      await DataApi.confirmUpdate(id);
      setInfo('نصب با موفقیت انجام شد.');
      await load();
    } catch (e: any) {
      setError(e.message || 'نصب ناموفق بود.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-2xl p-5 border border-slate-200">
        <h1 className="text-lg font-bold text-[#12345B] flex items-center gap-2">
          <RefreshCw className="w-5 h-5" />
          به‌روزرسانی سامانه
        </h1>
        <p className="text-xs text-[#5B6573] mt-2 leading-6">
          فایل zip پروژه یا بستهٔ امضاشده را بارگذاری کنید. پوشهٔ تو در تو، docker-compose و install.sh نادیده گرفته می‌شوند و فقط کد سامانه اعمال می‌شود.
          پس از وضعیت <strong>validated</strong> دکمهٔ «تأیید نهایی و نصب» را بزنید.
          نسخه فعلی: <strong>{current || '—'}</strong>
        </p>
      </div>
      {error && <div className="bg-[#FDEBEC] text-[#991B1B] text-xs p-3 rounded-xl">{error}</div>}
      {info && <div className="bg-[#E4F4EA] text-[#166534] text-xs p-3 rounded-xl">{info}</div>}
      <label className="bg-white rounded-2xl p-6 border border-dashed border-[#2E5E8C] flex flex-col items-center gap-2 cursor-pointer">
        <UploadCloud className="w-8 h-8 text-[#12345B]" />
        <span className="text-xs font-bold">بارگذاری بسته .zip امضاشده به محیط staging</span>
        <input type="file" accept=".zip,.eytan.zip" className="hidden" disabled={busy} onChange={(e) => e.target.files && onUpload(e.target.files[0])} />
      </label>
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-[#E8EEF5] text-[#12345B]">
            <tr>
              <th className="p-3 text-right">نسخه</th>
              <th className="p-3 text-right">وضعیت</th>
              <th className="p-3 text-right">changelog</th>
              <th className="p-3 text-right">عملیات</th>
            </tr>
          </thead>
          <tbody>
            {items.map((u) => (
              <tr key={u.id} className="border-t border-slate-100">
                <td className="p-3 font-mono">{u.version}</td>
                <td className="p-3">{u.status}</td>
                <td className="p-3">{u.changelog}</td>
                <td className="p-3">
                  {u.status === 'rejected' && <span className="text-red-700">{u.error}</span>}
                  {u.status === 'validated' && (
                    <button disabled={busy} onClick={() => confirm(u.id)} className="px-3 py-1.5 bg-[#12345B] text-white rounded-lg">
                      تأیید نهایی و نصب
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-[#5B6573] flex items-center gap-1">
        <ShieldCheck className="w-3.5 h-3.5" />
        نصب توسط update-agent جداگانه انجام می‌شود؛ اپلیکیشن وب به Docker socket دسترسی ندارد.
      </p>
    </div>
  );
};
