import React, { useEffect, useMemo, useState } from 'react';
import { ClipboardList, Plus, Search, Trash2 } from 'lucide-react';
import { FileItem, User } from '../types';
import { DataApi } from '../services/api';

const CHANNELS = [
  { id: 'handoff', label: 'تحویل حضوری' },
  { id: 'email_offline', label: 'رایانامه خارج از سامانه' },
  { id: 'physical_media', label: 'رسانه فیزیکی' },
  { id: 'other', label: 'سایر (غیرخودکار)' },
];

interface Props {
  currentUser: User;
  files: FileItem[];
  initialFileId?: string | null;
  onInitialFileHandled?: () => void;
}

export const TransactionLogView: React.FC<Props> = ({ currentUser, files, initialFileId, onInitialFileHandled }) => {
  const canWrite = currentUser.role !== 'viewer';
  const [rows, setRows] = useState<any[]>([]);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    file_id: '',
    recipient_name: '',
    recipient_organization: '',
    request_origin: '',
    purpose: '',
    channel: 'handoff',
    occurred_at: new Date().toISOString().slice(0, 16),
    notes: '',
    create_recipient: true,
  });

  const load = async (search = query) => {
    const res = await DataApi.transactions(search);
    setRows(res.transactions || []);
  };

  useEffect(() => {
    load().catch((e) => setError(e.message || 'بارگذاری تراکنش‌ها ممکن نشد.'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!initialFileId) return;
    setForm((prev) => ({ ...prev, file_id: initialFileId }));
    onInitialFileHandled?.();
  }, [initialFileId, onInitialFileHandled]);

  const fileTitle = useMemo(() => Object.fromEntries(files.map((file) => [file.id, file.title])), [files]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canWrite) return;
    if (!form.file_id) {
      setError('انتخاب فایل برای ثبت تحویل الزامی است.');
      return;
    }
    if (!form.recipient_name.trim()) {
      setError('نام مخاطب الزامی است.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await DataApi.createTransaction({
        ...form,
        occurred_at: new Date(form.occurred_at).toISOString(),
        kind: 'file_delivery',
      });
      setForm((prev) => ({
        ...prev,
        recipient_name: '',
        recipient_organization: '',
        purpose: '',
        notes: '',
        request_origin: '',
      }));
      await load();
    } catch (err: any) {
      setError(err.message || 'ثبت تراکنش ممکن نشد.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4]">
        <h1 className="text-lg font-bold text-[#4A2C17] flex items-center gap-2">
          <ClipboardList className="w-5 h-5" />
          ثبت دستی تحویل و بایگانی
        </h1>
        <p className="text-xs text-[#6B5344] mt-2 leading-relaxed">
          ارسال خودکار لینک یا فایل از طریق پیام‌رسان و پیامک منسوخ و غیرفعال است. هر تحویل باید با ذکر فایل، مخاطب، تاریخ و هدف به‌صورت دستی ثبت شود.
        </p>
      </div>

      {canWrite && (
        <form onSubmit={submit} className="bg-white rounded-2xl p-5 border border-[#E8D9C4] space-y-3">
          <h2 className="text-sm font-bold text-[#4A2C17] flex items-center gap-2">
            <Plus className="w-4 h-4" /> ثبت تحویل جدید
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label className="text-xs space-y-1">
              <span>فایل / گزارش</span>
              <select
                className="w-full border border-[#E8D9C4] rounded-xl p-2 bg-[#F7F1E8]"
                value={form.file_id}
                onChange={(e) => setForm({ ...form, file_id: e.target.value })}
              >
                <option value="">انتخاب فایل (الزامی)</option>
                {files.map((file) => (
                  <option key={file.id} value={file.id}>
                    {file.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs space-y-1">
              <span>تاریخ تحویل</span>
              <input
                type="datetime-local"
                className="w-full border border-[#E8D9C4] rounded-xl p-2 bg-[#F7F1E8]"
                value={form.occurred_at}
                onChange={(e) => setForm({ ...form, occurred_at: e.target.value })}
                required
              />
            </label>
            <label className="text-xs space-y-1">
              <span>نام مخاطب</span>
              <input
                className="w-full border border-[#E8D9C4] rounded-xl p-2 bg-[#F7F1E8]"
                value={form.recipient_name}
                onChange={(e) => setForm({ ...form, recipient_name: e.target.value })}
                required
              />
            </label>
            <label className="text-xs space-y-1">
              <span>سازمان / نهاد</span>
              <input
                className="w-full border border-[#E8D9C4] rounded-xl p-2 bg-[#F7F1E8]"
                value={form.recipient_organization}
                onChange={(e) => setForm({ ...form, recipient_organization: e.target.value })}
              />
            </label>
            <label className="text-xs space-y-1 sm:col-span-2">
              <span>هدف / دلیل تحویل</span>
              <input
                className="w-full border border-[#E8D9C4] rounded-xl p-2 bg-[#F7F1E8]"
                value={form.purpose}
                onChange={(e) => setForm({ ...form, purpose: e.target.value })}
                required
              />
            </label>
            <label className="text-xs space-y-1">
              <span>کانال (فقط دستی)</span>
              <select
                className="w-full border border-[#E8D9C4] rounded-xl p-2 bg-[#F7F1E8]"
                value={form.channel}
                onChange={(e) => setForm({ ...form, channel: e.target.value })}
              >
                {CHANNELS.map((channel) => (
                  <option key={channel.id} value={channel.id}>
                    {channel.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs space-y-1">
              <span>منشأ درخواست</span>
              <input
                className="w-full border border-[#E8D9C4] rounded-xl p-2 bg-[#F7F1E8]"
                value={form.request_origin}
                onChange={(e) => setForm({ ...form, request_origin: e.target.value })}
              />
            </label>
            <label className="text-xs space-y-1 sm:col-span-2">
              <span>یادداشت</span>
              <textarea
                className="w-full border border-[#E8D9C4] rounded-xl p-2 bg-[#F7F1E8]"
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </label>
          </div>
          <button disabled={saving} className="px-4 py-2 text-xs bg-[#4A2C17] text-white rounded-xl font-bold min-h-11">
            {saving ? 'در حال ثبت...' : 'ثبت تراکنش'}
          </button>
        </form>
      )}

      <div className="bg-white rounded-2xl border border-[#E8D9C4] overflow-hidden">
        <div className="p-4 border-b border-[#EFE6D6] flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute right-3 top-2.5 text-[#6B5344]" />
            <input
              className="w-full pr-9 pl-3 py-2 text-xs border border-[#E8D9C4] rounded-xl bg-[#F7F1E8]"
              placeholder="جست‌وجوی مخاطب، هدف یا فایل"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') load(query);
              }}
            />
          </div>
          <button onClick={() => load(query)} className="px-3 py-2 text-xs bg-[#EFE6D6] rounded-xl font-bold">
            پالایش
          </button>
        </div>
        {error && <p className="p-3 text-xs text-red-700">{error}</p>}
        <div className="divide-y divide-[#F0E6D8]">
          {rows.map((row) => (
            <div key={row.id} className="p-4 text-xs space-y-1">
              <p className="font-bold text-[#4A2C17]">
                {row.recipient_name} {row.recipient_organization ? `• ${row.recipient_organization}` : ''}
              </p>
              <p className="text-[#6B5344]">{row.purpose}</p>
              <p className="text-[11px] text-[#8B5A2B]">
                {row.file_title || fileTitle[row.file_id] || 'بدون فایل'} •{' '}
                {CHANNELS.find((channel) => channel.id === row.channel)?.label || row.channel} •{' '}
                {new Date(row.occurred_at).toLocaleString('fa-IR')}
              </p>
              {canWrite && (currentUser.role === 'system_admin' || row.logged_by_user_id === currentUser.id) && (
                <button
                  className="text-red-700 flex items-center gap-1 mt-1"
                  onClick={async () => {
                    await DataApi.deleteTransaction(row.id);
                    await load();
                  }}
                >
                  <Trash2 className="w-3 h-3" /> حذف
                </button>
              )}
            </div>
          ))}
          {rows.length === 0 && <p className="p-6 text-center text-[#6B5344]">هنوز تراکنش دستی ثبت نشده است.</p>}
        </div>
      </div>
    </div>
  );
};
