import React, { useEffect, useState } from 'react';
import { MessageSquare, Save, Send } from 'lucide-react';
import { User } from '../types';
import { DataApi } from '../services/api';

interface SmsSendViewProps {
  currentUser: User;
}

export const SmsSendView: React.FC<SmsSendViewProps> = ({ currentUser }) => {
  const isSystemAdmin = currentUser.role === 'system_admin';
  const [config, setConfig] = useState<any>(null);
  const [directory, setDirectory] = useState<{ users: any[]; recipients: any[] }>({ users: [], recipients: [] });
  const [message, setMessage] = useState('');
  const [phones, setPhones] = useState('');
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
  const [selectedRecipients, setSelectedRecipients] = useState<string[]>([]);
  const [feedback, setFeedback] = useState('');
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    enabled: false,
    base_url: '',
    api_key: '',
    sender: '',
    http_method: 'POST',
    content_type: 'json',
    url_template: '',
    body_template: '',
    auth_header_name: '',
  });

  const load = async () => {
    try {
      if (isSystemAdmin) {
        const cfg = await DataApi.smsConfig();
        setConfig(cfg.config);
        setForm({
          enabled: !!cfg.config.enabled,
          base_url: cfg.config.base_url || '',
          api_key: '',
          sender: cfg.config.sender || '',
          http_method: cfg.config.http_method || 'POST',
          content_type: cfg.config.content_type || 'json',
          url_template: cfg.config.url_template || '',
          body_template: cfg.config.body_template || '',
          auth_header_name: cfg.config.auth_header_name || '',
        });
      }
      const dir = await DataApi.smsDirectory();
      setDirectory({ users: dir.users || [], recipients: dir.recipients || [] });
    } catch (err: any) {
      setFeedback(err.message || 'بارگذاری تنظیمات پیامک ممکن نشد.');
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4]">
        <h1 className="text-lg font-bold text-[#4A2C17] flex items-center gap-2">
          <MessageSquare className="w-5 h-5" /> اتصال پیامک و ارسال
        </h1>
        <p className="text-xs text-[#6B5344] mt-2 leading-6">
          API ارائه‌دهنده پیامک را ذخیره کنید، سپس متن نمایش‌داده‌شده را برای مخاطبان انتخاب‌شده بفرستید.
        </p>
        {feedback && <p className="text-xs text-[#8B5A2B] mt-2">{feedback}</p>}
      </div>

      {isSystemAdmin && (
        <form
          className="bg-white rounded-2xl p-5 border border-[#E8D9C4] space-y-3 text-xs"
          onSubmit={async (e) => {
            e.preventDefault();
            setSaving(true);
            try {
              await DataApi.saveSmsConfig(form);
              setFeedback('تنظیمات پیامک ذخیره شد.');
              await load();
            } catch (err: any) {
              setFeedback(err.message || 'ذخیره تنظیمات ناموفق بود.');
            } finally {
              setSaving(false);
            }
          }}
        >
          <h2 className="text-sm font-bold text-[#4A2C17]">پیکربندی ارائه‌دهنده</h2>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />
            ارسال پیامک فعال باشد
          </label>
          <input className="w-full bg-[#F7F1E8] p-2 rounded-xl border" placeholder="آدرس پایه API" value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
          <input className="w-full bg-[#F7F1E8] p-2 rounded-xl border" placeholder="کلید API (خالی بماند اگر تغییری نیست)" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
          {config?.api_key_masked && <p className="text-[11px] text-[#6B5344]">کلید فعلی: {config.api_key_masked}</p>}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <input className="bg-[#F7F1E8] p-2 rounded-xl border" placeholder="خط ارسال‌کننده" value={form.sender} onChange={(e) => setForm({ ...form, sender: e.target.value })} />
            <select className="bg-[#F7F1E8] p-2 rounded-xl border" value={form.http_method} onChange={(e) => setForm({ ...form, http_method: e.target.value })}>
              <option value="POST">POST</option>
              <option value="GET">GET</option>
              <option value="PUT">PUT</option>
            </select>
            <select className="bg-[#F7F1E8] p-2 rounded-xl border" value={form.content_type} onChange={(e) => setForm({ ...form, content_type: e.target.value })}>
              <option value="json">JSON</option>
              <option value="form">Form</option>
              <option value="query">Query</option>
            </select>
          </div>
          <input className="w-full bg-[#F7F1E8] p-2 rounded-xl border font-mono" placeholder="قالب آدرس با {to} {text} {sender} {api_key}" value={form.url_template} onChange={(e) => setForm({ ...form, url_template: e.target.value })} />
          <textarea className="w-full bg-[#F7F1E8] p-2 rounded-xl border font-mono min-h-24" placeholder='قالب بدنه مثلا {"receptor":"{to}","message":"{text}"}' value={form.body_template} onChange={(e) => setForm({ ...form, body_template: e.target.value })} />
          <input className="w-full bg-[#F7F1E8] p-2 rounded-xl border" placeholder="نام هدر احراز (مثلا Authorization یا apikey)" value={form.auth_header_name} onChange={(e) => setForm({ ...form, auth_header_name: e.target.value })} />
          <button disabled={saving} className="inline-flex items-center gap-1 bg-[#4A2C17] text-white rounded-xl px-4 py-2 font-bold">
            <Save size={14} /> ذخیره پیکربندی
          </button>
        </form>
      )}

      <form
        className="bg-white rounded-2xl p-5 border border-[#E8D9C4] space-y-3 text-xs"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            const res = await DataApi.sendSms({
              message,
              phones: phones.split(/[\s,]+/).map((x) => x.trim()).filter(Boolean),
              user_ids: selectedUsers,
              recipient_ids: selectedRecipients,
            });
            setFeedback(`${res.sent} پیامک ارسال شد` + (res.failed ? ` و ${res.failed} ناموفق بود.` : '.'));
          } catch (err: any) {
            setFeedback(err.message || 'ارسال پیامک ناموفق بود.');
          }
        }}
      >
        <h2 className="text-sm font-bold text-[#4A2C17]">ارسال پیامک</h2>
        <textarea className="w-full bg-[#F7F1E8] p-3 rounded-xl border min-h-28" placeholder="متن پیامک / محتوایی که باید نمایش داده شود" value={message} onChange={(e) => setMessage(e.target.value)} />
        <input className="w-full bg-[#F7F1E8] p-2 rounded-xl border" placeholder="شماره‌های دستی با کاما" value={phones} onChange={(e) => setPhones(e.target.value)} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <p className="font-bold mb-1">کاربران دارای شماره</p>
            <div className="max-h-40 overflow-auto border rounded-xl p-2 space-y-1">
              {directory.users.map((u) => (
                <label key={u.id} className="flex items-center gap-2">
                  <input type="checkbox" checked={selectedUsers.includes(u.id)} onChange={(e) => setSelectedUsers(e.target.checked ? [...selectedUsers, u.id] : selectedUsers.filter((id) => id !== u.id))} />
                  {u.full_name} — {u.phone}
                </label>
              ))}
              {directory.users.length === 0 && <p className="text-[#6B5344]">شماره‌ای ثبت نشده است.</p>}
            </div>
          </div>
          <div>
            <p className="font-bold mb-1">مخاطبان بیرونی</p>
            <div className="max-h-40 overflow-auto border rounded-xl p-2 space-y-1">
              {directory.recipients.map((r) => (
                <label key={r.id} className="flex items-center gap-2">
                  <input type="checkbox" checked={selectedRecipients.includes(r.id)} onChange={(e) => setSelectedRecipients(e.target.checked ? [...selectedRecipients, r.id] : selectedRecipients.filter((id) => id !== r.id))} />
                  {r.full_name} — {r.phone}
                </label>
              ))}
              {directory.recipients.length === 0 && <p className="text-[#6B5344]">مخاطب دارای شماره نیست.</p>}
            </div>
          </div>
        </div>
        <button className="inline-flex items-center gap-1 bg-[#8B5A2B] text-white rounded-xl px-4 py-2 font-bold">
          <Send size={14} /> ارسال پیامک
        </button>
      </form>
    </div>
  );
};
