import React, { useEffect, useState } from 'react';
import { Users, Eye, Download, FileText, Calendar, Activity } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { User, FileItem, AuditLog, Department, DashboardData } from '../types';
import { DataApi } from '../services/api';
import { formatDateTimeFa } from '../services/storageService';

interface DashboardProps {
  currentUser: User;
  users: User[];
  files: FileItem[];
  departments: Department[];
  auditLogs: AuditLog[];
  onOpenFileDetails: (file: FileItem) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onOpenFileDetails, files }) => {
  const [range, setRange] = useState('week');
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    DataApi.dashboard(range)
      .then(setData)
      .catch((e) => setError(e.message || 'خطا در بارگذاری داشبورد'));
  }, [range]);

  if (error) {
    return <div className="bg-[#FDEBEC] text-[#991B1B] p-4 rounded-2xl text-xs">{error}</div>;
  }
  if (!data) {
    return <div className="text-xs text-[#5B6573]">در حال بارگذاری شاخص‌ها...</div>;
  }

  const cards = [
    { label: 'کاربران', value: data.kpis.users_total, icon: Users },
    { label: 'کاربران فعال', value: data.kpis.users_active, icon: Activity },
    { label: 'مشاهده', value: data.kpis.views, icon: Eye },
    { label: 'دریافت', value: data.kpis.downloads, icon: Download },
    { label: 'فایل‌ها', value: data.kpis.files_total, icon: FileText },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl p-5 border border-[#E8EEF5] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-[#12345B]">داشبورد مدیریتی و گزارش مصرف</h1>
        <label className="text-xs flex items-center gap-2">
          <Calendar className="w-4 h-4 text-[#2E5E8C]" />
          <select value={range} onChange={(e) => setRange(e.target.value)} className="bg-[#F2F4F7] rounded-lg p-2 border border-[#E8EEF5]">
            <option value="today">امروز</option>
            <option value="3days">سه روز</option>
            <option value="week">هفته</option>
            <option value="month">ماه</option>
            <option value="all">همه</option>
          </select>
        </label>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <div key={c.label} className="bg-white rounded-2xl p-4 border border-[#E8EEF5]">
              <div className="w-8 h-8 rounded-lg bg-[#E8EEF5] text-[#12345B] flex items-center justify-center mb-2">
                <Icon className="w-4 h-4" />
              </div>
              <p className="text-[11px] text-[#5B6573]">{c.label}</p>
              <p className="text-xl font-bold text-[#12345B]">{c.value}</p>
            </div>
          );
        })}
      </div>

      <div className="bg-white rounded-2xl p-5 border border-[#E8EEF5]">
        <h2 className="text-sm font-bold text-[#12345B] mb-4">موضوعات پرمراجعه</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.top_topics}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="topic" tick={{ fontSize: 10 }} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#12345B" radius={6} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-[#E8EEF5] overflow-hidden">
        <div className="p-4 border-b border-[#E8EEF5]">
          <h2 className="text-sm font-bold text-[#12345B]">جدول رخدادها</h2>
        </div>
        <table className="w-full text-xs">
          <thead className="bg-[#E8EEF5] text-[#12345B]">
            <tr>
              <th className="p-3 text-right">کاربر</th>
              <th className="p-3 text-right">گزارش/فایل</th>
              <th className="p-3 text-right">موضوع</th>
              <th className="p-3 text-right">نوع رویداد</th>
              <th className="p-3 text-right">زمان</th>
            </tr>
          </thead>
          <tbody>
            {data.events.map((e, idx) => (
              <tr key={idx} className="border-t border-slate-100">
                <td className="p-3">{e.user}</td>
                <td className="p-3">
                  <button
                    className="text-[#2E5E8C]"
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
