import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard,
  AlertTriangle,
  Package,
  TrendingUp,
  Clock
} from 'lucide-react';
import apiClient from '../api/client';
import { useLocationScope } from '../store/locationContext';

const StatCard = ({ title, value, icon: Icon, color, trend }: any) => (
  <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <h3 className="text-2xl font-bold text-slate-900 mt-1">{value}</h3>
        {trend && (
          <p className={`text-xs mt-2 ${trend > 0 ? 'text-green-600' : 'text-red-600'} font-medium`}>
            {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% from last month
          </p>
        )}
      </div>
      <div className={`p-3 rounded-xl ${color}`}>
        <Icon size={20} className="text-white" />
      </div>
    </div>
  </div>
);

const Dashboard: React.FC = () => {
  const { scope } = useLocationScope();

  // In a real app, these would be separate endpoints or a single dashboard summary endpoint
  // For now, we simulate the query structure
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats', scope],
    queryFn: async () => {
      // const res = await apiClient.get('/dashboard/stats', { params: { scope: scope.type, id: scope.id } });
      // return res.data;

      // Mock data for visual demonstration until endpoints are refined
      return {
        totalProducts: '1,240',
        lowStock: '12',
        outOfStock: '3',
        pendingReceipts: '8',
        inventoryValue: '₹42.5L',
        todaySales: '₹12,400'
      };
    }
  });

  if (isLoading) return <div className="flex items-center justify-center h-full text-slate-500">Loading Dashboard...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Operational Overview</h1>
          <p className="text-slate-500">Real-time inventory health and movement</p>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
            Export Report
          </button>
          <button className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
            New Operation
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title="Total Products"
          value={stats?.totalProducts}
          icon={Package}
          color="bg-blue-500"
          trend={12}
        />
        <StatCard
          title="Low Stock Alerts"
          value={stats?.lowStock}
          icon={AlertTriangle}
          color="bg-amber-500"
          trend={-5}
        />
        <StatCard
          title="Out of Stock"
          value={stats?.outOfStock}
          icon={Clock}
          color="bg-red-500"
        />
        <StatCard
          title="Inventory Value"
          value={stats?.inventoryValue}
          icon={TrendingUp}
          color="bg-emerald-500"
          trend={8}
        />
        <StatCard
          title="Pending Receipts"
          value={stats?.pendingReceipts}
          icon={LayoutDashboard}
          color="bg-indigo-500"
        />
        <StatCard
          title="Today's Revenue"
          value={stats?.todaySales}
          icon={TrendingUp}
          color="bg-violet-500"
          trend={15}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <h3 className="text-lg font-bold text-slate-900 mb-4">Recent Movements</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-slate-500 border-b border-slate-100">
                  <th className="pb-3 font-medium">Product</th>
                  <th className="pb-3 font-medium">Operation</th>
                  <th className="pb-3 font-medium">Qty</th>
                  <th className="pb-3 font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {[1, 2, 3, 4, 5].map((i) => (
                  <tr key={i} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 font-medium text-slate-700">Industrial Bolt X-200</td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">Receipt</span>
                    </td>
                    <td className="py-3 text-slate-600">+500</td>
                    <td className="py-3 text-slate-400">2h ago</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <h3 className="text-lg font-bold text-slate-900 mb-4">Critical Alerts</h3>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-red-50 border border-red-100">
                <div className="p-2 bg-red-100 text-red-600 rounded-lg">
                  <AlertTriangle size={16} />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-red-900">Steel Rods (12mm)</p>
                  <p className="text-xs text-red-700">Stock dropped below reorder level (10 units left)</p>
                </div>
                <button className="text-xs font-bold text-red-600 hover:underline">Order Now</button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
