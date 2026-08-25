import React, { useEffect, useState } from 'react';
import { Share2 } from 'lucide-react';
import { FileItem, User } from '../types';
import { DataApi } from '../services/api';

interface Props {
  enabled: boolean;
  currentUser: User;
  files: FileItem[];
}

export const SharingAccessView: React.FC<Props> = ({ enabled, currentUser, files }) => {
  const canCreate = enabled && currentUser.role !== 'viewer';
  const [shares, setShares] = useState<any[]>([]);
  const [directory, setDirectory] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    file_id: '',
    grantee_user_id: '',
    can_download: true,
    expires_at: '',
    purpose: '',
  });

  const load = async () => {
    if (!enabled) return;
    const listed = await DataApi.shares();
    setShares(listed.shares || []);
    if (canCreate) {
      const dir = await DataApi.shareDirectory();
      setDirectory(dir.users || []);
    }
  };

  useEffect(() => {
    load().catch((e) => setError(e.message || 'بارگذاری اشتراک‌ها ممکن نشد.'));
  }, [enabled]);

  if (!enabled) {
    return (
      <div className="bg-white rounded-2xl p-6 border border-[#E8D9C4] space-y-2">
        <h1 className="text-lg font-bold text-[#4A2C17]">اشتراک‌گذاری درون‌شبکه‌ای</h1>
        <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-xl p-3">
          فاز ۴ خاموش است. هیچ پیوند عمومی ساخته نمی‌شود و API اشتراک با پاسخ روشن رد می‌شود.
        </p>
      </div>
    );
  }

  const shareable = files.filter((file) => file.canManage || currentUser.role === 'system_admin' || currentUser.role === 'group_admin');

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4]">
        <h1 className="text-lg font-bold text-[#4A2C17] flex items-center gap-2">
          <Share2 className="w-5 h-5" /> اشتراک‌گذاری درون‌شبکه‌ای
        </h1>
        <p className="text-xs text-[#6B5344] mt-2 leading-6">
          فقط کاربران داخل سامانه و با نقش مشخص. پیوند عمومی یا دسترسی ناشناس وجود ندارد. دریافت فایل دوباره کنترل مجوز و پویش را اعمال می‌کند.
        </p>
        {error && <p className="text-xs text-red-700 mt-2">{error}</p>}
      </div>

      {canCreate && (
        <form
          className="bg-white rounded-2xl p-5 border border-[#E8D9C4] space-y-3 text-xs"
          onSubmit={async (event) => {
            event.preventDefault();
            setSaving(true);
            setError('');
            try {
              await DataApi.createShare({
                file_id: form.file_id,
                grantee_user_id: form.grantee_user_id,
                can_download: form.can_download,
                expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
                purpose: form.purpose,
                audience: 'internal',
              });
              setForm({ file_id: '', grantee_user_id: '', can_download: true, expires_at: '', purpose: '' });
              await load();
            } catch (err: any) {
              setError(err.message || 'ایجاد اشتراک ممکن نشد.');
            } finally {
              setSaving(false);
            }
          }}
        >
          <p className="font-bold text-[#4A2C17]">ایجاد اشتراک برای یک کاربر</p>
          <select
            required
            className="w-full border border-[#E8D9C4] rounded-xl p-2 bg-[#F7F1E8]"
            value={form.file_id}
            onChange={(e) => setForm({ ...form, file_id: e.target.value })}
          >
            <option value="">انتخاب فایل</option>
            {shareable.map((file) => (
              <option key={file.id} value={file.id}>
                {file.title}
              </option>
            ))}
          </select>
          <select
            required
            className="w-full border border-[#E8D9C4] rounded-xl p-2 bg-[#F7F1E8]"
            value={form.grantee_user_id}
            onChange={(e) => setForm({ ...form, grantee_user_id: e.target.value })}
          >
            <option value="">انتخاب گیرنده داخل سامانه</option>
            {directory.map((item) => (
              <option key={item.id} value={item.id}>
                {item.full_name} ({item.role})
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.can_download}
              onChange={(e) => setForm({ ...form, can_download: e.target.checked })}
            />
            اجازه دریافت فایل
          </label>
          <input
            type="datetime-local"
            className="w-full border border-[#E8D9C4] rounded-xl p-2 bg-[#F7F1E8]"
            value={form.expires_at}
            onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
          />
          <input
            className="w-full border border-[#E8D9C4] rounded-xl p-2 bg-[#F7F1E8]"
            placeholder="هدف اشتراک"
            value={form.purpose}
            onChange={(e) => setForm({ ...form, purpose: e.target.value })}
          />
          <button disabled={saving} className="px-3 py-2 bg-[#4A2C17] text-white rounded-xl font-bold">
            ایجاد اشتراک داخلی
          </button>
        </form>
      )}

      <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4] space-y-2 text-xs">
        {shares.map((row) => (
          <div key={row.id} className="border border-[#E8D9C4] rounded-xl p-3 flex items-center justify-between gap-3">
            <div>
              <p className="font-bold text-[#4A2C17]">{row.file_title}</p>
              <p className="text-[#6B5344]">
                به {row.grantee_name} • {row.is_active ? 'فعال' : 'غیرفعال'} • دریافت {row.download_count}
              </p>
            </div>
            {(currentUser.role === 'system_admin' || row.created_by === currentUser.id) && row.is_active && (
              <button
                className="px-2 py-1 border border-red-200 text-red-800 rounded-lg"
                onClick={async () => {
                  await DataApi.revokeShare(row.id);
                  await load();
                }}
              >
                لغو
              </button>
            )}
            {row.grantee_user_id === currentUser.id && row.can_download && row.is_active && (
              <button
                className="px-2 py-1 bg-[#8B5A2B] text-white rounded-lg"
                onClick={() => DataApi.downloadShare(row.id, row.file_title || 'file')}
              >
                دریافت
              </button>
            )}
          </div>
        ))}
        {!shares.length && <p className="text-[#6B5344]">اشتراکی ثبت نشده است.</p>}
      </div>
    </div>
  );
};
