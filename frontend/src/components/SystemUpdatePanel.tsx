import React, { useState } from 'react';
import { RefreshCw, ShieldCheck, UploadCloud } from 'lucide-react';
import { DataApi, uploadUpdateBundle } from '../services/api';
import { SystemUpdateItem } from '../types';

const RETRYABLE = new Set(['validated', 'failed', 'rolled_back', 'installing']);

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
      const st = res.update.status;
      if (st === 'validated') {
        setInfo(`بسته نسخه ${res.update.version} بررسی شد و آماده نصب است.`);
      } else {
        setError(res.update.error || `وضعیت بسته: ${st}`);
      }
      await load();
    } catch (e: any) {
      setError(e.message || 'بارگذاری بسته ناموفق بود.');
    } finally {
      setBusy(false);
    }
  };

  const confirm = async (id: string) => {
    if (!window.confirm('نصب این بسته کد سامانه را روی همین سرور اعمال می‌کند. ادامه می‌دهید؟')) return;
    setBusy(true);
    setError('');
    setInfo('در حال نصب…');
    try {
      const res: any = await DataApi.confirmUpdate(id);
      const notes = Array.isArray(res.notes) ? res.notes.join('؛ ') : '';
      setInfo(notes ? `نصب انجام شد. ${notes}` : 'نصب با موفقیت انجام شد. چند ثانیه بعد سامانه تازه می‌شود.');
      await load();
    } catch (e: any) {
      setError(e.message || 'نصب ناموفق بود.');
      await load().catch(() => undefined);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-2xl p-5 border border-slate-200">
        <h1 className="text-lg font-bold text-[#4A2C17] flex items-center gap-2">
          <RefreshCw className="w-5 h-5" />
          به‌روزرسانی سامانه
        </h1>
        <p className="text-xs text-[#5B6573] mt-2 leading-6">
          فایل zip پروژه را بارگذاری کنید. پوشهٔ تو در تو، docker-compose و install.sh نادیده گرفته می‌شوند.
          پس از بررسی موفق، «تأیید نهایی و نصب» را بزنید. اگر نصب ناموفق بود می‌توانید دوباره تلاش کنید.
          رابط کاربری فقط با وجود <span className="font-mono">frontend/dist</span> عوض می‌شود.
          نسخه فعلی: <strong>{current || '—'}</strong>
        </p>
      </div>
      {error && <div className="bg-[#FDEBEC] text-[#991B1B] text-xs p-3 rounded-xl whitespace-pre-wrap">{error}</div>}
      {info && <div className="bg-[#E4F4EA] text-[#166534] text-xs p-3 rounded-xl">{info}</div>}
      <label className="bg-white rounded-2xl p-6 border border-dashed border-[#8B5A2B] flex flex-col items-center gap-2 cursor-pointer">
        <UploadCloud className="w-8 h-8 text-[#4A2C17]" />
        <span className="text-xs font-bold">بارگذاری بسته .zip به محیط staging</span>
        <input type="file" accept=".zip,.eytan.zip" className="hidden" disabled={busy} onChange={(e) => e.target.files && onUpload(e.target.files[0])} />
      </label>
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-[#EFE6D6] text-[#4A2C17]">
            <tr>
              <th className="p-3 text-right">نسخه</th>
              <th className="p-3 text-right">وضعیت</th>
              <th className="p-3 text-right">توضیح / خطا</th>
              <th className="p-3 text-right">عملیات</th>
            </tr>
          </thead>
          <tbody>
            {items.map((u) => (
              <tr key={u.id} className="border-t border-slate-100">
                <td className="p-3 font-mono">{u.version}</td>
                <td className="p-3">{u.status}</td>
                <td className="p-3 text-[#6B5344]">{u.error || u.changelog || '—'}</td>
                <td className="p-3">
                  {RETRYABLE.has(u.status) && (
                    <button disabled={busy} onClick={() => confirm(u.id)} className="px-3 py-1.5 bg-[#4A2C17] text-white rounded-lg">
                      {u.status === 'validated' ? 'تأیید نهایی و نصب' : 'تلاش دوباره برای نصب'}
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
        نصب روی همین سرور انجام می‌شود و اسکریپت داخل zip اجرا نمی‌شود.
      </p>
    </div>
  );
};
