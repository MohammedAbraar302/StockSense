import React, { useState } from 'react';
import { useNavigate, Outlet, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Box,
  ArrowLeftRight,
  ClipboardList,
  BarChart3,
  Settings,
  LogOut,
  Bell,
  Search,
  ChevronDown,
  Warehouse
} from 'lucide-react';
import { useLocationScope } from '../store/locationContext';

const Layout: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const { scope, setScope } = useLocationScope();
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    navigate('/login');
  };

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
    { icon: Box, label: 'Products', path: '/products' },
    { icon: ArrowLeftRight, label: 'Operations', path: '/operations' },
    { icon: ClipboardList, label: 'Inventory', path: '/inventory' },
    { icon: BarChart3, label: 'Reports', path: '/reports' },
    { icon: Settings, label: 'Settings', path: '/settings' },
  ];

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col shrink-0">
        <div className="p-6">
          <div className="flex items-center gap-2 text-blue-600 font-bold text-2xl tracking-tight">
            <div className="bg-blue-600 text-white p-1 rounded-lg">
              <Box size={24} />
            </div>
            <span>StockSense</span>
          </div>
        </div>

        <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
          {menuItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                window.location.pathname === item.path
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <item.icon size={18} />
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-200">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2 text-sm font-medium text-slate-600 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors"
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-4 flex-1">
            {/* Search */}
            <div className="relative max-w-md w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input
                type="text"
                placeholder="Search products, SKUs, orders..."
                className="w-full pl-10 pr-4 py-1.5 bg-slate-100 border-transparent focus:bg-white focus:ring-2 focus:ring-blue-500 rounded-full text-sm outline-none transition-all"
              />
            </div>

            {/* Location Selector */}
            <div className="flex items-center gap-2 ml-4 bg-slate-100 p-1 rounded-full border border-slate-200">
              <div className="pl-2 pr-1">
                <Warehouse size={14} className="text-slate-500" />
              </div>
              <button
                onClick={() => setScope({ type: 'ALL' })}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                  scope.type === 'ALL' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                All Locations
              </button>
              {/* In a real app, this would be a dropdown with warehouses/bins */}
              <div className="flex items-center px-2 text-slate-400">
                <ChevronDown size={14} />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="relative p-2 text-slate-500 hover:bg-slate-100 rounded-full transition-colors">
              <Bell size={20} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
            </button>
            <div className="flex items-center gap-3 pl-4 border-l border-slate-200">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-semibold text-slate-900">Admin User</p>
                <p className="text-xs text-slate-500">Super Administrator</p>
              </div>
              <div className="w-8 h-8 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center font-bold text-xs">
                AU
              </div>
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {children || <Outlet />}
        </div>
      </main>
    </div>
  );
};

export default Layout;
