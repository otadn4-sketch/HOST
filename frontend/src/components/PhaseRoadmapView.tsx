import React, { useEffect, useState } from 'react';
import { Map } from 'lucide-react';
import { DataApi } from '../services/api';

export const PhaseRoadmapView: React.FC = () => {
  const [data, setData] = useState<any | null>(null);
  useEffect(() => {
    DataApi.phases().then(setData).catch(() => undefined);
  }, []);
  return (
    <div className="space-y-4">
      <div className="bg-white rounded-2xl p-5 border border-[#E8D9C4]">
        <h1 className="text-lg font-bold text-[#4A2C17] flex items-center gap-2"><Map className="w-5 h-5" /> نقشه راه پنج‌فاز</h1>
        <p className="text-xs text-[#6B5344] mt-2">{data?.automated_delivery_note}</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {(data?.phases || []).map((p: any) => (
          <div key={p.id} className="bg-white rounded-2xl p-4 border border-[#E8D9C4]">
            <p className="text-xs font-bold text-[#4A2C17]">فاز {p.id}: {p.title}</p>
            <p className="text-[11px] text-[#6B5344] mt-1">{p.summary}</p>
            <p className={`text-[11px] mt-2 font-bold ${p.enabled ? 'text-emerald-700' : 'text-amber-800'}`}>{p.enabled ? 'فعال' : 'خاموش / اسکلت'}</p>
          </div>
        ))}
      </div>
      {data?.faran && (
        <div className="bg-white rounded-2xl p-4 border border-[#E8D9C4] text-xs text-[#6B5344]">
          اتصال فاران: {data.faran.configured ? 'پیکربندی شده' : 'پیکربندی نشده'} • حالت {data.faran.mode} • شبکه {data.faran.allow_network ? 'مجاز' : 'مسدود (stub)'}
        </div>
      )}
    </div>
  );
};
