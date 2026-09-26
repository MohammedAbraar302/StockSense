import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Package,
  BarChart3,
  PieChart,
  Download,
  Calendar,
  Filter
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell, PieChart as RePieChart, Pie } from 'recharts';
import apiClient from '../api/client';
import { useLocationScope } from '../store/locationContext';

const AnalyticsCard = ({ title, value, change, icon: Icon, trend }: any) => (
  <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
    <div className="flex items-center justify-between mb-4">
      <div className="p-2 bg-slate-100 text-slate-600 rounded-lg">
        <Icon size={20} />
      </div>
      <span className={`flex items-center gap-1 text-xs font-bold ${trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
        {trend === 'up' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
        {change}
      </span>
    </div>
    <div>
      <p className="text-sm font-medium text-slate-500">{title}</p>
      <h3 className="text-2xl font-bold text-slate-900 mt-1">{value}</h3>
    </div>
  </div>
);

const Reports: React.FC = () => {
  const { scope } = useLocationScope();

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics', scope],
    queryFn: async () => {
      const res = await apiClient.get('/analytics', {
        params: { scope: scope.type, id: scope.id }
      });
      return res.data.data || res.data;
    },
    // Mock data for professional demonstration if backend is still seeding
    placeholderData: {
      kpis: {
        revenue: '₹12.4L',
        unitsSold: '4,200',
        avgOrderValue: '₹2,950',
        turnoverRate: '4.2x'
      },
      salesTrend: [
        { date: 'Sep 01', sales: 4000 }, { date: 'Sep 05', sales: 3000 }, { date: 'Sep 10', sales: 2000 },
        { date: 'Sep 15', sales: 2780 }, { date: 'Sep 20', sales: 1890 }, { date: 'Sep 25', sales: 2390 },
      ],
      categorySales: [
        { name: 'Steel', value: 400, color: '#3b82f6' },
        { name: 'Bolts', value: 300, color: '#10b981' },
        { name: 'Pipes', value: 200, color: '#f59e0b' },
        { name: 'Others', value: 100, color: '#6366f1' },
      ]
    }
  });

  if (isLoading) return <div className="flex items-center justify-center h-full text-slate-500">Loading Analytics...</div>;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Sales & Inventory Analytics</h1>
          <p className="text-slate-500">Performance metrics and business intelligence</p>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
            <Calendar size={16} />
            Last 30 Days
          </button>
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-all shadow-sm">
            <Download size={16} />
            Export CSV
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <AnalyticsCard title="Total Revenue" value={analytics?.kpis.revenue} change="+12.5%" icon={DollarSign} trend="up" />
        <AnalyticsCard title="Units Sold" value={analytics?.kpis.unitsSold} change="+8.2%" icon={Package} trend="up" />
        <AnalyticsCard title="Avg Order Value" value={analytics?.kpis.avgOrderValue} change="-2.1%" icon={BarChart3} trend="down" />
        <AnalyticsCard title="Turnover Rate" value={analytics?.kpis.turnoverRate} change="+0.4x" icon={TrendingUp} trend="up" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Sales Trend Chart */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp size={18} className="text-blue-600" />
              Revenue Trend
            </h3>
            <select className="text-xs bg-slate-100 border-none rounded-md p-1 outline-none">
              <option>Daily</option>
              <option>Weekly</option>
              <option>Monthly</option>
            </select>
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={analytics?.salesTrend}>
                <defs>
                  <linearGradient id="colorSales" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#94a3b8'}} />
                <YAxis axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#94a3b8'}} />
                <Tooltip
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                />
                <Area type="monotone" dataKey="sales" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorSales)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Category Distribution Chart */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-slate-900 flex items-center gap-2">
              <PieChart size={18} className="text-blue-600" />
              Sales by Category
            </h3>
          </div>
          <div className="h-72 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <RePieChart>
                <Pie
                  data={analytics?.categorySales}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {analytics?.categorySales.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </RePieChart>
            </ResponsiveContainer>
            <div className="absolute flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-bold text-slate-900">Total</span>
              <span className="text-xs text-slate-500">Volume</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 mt-4">
            {analytics?.categorySales.map((cat: any) => (
              <div key={cat.name} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: cat.color }} />
                <span className="text-xs text-slate-600 font-medium">{cat.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Reports;
