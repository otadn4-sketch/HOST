import React, { useState, useMemo } from 'react';
import { 
  ScrollText, 
  Search, 
  ShieldAlert, 
  AlertTriangle, 
  Info, 
  Terminal, 
  X,
  FileSpreadsheet
} from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { AuditLog, User, LogSeverity } from '../types';

interface AuditLogsViewProps {
  logs: AuditLog[];
  currentUser: User;
}

export const AuditLogsView: React.FC<AuditLogsViewProps> = ({
  logs,
  currentUser,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [actionFilter, setActionFilter] = useState<string>('all');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const matches =
          log.username.toLowerCase().includes(q) ||
          log.actionTitle.toLowerCase().includes(q) ||
          log.targetResource.toLowerCase().includes(q) ||
          log.details.toLowerCase().includes(q) ||
          (currentUser.role === 'system_admin' && log.ipAddress.toLowerCase().includes(q));
        if (!matches) return false;
      }

      if (severityFilter !== 'all' && log.severity !== severityFilter) return false;
      if (actionFilter !== 'all' && log.action !== actionFilter) return false;

      return true;
    });
  }, [logs, searchTerm, severityFilter, actionFilter, currentUser.role]);

  const isAdmin = currentUser.role === 'system_admin';
  const colors = ['#4A2C17', '#8B5A2B', '#896B17', '#991B1B', '#166534'];
  const byAction = Object.entries(filteredLogs.reduce<Record<string, number>>((acc, l) => {
    acc[l.actionTitle] = (acc[l.actionTitle] || 0) + 1;
    return acc;
  }, {})).map(([name, count]) => ({ name, count }));
  const bySeverity = Object.entries(filteredLogs.reduce<Record<string, number>>((acc, l) => {
    acc[l.severity] = (acc[l.severity] || 0) + 1;
    return acc;
  }, {})).map(([name, count]) => ({ name, count }));

  const handleExportCSV = () => {
    const headers = isAdmin
      ? ['شناسه لاگ', 'زمان', 'نام کاربری', 'نقش', 'نوع عملیات', 'منبع هدف', 'آدرس IP', 'سطح اهمیت', 'شرح']
      : ['شناسه لاگ', 'زمان', 'نام کاربری', 'نقش', 'نوع عملیات', 'منبع هدف', 'سطح اهمیت', 'شرح'];
    const rows = filteredLogs.map((l) =>
      isAdmin
        ? [
            l.id,
            l.timestamp,
            l.username,
            l.userRole,
            l.actionTitle,
            `"${l.targetResource.replace(/"/g, '""')}"`,
            l.ipAddress,
            l.severity,
            `"${l.details.replace(/"/g, '""')}"`,
          ]
        : [
            l.id,
            l.timestamp,
            l.username,
            l.userRole,
            l.actionTitle,
            `"${l.targetResource.replace(/"/g, '""')}"`,
            l.severity,
            `"${l.details.replace(/"/g, '""')}"`,
          ]
    );

    const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `eytan_audit_logs_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const getSeverityBadge = (sev: LogSeverity) => {
    switch (sev) {
      case 'critical':
        return { label: 'بحرانی', class: 'bg-red-50 text-red-700 border-red-200', icon: ShieldAlert };
      case 'warning':
        return { label: 'هشدار', class: 'bg-amber-50 text-amber-700 border-amber-200', icon: AlertTriangle };
      case 'info':
      default:
        return { label: 'اطلاعاتی', class: 'bg-slate-100 text-slate-700 border-slate-200', icon: Info };
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header & Export Toolbar */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <ScrollText className="w-5 h-5 text-blue-600" />
            <span>ثبت و ردگیری رخدادهای امنیتی (Audit Trails)</span>
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all border border-slate-200"
            title="دریافت گزارش کامل اکسل و CSV"
          >
            <FileSpreadsheet className="w-4 h-4 text-blue-600" />
            <span>خروجی CSV و اکسل</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-xs flex flex-col md:flex-row gap-3">
        
        {/* Search */}
        <div className="relative flex-1">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="جست‌وجو در متن پیام، کاربر، IP، منبع یا عنوان رویداد..."
            className="w-full bg-slate-100 text-xs text-slate-800 pr-9 pl-4 py-2 rounded-xl border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-hidden"
          />
          <Search className="w-4 h-4 text-slate-400 absolute right-3 top-2.5" />
        </div>

        {/* Severity Filter */}
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="bg-slate-100 text-xs text-slate-800 px-3 py-2 rounded-xl border border-slate-200 focus:border-blue-600 focus:outline-hidden"
        >
          <option value="all">همه سطوح اهمیت</option>
          <option value="info">اطلاعاتی (Info)</option>
          <option value="warning">هشدار امنیتی (Warning)</option>
          <option value="critical">بحرانی و بدافزار (Critical)</option>
        </select>

        {/* Action Type Filter */}
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="bg-slate-100 text-xs text-slate-800 px-3 py-2 rounded-xl border border-slate-200 focus:border-blue-600 focus:outline-hidden"
        >
          <option value="all">همه انواع عملیات</option>
          <option value="login_success">ورود موفق</option>
          <option value="login_failed">ورود ناموفق</option>
          <option value="file_download">دریافت فایل</option>
          <option value="file_preview">پیش‌نمایش محتوا</option>
          <option value="file_view">مشاهده جزئیات فایل</option>
          <option value="file_upload">بارگذاری فایل</option>
          <option value="file_quarantined">قرنطینه بدافزار</option>
          <option value="permission_change">تغییر سطح دسترسی</option>
          <option value="ai_summarize">خلاصه‌سازی هوشمند</option>
          <option value="file_preview_heartbeat">حضور در پیش‌نمایش</option>
          <option value="sms_sent">ارسال پیامک</option>
          <option value="suspicious_activity">فعالیت مشکوک</option>
        </select>

      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-2xl p-4 border border-slate-200">
          <h2 className="text-xs font-bold mb-3">نمودار تفکیک نوع رخداد</h2>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={byAction} dataKey="count" nameKey="name" innerRadius={35} outerRadius={65}>
                  {byAction.map((_, i) => <Cell key={i} fill={colors[i % colors.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="bg-white rounded-2xl p-4 border border-slate-200">
          <h2 className="text-xs font-bold mb-3">نمودار سطح اهمیت</h2>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bySeverity}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#4A2C17" radius={6} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-right text-xs">
            <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
              <tr>
                <th className="p-3.5 pr-5">سطح</th>
                <th className="p-3.5">عنوان رخداد</th>
                <th className="p-3.5">کاربر و شناسه</th>
                <th className="p-3.5">منبع هدف</th>
                <th className="p-3.5">آدرس IP</th>
                <th className="p-3.5">زمان ثبت</th>
                <th className="p-3.5 pl-5 text-center">جزئیات</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {filteredLogs.map((log) => {
                const badge = getSeverityBadge(log.severity);
                const BadgeIcon = badge.icon;

                return (
                  <tr
                    key={log.id}
                    onClick={() => setSelectedLog(log)}
                    className="hover:bg-slate-50 cursor-pointer transition-colors"
                  >
                    <td className="p-3.5 pr-5">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold flex items-center gap-1 w-fit ${badge.class}`}>
                        <BadgeIcon className="w-3 h-3" />
                        <span>{badge.label}</span>
                      </span>
                    </td>

                    <td className="p-3.5 font-bold text-slate-900">
                      {log.actionTitle}
                    </td>

                    <td className="p-3.5">
                      <p className="font-semibold text-slate-900">{log.username}</p>
                      <p className="text-[10px] text-slate-500 font-mono">{log.userId}</p>
                    </td>

                    <td className="p-3.5 max-w-xs truncate text-slate-600" title={log.targetResource}>
                      {log.targetResource}
                    </td>

                    <td className="p-3.5 font-mono text-[11px] text-slate-500">
                      {isAdmin ? log.ipAddress : '—'}
                    </td>

                    <td className="p-3.5 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                      {log.timestamp}
                    </td>

                    <td className="p-3.5 pl-5 text-center">
                      <button
                        onClick={(e) => { e.stopPropagation(); setSelectedLog(log); }}
                        className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg font-medium text-[11px] border border-slate-200"
                      >
                        بررسی
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Log Forensic Detail Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-lg w-full border border-slate-200 shadow-2xl p-6 space-y-4">
            
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Terminal className="w-5 h-5 text-blue-600" />
                <h2 className="text-sm font-bold text-slate-900">جزئیات تفصیلی لاگ امنیتی</h2>
              </div>
              <button onClick={() => setSelectedLog(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-slate-500">عنوان عملیات:</span>
                  <strong className="text-slate-900">{selectedLog.actionTitle}</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">شناسه یکتای رخداد:</span>
                  <span className="font-mono text-slate-600">{selectedLog.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">زمان دقیق:</span>
                  <span className="font-mono text-slate-900">{selectedLog.timestamp}</span>
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">شرح کامل رویداد:</label>
                <p className="p-3 bg-slate-50 text-slate-800 rounded-xl leading-relaxed border border-slate-200">
                  {selectedLog.details}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="text-slate-500 block">کاربر عامل:</span>
                  <span className="font-bold text-slate-900">{selectedLog.username} ({selectedLog.userRole})</span>
                </div>
                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="text-slate-500 block">آدرس مبدأ (IP):</span>
                  <span className="font-mono font-bold text-slate-900">{isAdmin ? selectedLog.ipAddress : 'مخفی'}</span>
                </div>
              </div>

              {isAdmin && selectedLog.userAgent && (
                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-[10px] text-slate-600 font-mono break-all">
                  <span className="font-bold block text-slate-800 mb-0.5">User Agent:</span>
                  {selectedLog.userAgent}
                </div>
              )}

            </div>

            <div className="pt-3 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold"
              >
                بستن پنجره
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
