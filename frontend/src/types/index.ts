export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'ADMIN' | 'INVENTORY_MANAGER' | 'WAREHOUSE_STAFF';
  is_verified: boolean;
  created_at: string;
}

export interface Warehouse {
  id: string;
  name: string;
  code: string;
  address: string;
  manager_id?: string;
}

export interface Location {
  id: string;
  warehouse_id: string;
  name: string;
  type: 'RACK' | 'SHELF' | 'BIN' | 'ZONE';
  parent_id?: string;
}

export interface Product {
  id: string;
  name: string;
  sku: string;
  category_id: string;
  unit_of_measure: string;
  description?: string;
  reorder_level: number;
  reorder_quantity: number;
  status: 'ACTIVE' | 'INACTIVE' | 'DISCONTINUED';
}

export interface Inventory {
  id: string;
  product_id: string;
  warehouse_id: string;
  location_id: string;
  bin_id?: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
  quantity_damaged: number;
}

export interface InventoryMovement {
  id: string;
  product_id: string;
  warehouse_id: string;
  location_id: string;
  bin_id?: string;
  operation_type: 'RECEIPT' | 'DELIVERY' | 'TRANSFER_OUT' | 'TRANSFER_IN' | 'ADJUSTMENT' | 'DAMAGE' | 'RETURN' | 'INITIAL_STOCK';
  quantity_change: number;
  quantity_before: number;
  quantity_after: number;
  user_id: string;
  reference_id?: string;
  created_at: string;
}

export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  user: User;
}

export interface APIResponse<T> {
  data: T;
  message?: string;
}

export interface APIError {
  error: {
    code: string;
    message: string;
    details?: any;
  };
}
