import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Plus, Trash2, Save, XCircle, AlertCircle, Truck } from 'lucide-react';
import apiClient from '../api/client';
import { useLocationScope } from '../store/locationContext';

const deliverySchema = z.object({
  customer_id: z.string().min(1, 'Customer is required'),
  warehouse_id: z.string().min(1, 'Warehouse is required'),
  location_id: z.string().min(1, 'Location is required'),
  notes: z.string().optional(),
  items: z.array(z.object({
    product_id: z.string().min(1, 'Product is required'),
    quantity: z.number().min(1, 'Quantity must be at least 1'),
  })).min(1, 'At least one item is required'),
});

type DeliveryFormValues = z.infer<typeof deliverySchema>;

const CreateDeliveryModal = ({ isOpen, onClose, onSuccess }: { isOpen: boolean, onClose: () => void, onSuccess: () => void }) => {
  const { scope } = useLocationScope();
  const queryClient = useQueryClient();

  const { register, control, handleSubmit, formState: { errors } } = useForm<DeliveryFormValues>({
    resolver: zodResolver(deliverySchema),
    defaultValues: {
      items: [{ product_id: '', quantity: 1 }],
      warehouse_id: scope.warehouseId || '',
      location_id: scope.locationId || '',
    }
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'items',
  });

  const mutation = useMutation({
    mutationFn: async (data: DeliveryFormValues) => {
      const res = await apiClient.post('/operations/deliveries', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['operations'] });
      onSuccess();
    }
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white w-full max-w-3xl rounded-2xl shadow-2xl border border-slate-200 flex flex-col max-h-[90vh]">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
              <Truck size={20} />
            </div>
            <h2 className="text-xl font-bold text-slate-900">Create Delivery Order</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <XCircle size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit((data) => mutation.mutate(data))} className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Customer</label>
              <select
                {...register('customer_id')}
                className="w-full p-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="">Select Customer</option>
                <option value="cust_1">Retail Hub India</option>
                <option value="cust_2">BuildCorp Construction</option>
              </select>
              {errors.customer_id && <p className="text-xs text-red-500">{errors.customer_id.message}</p>}
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Warehouse</label>
              <input
                {...register('warehouse_id')}
                className="w-full p-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                placeholder="Warehouse ID"
              />
              {errors.warehouse_id && <p className="text-xs text-red-500">{errors.warehouse_id.message}</p>}
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-500 uppercase">Location/Bin</label>
              <input
                {...register('location_id')}
                className="w-full p-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                placeholder="Bin ID"
              />
              {errors.location_id && <p className="text-xs text-red-500">{errors.location_id.message}</p>}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-500 uppercase">Items to Deliver</label>
              <button
                type="button"
                onClick={() => append({ product_id: '', quantity: 1 })}
                className="flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-blue-700"
              >
                <Plus size={14} /> Add Item
              </button>
            </div>

            <div className="space-y-2">
              {fields.map((field, index) => (
                <div key={field.id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <div className="flex-1 space-y-1">
                    <select
                      {...register(`items.${index}.product_id`)}
                      className="w-full p-2 bg-white border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Select Product</option>
                      <option value="prod_1">Steel Rods (12mm)</option>
                      <option value="prod_2">Industrial Bolts X-200</option>
                    </select>
                  </div>
                  <div className="w-32 space-y-1">
                    <input
                      type="number"
                      {...register(`items.${index}.quantity`, { valueAsNumber: true })}
                      className="w-full p-2 bg-white border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => remove(index)}
                    className="p-2 text-slate-400 hover:text-red-500 transition-colors"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}
            </div>
            {errors.items && <p className="text-xs text-red-500">{errors.items.message as string}</p>}
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-500 uppercase">Delivery Notes</label>
            <textarea
              {...register('notes')}
              className="w-full p-2 border border-slate-200 rounded-lg h-20 outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter shipping instructions or special requirements..."
            />
          </div>
        </form>

        <div className="p-6 border-t border-slate-100 flex items-center justify-between bg-slate-50 rounded-b-2xl">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800"
          >
            Cancel
          </button>
          <div className="flex gap-3">
            <button
              onClick={() => handleSubmit((data) => mutation.mutate(data))()}
              disabled={mutation.isPending}
              className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 transition-all disabled:opacity-50 shadow-sm"
            >
              {mutation.isPending ? 'Processing...' : (
                <>
                  <Save size={18} />
                  Create Delivery
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateDeliveryModal;
