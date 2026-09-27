import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Save, Calendar, Warehouse, MapPin, CheckCircle, AlertTriangle, FileText, ChevronRight } from 'lucide-react';
import apiClient from '../api/client';
import { useLocationScope } from '../store/locationContext';

const eodSchema = z.object({
  location_id: z.string().min(1, 'Location is required'),
  date: z.string().min(1, 'Date is required'),
  physical_counts: z.array(z.object({
    product_id: z.string().min(1, 'Product is required'),
    actual_quantity: z.number().min(0),
    variance_explanation: z.string().optional(),
  })).min(1, 'At least one count is required'),
});

type EODFormValues = z.infer<typeof eodSchema>;

const EODClosingModal = ({ isOpen, onClose, onSuccess }: { isOpen: boolean, onClose: () => void, onSuccess: () => void }) => {
  const { scope } = useLocationScope();
  const queryClient = useQueryClient();

  const { register, handleSubmit, formState: { errors } } = useForm<EODFormValues>({
    resolver: zodResolver(eodSchema),
    defaultValues: {
      location_id: scope.locationId || '',
      date: new Date().toISOString().split('T')[0],
    }
  });

  const mutation = useMutation({
    mutationFn: async (data: EODFormValues) => {
      const res = await apiClient.post('/reconciliation/daily-closing', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reconciliation'] });
      onSuccess();
    }
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-slate-200 flex flex-col max-h-[90vh]">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
              <Calendar size={20} />
            </div>
            <h2 className="text-xl font-bold text-slate-900">End-of-Day Reconciliation</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <XCircle size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit((data) => mutation.mutate(data))} className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Location</label>
              <input
                {...register('location_id')}
                className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Location ID"
              />
              {errors.location_id && <p className="text-xs text-red-500">{errors.location_id.message}</p>}
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Closing Date</label>
              <input
                type="date"
                {...register('date')}
                className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
              />
              {errors.date && <p className="text-xs text-red-500">{errors.date.message}</p>}
            </div>
            <div className="flex items-end pb-2">
              <div className="bg-blue-50 text-blue-700 p-2 rounded-lg text-xs font-medium w-full text-center border border-blue-100">
                All stock movements for this date will be locked.
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-bold text-slate-700 uppercase">Physical Count Verification</h3>
            <div className="bg-slate-50 rounded-xl border border-slate-200 overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-100 text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 font-medium">Product</th>
                    <th className="px-4 py-3 font-medium text-center">Expected</th>
                    <th className="px-4 py-3 font-medium text-center">Actual</th>
                    <th className="px-4 py-3 font-medium text-center">Variance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {[1, 2, 3].map((i) => (
                    <tr key={i} className="hover:bg-white transition-colors">
                      <td className="px-4 py-3 font-medium text-slate-700">Industrial Bolt X-200</td>
                      <td className="px-4 py-3 text-center text-slate-500">150</td>
                      <td className="px-4 py-3 text-center">
                        <input type="number" className="w-20 p-1 border border-slate-200 rounded text-center" defaultValue="148" />
                      </td>
                      <td className="px-4 py-3 text-center font-bold text-red-600">-2</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </form>

        <div className="p-6 border-t border-slate-100 flex items-center justify-between bg-slate-50 rounded-b-2xl">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800">Cancel</button>
          <button
            onClick={() => handleSubmit((data) => mutation.mutate(data))()}
            disabled={mutation.isPending}
            className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 transition-all disabled:opacity-50 shadow-sm"
          >
            {mutation.isPending ? 'Locking Date...' : (
              <>
                <Save size={18} />
                Finalize Daily Closing
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

const Reconciliation: React.FC = () => {
  const { scope } = useLocationScope();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: history, isLoading } = useQuery({
    queryKey: ['reconciliation', scope],
    queryFn: async () => {
      const res = await apiClient.get('/reconciliation/history', {
        params: { scope: scope.type, id: scope.id }
      });
      return res.data.data || res.data;
    }
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Daily Reconciliation</h1>
          <p className="text-slate-500">Verify physical stock against system records to close the day</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-all shadow-sm"
        >
          <Calendar size={18} />
          Start Daily Closing
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-6 border-b border-slate-100">
            <h3 className="font-bold text-slate-900">Closing History</h3>
          </div>
          {isLoading ? (
            <div className="text-center py-20 text-slate-500">Loading history...</div>
          ) : history && history.length > 0 ? (
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Location</th>
                  <th className="px-4 py-3 font-medium text-center">Total Variance</th>
                  <th className="px-4 py-3 font-medium text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {history.map((entry: any) => (
                  <tr key={entry.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 text-slate-600">{entry.date}</td>
                    <td className="px-4 py-3 font-medium text-slate-700">{entry.location_name}</td>
                    <td className={`px-4 py-3 text-center font-bold ${entry.total_variance === 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {entry.total_variance}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">Closed</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-20 text-slate-500">No closing records found for this scope.</div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
              <AlertTriangle size={18} className="text-amber-500" />
              Closing Guidelines
            </h3>
            <ul className="space-y-3 text-sm text-slate-600">
              <li className="flex gap-2">
                <CheckCircle size={16} className="text-green-500 shrink-0" />
                <span>Verify all receipts are entered.</span>
              </li>
              <li className="flex gap-2">
                <CheckCircle size={16} className="text-green-500 shrink-0" />
                <span>Verify all deliveries are processed.</span>
              </li>
              <li className="flex gap-2">
                <CheckCircle size={16} className="text-green-500 shrink-0" />
                <span>Confirm no pending transfers.</span>
              </li>
            </ul>
          </div>
          <div className="bg-blue-600 p-6 rounded-2xl shadow-sm text-white">
            <h3 className="font-bold mb-2 flex items-center gap-2">
              <FileText size={18} />
              EOD Report
            </h3>
            <p className="text-blue-100 text-xs mb-4">Generate a printable summary of today's closing variance.</p>
            <button className="w-full py-2 bg-white text-blue-600 rounded-lg text-xs font-bold hover:bg-blue-50 transition-colors">
              Download PDF
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Reconciliation;
