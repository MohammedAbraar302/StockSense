import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Plus,
  ArrowUpRight,
  ArrowDownLeft,
  ArrowLeftRight,
  RotateCcw,
  Filter,
  Search,
  ChevronRight,
  Package,
  Truck,
  Warehouse as WarehouseIcon
} from 'lucide-react';
import apiClient from '../api/client';
import { useLocationScope } from '../store/locationContext';
import CreateReceiptModal from '../components/CreateReceiptModal';
import CreateDeliveryModal from '../components/CreateDeliveryModal';
import CreateTransferModal from '../components/CreateTransferModal';
import CreateAdjustmentModal from '../components/CreateAdjustmentModal';

type OperationType = 'RECEIPT' | 'DELIVERY' | 'TRANSFER' | 'ADJUSTMENT';

type OperationType = 'RECEIPT' | 'DELIVERY' | 'TRANSFER' | 'ADJUSTMENT';

type OperationType = 'RECEIPT' | 'DELIVERY' | 'TRANSFER' | 'ADJUSTMENT';

type OperationType = 'RECEIPT' | 'DELIVERY' | 'TRANSFER' | 'ADJUSTMENT';

type OperationType = 'RECEIPT' | 'DELIVERY' | 'TRANSFER' | 'ADJUSTMENT';

const OperationCard = ({
  type,
  title,
  description,
  icon: Icon,
  color,
  count,
  onClick
}: {
  type: OperationType,
  title: string,
  description: string,
  icon: any,
  color: string,
  count: number,
  onClick: () => void
}) => (
  <button
    onClick={onClick}
    className="flex items-start gap-4 p-6 bg-white border border-slate-200 rounded-2xl text-left hover:border-blue-400 hover:shadow-md transition-all group"
  >
    <div className={`p-3 rounded-xl ${color} text-white group-hover:scale-110 transition-transform`}>
      <Icon size={24} />
    </div>
    <div className="flex-1">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-slate-900">{title}</h3>
        <span className="text-xs font-semibold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
          {count} Pending
        </span>
      </div>
      <p className="text-sm text-slate-500 mt-1">{description}</p>
    </div>
    <ChevronRight size={20} className="text-slate-300 group-hover:text-blue-500 transition-colors" />
  </button>
);

const Operations: React.FC = () => {
  const { scope } = useLocationScope();
  const [activeTab, setActiveTab] = useState<'MENU' | OperationType>('MENU');
  const [searchTerm, setSearchTerm] = useState('');
  const [isReceiptModalOpen, setIsReceiptModalOpen] = useState(false);
  const [isDeliveryModalOpen, setIsDeliveryModalOpen] = useState(false);
  const [isTransferModalOpen, setIsTransferModalOpen] = useState(false);
  const [isAdjustmentModalOpen, setIsAdjustmentModalOpen] = useState(false);

  const { data: operations, isLoading } = useQuery({
    queryKey: ['operations', activeTab, searchTerm, scope],
    queryFn: async () => {
      if (activeTab === 'MENU') return null;
      const endpoint = `/operations/${activeTab.toLowerCase()}s`;
      const res = await apiClient.get(endpoint, {
        params: { q: searchTerm, scope: scope.type, id: scope.id }
      });
      return res.data.data || res.data;
    }
  });

  const renderMenu = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <OperationCard
        type="RECEIPT"
        title="Stock Receipt"
        description="Receive incoming goods from suppliers and update inventory."
        icon={ArrowDownLeft}
        color="bg-emerald-500"
        count={8}
        onClick={() => setActiveTab('RECEIPT')}
      />
      <OperationCard
        type="DELIVERY"
        title="Delivery Order"
        description="Ship products to customers and reduce available stock."
        icon={ArrowUpRight}
        color="bg-blue-500"
        count={5}
        onClick={() => setActiveTab('DELIVERY')}
      />
      <OperationCard
        type="TRANSFER"
        title="Internal Transfer"
        description="Move inventory between warehouses or racks/bins."
        icon={ArrowLeftRight}
        color="bg-indigo-500"
        count={3}
        onClick={() => setActiveTab('TRANSFER')}
      />
      <OperationCard
        type="ADJUSTMENT"
        title="Stock Adjustment"
        description="Reconcile physical counts with system records."
        icon={RotateCcw}
        color="bg-amber-500"
        count={2}
        onClick={() => setActiveTab('ADJUSTMENT')}
      />
    </div>
  );

  const renderList = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <button
          onClick={() => setActiveTab('MENU')}
          className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-blue-600 transition-colors"
        >
          <ArrowLeftRight size={16} />
          Back to Operations Menu
        </button>
        {activeTab === 'RECEIPT' && (
          <button
            onClick={() => setIsReceiptModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-all shadow-sm"
          >
            <Plus size={18} />
            Create New Receipt
          </button>
        )}
        {activeTab === 'DELIVERY' && (
          <button
            onClick={() => setIsDeliveryModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-all shadow-sm"
          >
            <Plus size={18} />
            Create New Delivery
          </button>
        )}
        {activeTab === 'TRANSFER' && (
          <button
            onClick={() => setIsTransferModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-all shadow-sm"
          >
            <Plus size={18} />
            Create New Transfer
          </button>
        )}
        {activeTab === 'ADJUSTMENT' && (
          <button
            onClick={() => setIsAdjustmentModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-all shadow-sm"
          >
            <Plus size={18} />
            Create New Adjustment
          </button>
        )}
        {activeTab !== 'RECEIPT' && activeTab !== 'DELIVERY' && activeTab !== 'TRANSFER' && activeTab !== 'ADJUSTMENT' && (
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-all shadow-sm">
            <Plus size={18} />
            Create New {activeTab}
          </button>
        )}
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={`Search ${activeTab}s...`}
            className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-all"
          />
        </div>
        <button className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
          <Filter size={16} />
          Filters
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        {isLoading ? (
          <div className="text-center py-20 text-slate-500">Loading operations...</div>
        ) : operations && operations.length > 0 ? (
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Total Items</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {operations.map((op: any) => (
                <tr key={op.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-slate-600">#{op.id.slice(0, 8)}</td>
                  <td className="px-4 py-3 text-slate-600">{new Date(op.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      op.status === 'DONE' ? 'bg-green-100 text-green-700' :
                      op.status === 'DRAFT' ? 'bg-slate-100 text-slate-700' : 'bg-amber-100 text-amber-700'
                    }`}>
                      {op.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{op.items_count || 0}</td>
                  <td className="px-4 py-3 text-right">
                    <button className="text-blue-600 hover:underline font-medium">View Details</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-center py-20 text-slate-500">No {activeTab.toLowerCase()}s found.</div>
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Inventory Operations</h1>
          <p className="text-slate-500">Execute and track stock movements</p>
        </div>
      </div>

      {activeTab === 'MENU' ? renderMenu() : renderList()}

      <CreateReceiptModal
        isOpen={isReceiptModalOpen}
        onClose={() => setIsReceiptModalOpen(false)}
        onSuccess={() => setIsReceiptModalOpen(false)}
      />

      <CreateDeliveryModal
        isOpen={isDeliveryModalOpen}
        onClose={() => setIsDeliveryModalOpen(false)}
        onSuccess={() => setIsDeliveryModalOpen(false)}
      />

      <CreateTransferModal
        isOpen={isTransferModalOpen}
        onClose={() => setIsTransferModalOpen(false)}
        onSuccess={() => setIsTransferModalOpen(false)}
      />

      <CreateAdjustmentModal
        isOpen={isAdjustmentModalOpen}
        onClose={() => setIsAdjustmentModalOpen(false)}
        onSuccess={() => setIsAdjustmentModalOpen(false)}
      />
    </div>
  );
};

export default Operations;
