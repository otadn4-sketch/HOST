import React, { useState } from 'react';
import { GitFork } from 'lucide-react';
import { DataApi } from '../services/api';

export const RelationshipGraphView: React.FC<{ enabled: boolean }> = ({ enabled }) => {
  const [data, setData] = useState<any | null>(null);
  const [error, setError] = useState('');
  const load = async () => {
    try {
      const res = await DataApi.relationshipGraph();
      setData(res.graph);
      setError('');
    } catch (e: any) {
      setError(e.message || 'گراف فقط روی localhost در دسترس است.');
    }
  };
  return (
    <div className="bg-white rounded-2xl p-6 border border-[#E8D9C4] space-y-3">
      <h1 className="text-lg font-bold text-[#4A2C17] flex items-center gap-2"><GitFork className="w-5 h-5" /> گراف تعاملات (محلی)</h1>
      <p className="text-xs text-[#6B5344] leading-relaxed">این گراف فقط برای محیط local / localhost است و روی وب عمومی production قرار نمی‌گیرد. اگر میزبان localhost نباشد، API داده برنمی‌گرداند.</p>
      {!enabled && <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-xl p-3">فاز ۵ خاموش است.</p>}
      <button onClick={load} className="px-3 py-2 text-xs bg-[#4A2C17] text-white rounded-xl font-bold">تلاش برای بارگذاری گراف محلی</button>
      {error && <p className="text-xs text-red-700">{error}</p>}
      {data && <p className="text-xs text-[#6B5344]">{data.nodes?.length || 0} گره • {data.edges?.length || 0} یال</p>}
    </div>
  );
};
