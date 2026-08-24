import React, { useEffect, useState } from 'react';
import { Users } from 'lucide-react';
import { User } from '../types';
import { DataApi } from '../services/api';

export const MeetingLogView: React.FC<{ currentUser: User; enabled: boolean }> = ({ currentUser, enabled }) => {
  const canWrite = currentUser.role !== 'viewer';
  const [rows, setRows] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    title: '',
    meeting_kind: 'physical_meeting',
    occurred_at: new Date().toISOString().slice(0, 16),
    location: '',
    attendees: '',
    agenda: '',
    outcome: '',
    notes: '',
  });

  const load = async () => {
    const res = await DataApi.meetings();
    setRows(res.meetings || []);
  };

  useEffect(() => {
    if (!enabled) return;
    load().catch((e) => setError(e.message || 'بارگذاری جلسات ممکن نشد.'));
  }, [enabled]);

  if (!enabled) {
    return <div className="bg-white rounded-2xl p-6 border border-[#E8D9C4] text-xs text-[#6B5344]">فاز ۲ (ثبت جلسات) هنوز فعال نشده است.</div>;
  }

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4]">
        <h1 className="text-lg font-bold text-[#4A2C17] flex items-center gap-2"><Users className="w-5 h-5" /> ثبت جلسات و ارائه‌ها</h1>
        <p className="text-xs text-[#6B5344] mt-2">تعاملات حضوری و ارائه‌های بیرونی به‌عنوان تراکنش تعامل ثبت می‌شوند.</p>
      </div>
      {canWrite && (
        <form
          className="bg-white rounded-2xl p-5 border border-[#E8D9C4] grid grid-cols-1 sm:grid-cols-2 gap-3"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              await DataApi.createMeeting({
                ...form,
                occurred_at: new Date(form.occurred_at).toISOString(),
                attendees: form.attendees.split(/[،,]/).map((s) => s.trim()).filter(Boolean),
              });
              setForm({ ...form, title: '', attendees: '', agenda: '', outcome: '', notes: '' });
              await load();
            } catch (err: any) {
              setError(err.message || 'ثبت جلسه ممکن نشد.');
            }
          }}
        >
          <input className="border border-[#E8D9C4] rounded-xl p-2 text-xs bg-[#F7F1E8]" placeholder="عنوان جلسه" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          <select className="border border-[#E8D9C4] rounded-xl p-2 text-xs bg-[#F7F1E8]" value={form.meeting_kind} onChange={(e) => setForm({ ...form, meeting_kind: e.target.value })}>
            <option value="physical_meeting">جلسه حضوری</option>
            <option value="external_presentation">ارائه بیرونی</option>
          </select>
          <input type="datetime-local" className="border border-[#E8D9C4] rounded-xl p-2 text-xs bg-[#F7F1E8]" value={form.occurred_at} onChange={(e) => setForm({ ...form, occurred_at: e.target.value })} />
          <input className="border border-[#E8D9C4] rounded-xl p-2 text-xs bg-[#F7F1E8]" placeholder="محل" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
          <input className="sm:col-span-2 border border-[#E8D9C4] rounded-xl p-2 text-xs bg-[#F7F1E8]" placeholder="حاضران (با ویرگول)" value={form.attendees} onChange={(e) => setForm({ ...form, attendees: e.target.value })} />
          <textarea className="sm:col-span-2 border border-[#E8D9C4] rounded-xl p-2 text-xs bg-[#F7F1E8]" placeholder="دستور جلسه" value={form.agenda} onChange={(e) => setForm({ ...form, agenda: e.target.value })} />
          <button className="px-4 py-2 text-xs bg-[#4A2C17] text-white rounded-xl font-bold">ثبت جلسه</button>
        </form>
      )}
      {error && <p className="text-xs text-red-700">{error}</p>}
      <div className="bg-white rounded-2xl border border-[#E8D9C4] divide-y divide-[#F0E6D8]">
        {rows.map((row) => (
          <div key={row.id} className="p-4 text-xs">
            <p className="font-bold text-[#4A2C17]">{row.title}</p>
            <p className="text-[#6B5344] mt-1">{row.meeting_kind === 'external_presentation' ? 'ارائه بیرونی' : 'جلسه حضوری'} • {row.location}</p>
          </div>
        ))}
        {rows.length === 0 && <p className="p-6 text-center text-xs text-[#6B5344]">جلسه‌ای ثبت نشده است.</p>}
      </div>
    </div>
  );
};
