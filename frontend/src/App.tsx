import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LocationProvider } from './store/locationContext';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Products from './pages/Products';
import Inventory from './pages/Inventory';
import Operations from './pages/Operations';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import Reconciliation from './pages/Reconciliation';
import Layout from './layouts/Layout';

const App: React.FC = () => {
  const isAuthenticated = !!localStorage.getItem('accessToken');

  return (
    <LocationProvider>
      <Routes>
        <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" replace />} />

        <Route
          path="/"
          element={isAuthenticated ? <Layout><Dashboard /></Layout> : <Navigate to="/login" replace />}
        >
          <Route index element={<Dashboard />} />
          <Route path="products" element={<Products />} />
          <Route path="inventory" element={<Inventory />} />
          <Route path="operations" element={<Operations />} />
          <Route path="reconciliation" element={<Reconciliation />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </LocationProvider>
  );
};

export default App;
