import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Filter, Warehouse, MapPin, Box, ArrowRight } from 'lucide-react';
import apiClient from '../api/client';
import { Inventory } from '../types';
import { useLocationScope } from '../store/locationContext';

const InventoryTable = ({ data, isLoading }: { data: Inventory[], isLoading: boolean }) => {
  if (isLoading) return <div className="text-center py-20 text-slate-500">Loading inventory levels...</div>;
  if (data.length === 0) return <div className="text-center py-20 text-slate-500">No inventory found for selected scope.</div>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
          <tr>
            <th className="px-4 py-3 font-medium">Product</th>
            <th className="px-4 py-3 font-medium">Warehouse</th>
            <th className="px-4 py-3 font-medium">Location/Bin</th>
            <th className="px-4 py-3 font-medium text-center">On Hand</th>
            <th className="px-4 py-3 font-medium text-center">Available</th>
            <th className="px-4 py-3 font-medium text-center">Reserved</th>
            <th className="px-4 py-3 font-medium text-center">Damaged</th>
            <th className="px-4 py-3 font-medium text-right">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {data.map((item) => (
            <tr key={item.id} className="hover:bg-slate-50 transition-colors">
              <td className="px-4 py-3 font-medium text-slate-700">
                <div className="flex items-center gap-2">
                  <Box size={14} className="text-slate-400" />
                  <span>Product #{item.product_id.slice(0, 8)}...</span>
                </div>
              </td>
              <td className="px-4 py-3 text-slate-600">
                <div className="flex items-center gap-1">
                  <Warehouse size={14} className="text-slate-400" />
                  <span>WH-01</span>
                </div>
              </td>
              <td className="px-4 py-3 text-slate-600">
                <div className="flex items-center gap-1">
                  <MapPin size={14} className="text-slate-400" />
                  <span>Rack A-01</span>
                </div>
              </td>
              <td className="px-4 py-3 text-center font-semibold text-slate-900">{item.quantity_on_hand}</td>
              <td className="px-4 py-3 text-center font-bold text-blue-600">{item.quantity_available}</td>
              <td className="px-4 py-3 text-center text-slate-600">{item.quantity_reserved}</td>
              <td className="px-4 py-3 text-center text-red-500">{item.quantity_damaged}</td>
              <td className="px-4 py-3 text-right">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  item.quantity_available > 10 ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                }`}>
                  {item.quantity_available > 10 ? 'Healthy' : 'Low'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const Inventory: React.FC = () => {
  const { scope } = useLocationScope();
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['inventory', searchTerm, scope],
    queryFn: async () => {
      const res = await apiClient.get('/inventory', {
        params: { q: searchTerm, scope: scope.type, id: scope.id }
      });
      return res.data.data || res.data;
    }
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Stock Ledger</h1>
          <p className="text-slate-500">Real-time inventory positions across all bins</p>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
            Export Stock List
          </button>
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-all shadow-sm">
            <ArrowRight size={18} />
            Create Movement
          </button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by product or SKU..."
            className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-all"
          />
        </div>
        <button className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
          <Filter size={16} />
          Filters
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <InventoryTable data={data || []} isLoading={isLoading} />
      </div>
    </div>
  );
};

export default Inventory;
