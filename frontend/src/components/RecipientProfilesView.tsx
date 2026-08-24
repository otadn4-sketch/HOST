import React, { useEffect, useState } from 'react';
import { Contact } from 'lucide-react';
import { DataApi } from '../services/api';

export const RecipientProfilesView: React.FC<{ enabled: boolean }> = ({ enabled }) => {
  const [rows, setRows] = useState<any[]>([]);
  const [selected, setSelected] = useState<any | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    DataApi.recipients().then((r) => setRows(r.recipients || [])).catch((e) => setError(e.message || 'بارگذاری مخاطبان ممکن نشد.'));
  }, []);

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4]">
        <h1 className="text-lg font-bold text-[#4A2C17] flex items-center gap-2"><Contact className="w-5 h-5" /> پروفایل مخاطبان بیرونی</h1>
        <p className="text-xs text-[#6B5344] mt-2">تاریخچه تعامل، گزارش‌های تحویل‌شده و منشأ درخواست.</p>
      </div>
      {!enabled && <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-xl p-3">نمایش کامل پروفایل فاز ۳ است؛ فهرست پایه از ثبت‌های فاز ۱ در دسترس است.</p>}
      {error && <p className="text-xs text-red-700">{error}</p>}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white rounded-2xl border border-[#E8D9C4] divide-y divide-[#F0E6D8]">
          {rows.map((row) => (
            <button key={row.id} className="w-full text-right p-4 text-xs hover:bg-[#F7F1E8]" onClick={async () => {
              try {
                const detail = await DataApi.recipient(row.id);
                setSelected(detail.recipient);
              } catch {
                setSelected(row);
              }
            }}>
              <p className="font-bold text-[#4A2C17]">{row.full_name}</p>
              <p className="text-[#6B5344]">{row.organization || 'بدون سازمان'}</p>
            </button>
          ))}
          {rows.length === 0 && <p className="p-6 text-center text-xs text-[#6B5344]">مخاطبی ثبت نشده است.</p>}
        </div>
        <div className="bg-white rounded-2xl border border-[#E8D9C4] p-4 text-xs min-h-40">
          {!selected && <p className="text-[#6B5344]">یک مخاطب را انتخاب کنید.</p>}
          {selected && (
            <div className="space-y-2">
              <p className="font-bold text-[#4A2C17]">{selected.full_name}</p>
              <p>{selected.organization}</p>
              <p>منشأ درخواست: {selected.request_origin || '—'}</p>
              {(selected.history || []).map((h: any) => (
                <p key={h.id} className="text-[#6B5344] border-t border-[#EFE6D6] pt-2">{h.purpose} • {h.channel}</p>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
