import React, { useEffect, useState } from 'react';
import { Users, Download, FileText, Calendar, Activity, Repeat, UserCheck } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { User, FileItem, Department, DashboardData } from '../types';
import { DataApi } from '../services/api';
import { formatDateTimeFa } from '../services/storageService';

interface DashboardProps {
  currentUser: User;
  users: User[];
  files: FileItem[];
  departments: Department[];
  auditLogs?: unknown[];
  onOpenFileDetails: (file: FileItem) => void;
}

const COLORS = ['#4A2C17', '#8B5A2B', '#A67C52', '#C4A574', '#6B5344', '#3B2114', '#896B17', '#991B1B'];

export const Dashboard: React.FC<DashboardProps> = ({ onOpenFileDetails, files }) => {
  const [range, setRange] = useState('week');
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState('');
  const [eventAction, setEventAction] = useState('all');
  const [eventUser, setEventUser] = useState('all');

  useEffect(() => {
    DataApi.dashboard(range)
      .then(setData)
      .catch((e) => setError(e.message || 'خطا در بارگذاری داشبورد'));
  }, [range]);

  if (error) {
    return <div className="bg-[#FDEBEC] text-[#991B1B] p-4 rounded-2xl text-xs">{error}</div>;
  }
  if (!data) {
    return <div className="text-xs text-[#6B5344]">در حال بارگذاری شاخص‌ها...</div>;
  }

  const cards = [
    { label: 'کاربران', value: data.kpis.users_total, icon: Users },
    { label: 'کاربران فعال', value: data.kpis.users_active, icon: Activity },
    { label: 'بازدید یکتا', value: data.kpis.views_unique ?? 0, icon: UserCheck },
    { label: 'تعداد مراجعه', value: data.kpis.views_total ?? data.kpis.views, icon: Repeat },
    { label: 'دریافت', value: data.kpis.downloads, icon: Download },
    { label: 'فایل‌ها', value: data.kpis.files_total, icon: FileText },
  ];
  const viewerUsers = data.file_viewer_users || [];

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-[#4A2C17]">داشبورد مدیریتی و گزارش مصرف</h1>
        <label className="text-xs flex items-center gap-2">
          <Calendar className="w-4 h-4 text-[#8B5A2B]" />
          <select value={range} onChange={(e) => setRange(e.target.value)} className="bg-[#F7F1E8] rounded-lg p-2 border border-[#E8D9C4]">
            <option value="today">امروز</option>
            <option value="3days">سه روز</option>
            <option value="week">هفته</option>
            <option value="month">ماه</option>
            <option value="all">همه</option>
          </select>
        </label>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <div key={c.label} className="bg-white rounded-2xl p-4 border border-[#E8D9C4]">
              <div className="w-8 h-8 rounded-lg bg-[#EFE6D6] text-[#4A2C17] flex items-center justify-center mb-2">
                <Icon className="w-4 h-4" />
              </div>
              <p className="text-[11px] text-[#6B5344]">{c.label}</p>
              <p className="text-xl font-bold text-[#4A2C17]">{c.value}</p>
            </div>
          );
        })}
      </div>
      <p className="text-[11px] text-[#6B5344] -mt-3">
        بازدید یکتا یعنی چند نفر محتوا را دیده‌اند؛ تعداد مراجعه مجموع پیش‌نمایش‌هاست و یک نفر می‌تواند چند بار مراجعه کند.
      </p>

      <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4]">
        <h2 className="text-sm font-bold text-[#4A2C17] mb-1">چه فایلی را چه افرادی دیدند</h2>
        <p className="text-[11px] text-[#6B5344] mb-4">هر ستون یک فایل است و رنگ‌ها کاربران بازدیدکننده را نشان می‌دهد.</p>
        {(data.file_viewer_chart || []).length === 0 ? (
          <p className="text-xs text-[#6B5344]">هنوز پیش‌نمایشی ثبت نشده است.</p>
        ) : (
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.file_viewer_chart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E8D9C4" />
                <XAxis dataKey="file" tick={{ fontSize: 10 }} interval={0} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend />
                {viewerUsers.map((uname, i) => (
                  <Bar key={uname} dataKey={uname} stackId="viewers" fill={COLORS[i % COLORS.length]} radius={4} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
        {(data.file_viewers || []).length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-[#EFE6D6] text-[#4A2C17]">
                <tr>
                  <th className="p-2 text-right">فایل</th>
                  <th className="p-2 text-right">کاربر</th>
                  <th className="p-2 text-right">تعداد مراجعه</th>
                </tr>
              </thead>
              <tbody>
                {(data.file_viewers || []).map((row, idx) => (
                  <tr key={`${row.file}-${row.user}-${idx}`} className="border-t border-[#E8D9C4]">
                    <td className="p-2">{row.file}</td>
                    <td className="p-2">{row.user}</td>
                    <td className="p-2 font-mono">{row.visits}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4]">
        <h2 className="text-sm font-bold text-[#4A2C17] mb-4">موضوعات پرمراجعه</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.top_topics}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E8D9C4" />
              <XAxis dataKey="topic" tick={{ fontSize: 10 }} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#4A2C17" radius={6} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4]">
          <h2 className="text-sm font-bold text-[#4A2C17] mb-4">تفکیک رخدادها بر اساس نوع</h2>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.event_by_action || []} dataKey="count" nameKey="name" innerRadius={40} outerRadius={70}>
                  {(data.event_by_action || []).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4]">
          <h2 className="text-sm font-bold text-[#4A2C17] mb-4">تفکیک بر اساس سطح اهمیت</h2>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.event_by_severity || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E8D9C4" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#8B5A2B" radius={6} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4]">
          <h2 className="text-sm font-bold text-[#4A2C17] mb-4">فعال‌ترین کاربران</h2>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.event_by_user || []} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#E8D9C4" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#4A2C17" radius={6} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-[#E8D9C4] overflow-hidden">
        <div className="p-4 border-b border-[#E8D9C4] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <h2 className="text-sm font-bold text-[#4A2C17]">جدول رخدادها</h2>
          <div className="flex gap-2 text-xs">
            <select value={eventAction} onChange={(e) => setEventAction(e.target.value)} className="bg-[#F7F1E8] rounded-lg p-2 border">
              <option value="all">همه انواع</option>
              {Array.from(new Set((data.events || []).map((e) => e.action))).map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
            <select value={eventUser} onChange={(e) => setEventUser(e.target.value)} className="bg-[#F7F1E8] rounded-lg p-2 border">
              <option value="all">همه کاربران</option>
              {Array.from(new Set((data.events || []).map((e) => e.user))).map((u) => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
          </div>
        </div>
        <table className="w-full text-xs">
          <thead className="bg-[#EFE6D6] text-[#4A2C17]">
            <tr>
              <th className="p-3 text-right">کاربر</th>
              <th className="p-3 text-right">گزارش/فایل</th>
              <th className="p-3 text-right">موضوع</th>
              <th className="p-3 text-right">نوع رویداد</th>
              <th className="p-3 text-right">زمان</th>
            </tr>
          </thead>
          <tbody>
            {data.events.filter((e) => (eventAction === 'all' || e.action === eventAction) && (eventUser === 'all' || e.user === eventUser)).map((e, idx) => (
              <tr key={idx} className="border-t border-slate-100">
                <td className="p-3">{e.user}</td>
                <td className="p-3">
                  <button
                    className="text-[#8B5A2B]"
                    onClick={() => {
                      const f = files.find((x) => x.title === e.file);
                      if (f) onOpenFileDetails(f);
                    }}
                  >
                    {e.file}
                  </button>
                </td>
                <td className="p-3">{e.topic}</td>
                <td className="p-3">{e.action_title}</td>
                <td className="p-3">{formatDateTimeFa(e.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
