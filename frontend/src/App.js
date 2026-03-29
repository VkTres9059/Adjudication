import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Claims from "./pages/Claims";
import ClaimDetail from "./pages/ClaimDetail";
import Plans from "./pages/Plans";
import PlanBuilder from "./pages/PlanBuilder";
import Members from "./pages/Members";
import Duplicates from "./pages/Duplicates";
import FeeSchedule from "./pages/FeeSchedule";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import PriorAuth from "./pages/PriorAuth";
import Network from "./pages/Network";
import CodeDatabase from "./pages/CodeDatabase";
import Layout from "./components/Layout";
import "./App.css";

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F7F4] flex items-center justify-center">
        <div className="text-[#64645F]">Loading...</div>
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return children;
};

function AppRoutes() {
  const { isAuthenticated } = useAuth();
  
  return (
    <Routes>
      <Route 
        path="/login" 
        element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />} 
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="claims" element={<Claims />} />
        <Route path="claims/:id" element={<ClaimDetail />} />
        <Route path="plans" element={<Plans />} />
        <Route 
          path="plans/new" 
          element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <PlanBuilder />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="plans/:id/edit" 
          element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <PlanBuilder />
            </ProtectedRoute>
          } 
        />
        <Route path="members" element={<Members />} />
        <Route path="fee-schedule" element={<FeeSchedule />} />
        <Route path="duplicates" element={<Duplicates />} />
        <Route path="prior-auth" element={<PriorAuth />} />
        <Route path="network" element={<Network />} />
        <Route path="code-database" element={<CodeDatabase />} />
        <Route path="reports" element={<Reports />} />
        <Route 
          path="settings" 
          element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <Settings />
            </ProtectedRoute>
          } 
        />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
