import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, Warehouse, Location } from '../types';

interface LocationScope {
  type: 'ALL' | 'WAREHOUSE' | 'LOCATION' | 'BIN';
  id?: string;
  name?: string;
}

interface LocationContextType {
  scope: LocationScope;
  setScope: (scope: LocationScope) => void;
  warehouseId?: string;
  locationId?: string;
  binId?: string;
}

const LocationContext = createContext<LocationContextType | undefined>(undefined);

export const LocationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [scope, setScope] = useState<LocationScope>({ type: 'ALL' });

  const warehouseId = scope.type === 'WAREHOUSE' || scope.type === 'LOCATION' || scope.type === 'BIN' ? scope.id : undefined;
  const locationId = scope.type === 'LOCATION' || scope.type === 'BIN' ? scope.id : undefined; // Simplification: in reality, we'd track parent IDs
  const binId = scope.type === 'BIN' ? scope.id : undefined;

  return (
    <LocationContext.Provider value={{ scope, setScope, warehouseId, locationId, binId }}>
      {children}
    </LocationContext.Provider>
  );
};

export const useLocationScope = () => {
  const context = useContext(LocationContext);
  if (!context) {
    throw new Error('useLocationScope must be used within a LocationProvider');
  }
  return context;
};
