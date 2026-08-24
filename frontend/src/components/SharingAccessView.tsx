import React from 'react';
export const SharingAccessView: React.FC<{ enabled?: boolean }> = ({ enabled = true }) => (
  <div className="bg-white rounded-2xl p-6 border border-[#E8D9C4] space-y-2">
    <h1 className="text-lg font-bold text-[#4A2C17]">اشتراک‌گذاری و کنترل دسترسی دانه‌ای</h1>
    <p className="text-xs text-[#6B5344] leading-relaxed">فاز ۴: پیوند امن و RBAC داخلی/خارجی. در این نسخه فقط اسکلت ماژول آماده است و ایجاد پیوند عمومی غیرفعال است.</p>
    {!enabled && <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-xl p-3">این فاز با پرچم پیکربندی خاموش است.</p>}
  </div>
);
