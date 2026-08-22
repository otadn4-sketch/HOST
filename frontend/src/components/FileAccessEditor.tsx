import React, { useState } from 'react';
import { X, Save, ShieldCheck } from 'lucide-react';
import { Department, FileItem, FilePermissionRule, User, UserRole } from '../types';
import { DataApi } from '../services/api';

interface FileAccessEditorProps {
  file: FileItem;
  currentUser: User;
  users: User[];
  departments: Department[];
  onClose: () => void;
  onSaved: () => void;
}

const emptyRule = (): FilePermissionRule => ({
  target_type: 'role',
  target_id: 'user',
  can_view: true,
  can_download: false,
  can_upload: false,
  can_manage: false,
});

export const FileAccessEditor: React.FC<FileAccessEditorProps> = ({
  file,
  users,
  departments,
  onClose,
  onSaved,
}) => {
  const [title, setTitle] = useState(file.title);
  const [topic, setTopic] = useState(file.topic);
  const [description, setDescription] = useState(file.description || '');
  const [classification, setClassification] = useState(file.classification);
  const [tags, setTags] = useState((file.tags || []).join(', '));
  const [groupId, setGroupId] = useState(file.departmentId);
  const [permissions, setPermissions] = useState<FilePermissionRule[]>(file.permissions?.length ? file.permissions : []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await DataApi.patchFile(file.id, {
        title,
        topic,
        description,
        classification,
        tags: tags.split(/[,\s]+/).map((t) => t.trim()).filter(Boolean),
        group_id: groupId,
        permissions: permissions.map((p) => ({
          target_type: p.target_type,
          target_id: p.target_id,
          can_view: p.can_view,
          can_download: p.can_download,
          can_upload: p.can_upload,
          can_manage: p.can_manage,
        })),
      });
      onSaved();
      onClose();
    } catch (err: any) {
      setError(err.message || 'ذخیره ناموفق بود.');
    } finally {
      setBusy(false);
    }
  };

  const updateRule = (idx: number, patch: Partial<FilePermissionRule>) => {
    setPermissions((prev) => prev.map((p, i) => (i === idx ? { ...p, ...patch } : p)));
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-900/50">
      <form onSubmit={save} className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-blue-600" />
            ویرایش مشخصات و سطوح دسترسی فایل
          </h2>
          <button type="button" onClick={onClose}><X className="w-4 h-4 text-slate-400" /></button>
        </div>
        {error && <p className="text-xs text-red-700 bg-red-50 p-2 rounded-lg">{error}</p>}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <label className="block">عنوان
            <input className="mt-1 w-full bg-slate-100 p-2 rounded-lg border" value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label className="block">موضوع
            <input className="mt-1 w-full bg-slate-100 p-2 rounded-lg border" value={topic} onChange={(e) => setTopic(e.target.value)} />
          </label>
          <label className="block">واحد سازمانی
            <select className="mt-1 w-full bg-slate-100 p-2 rounded-lg border" value={groupId} onChange={(e) => setGroupId(e.target.value)}>
              {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </label>
          <label className="block">رده محرمانگی
            <select className="mt-1 w-full bg-slate-100 p-2 rounded-lg border" value={classification} onChange={(e) => setClassification(e.target.value as any)}>
              <option value="public">عمومی</option>
              <option value="internal">سازمانی داخلی</option>
              <option value="confidential">محرمانه</option>
              <option value="secret">به‌کلی سری</option>
            </select>
          </label>
        </div>
        <label className="block text-xs">توضیحات
          <textarea className="mt-1 w-full bg-slate-100 p-2 rounded-lg border" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <label className="block text-xs">برچسب‌ها
          <input className="mt-1 w-full bg-slate-100 p-2 rounded-lg border" value={tags} onChange={(e) => setTags(e.target.value)} />
        </label>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold">سطوح دسترسی اضافی</p>
            <button type="button" onClick={() => setPermissions((p) => [...p, emptyRule()])} className="text-[11px] text-blue-700 font-bold">افزودن مجوز</button>
          </div>
          {permissions.map((p, idx) => (
            <div key={idx} className="grid grid-cols-2 md:grid-cols-6 gap-2 items-center text-[11px] bg-slate-50 p-2 rounded-xl border">
              <select value={p.target_type} onChange={(e) => updateRule(idx, { target_type: e.target.value as any, target_id: '' })} className="bg-white p-1.5 rounded border">
                <option value="role">نقش</option>
                <option value="group">واحد</option>
                <option value="user">کاربر</option>
              </select>
              {p.target_type === 'role' && (
                <select value={p.target_id} onChange={(e) => updateRule(idx, { target_id: e.target.value })} className="bg-white p-1.5 rounded border">
                  {(['system_admin', 'group_admin', 'user', 'viewer'] as UserRole[]).map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              )}
              {p.target_type === 'group' && (
                <select value={p.target_id} onChange={(e) => updateRule(idx, { target_id: e.target.value })} className="bg-white p-1.5 rounded border">
                  {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              )}
              {p.target_type === 'user' && (
                <select value={p.target_id} onChange={(e) => updateRule(idx, { target_id: e.target.value })} className="bg-white p-1.5 rounded border">
                  {users.map((u) => <option key={u.id} value={u.id}>{u.fullName}</option>)}
                </select>
              )}
              <label className="flex items-center gap-1"><input type="checkbox" checked={p.can_view} onChange={(e) => updateRule(idx, { can_view: e.target.checked })} /> مشاهده</label>
              <label className="flex items-center gap-1"><input type="checkbox" checked={p.can_download} onChange={(e) => updateRule(idx, { can_download: e.target.checked })} /> دریافت</label>
              <label className="flex items-center gap-1"><input type="checkbox" checked={p.can_manage} onChange={(e) => updateRule(idx, { can_manage: e.target.checked })} /> مدیریت</label>
              <button type="button" className="text-red-600" onClick={() => setPermissions((prev) => prev.filter((_, i) => i !== idx))}>حذف</button>
            </div>
          ))}
        </div>

        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <button type="button" onClick={onClose} className="px-3 py-2 bg-slate-100 rounded-xl text-xs">انصراف</button>
          <button type="submit" disabled={busy} className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-bold flex items-center gap-1">
            <Save className="w-4 h-4" /> ذخیره
          </button>
        </div>
      </form>
    </div>
  );
};
