import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { SidebarProvider } from "@/components/ui/sidebar";
import AdminLayout from "./components/AdminLayout";
import UserLayout from "./components/UserLayout"; 

// Admin Pages
import AdminDashboard from "./pages/Dashboard";
import Users from "./pages/Users";
import AIModels from "./pages/AIModels";
import AdminUsageAnalytics from "./pages/UsageAnalytics";
import AdminBilling from "./pages/Billing";
import Discounts from "./pages/Discounts";

// User Pages
import UserDashboard from "./pages/user/UserDashboard";
import UserBillingPage from "./pages/user/UserBillingPage";
import UserUsagePage from "./pages/user/UserUsagePage";
import ProfileSettingsPage from "./pages/user/ProfileSettingsPage";
import UserDiscountsPage from "./pages/user/UserDiscountsPage"; // NEW: Import discount page

// Public & Auth Pages
import NotFound from "./pages/NotFound";
import LoginPage from "./pages/LoginPage";
import SignUpPage from "./pages/SignUpPage"; 
import VerifyEmailPage from "./pages/VerifyEmailPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage"; 
import ResetPasswordPage from "./pages/ResetPasswordPage"; 
import LandingPage from "./pages/LandingPage";
import PaymentStatusPage from "./pages/PaymentStatusPage";

const queryClient = new QueryClient();

const PrivateRoute = () => {
  const isAuthenticated = !!localStorage.getItem("jwt_token");

  if (isAuthenticated) {
    return <Outlet />;
  }

  return <Navigate to="/login" replace />;
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Navigate to="/landing" replace />} />
          <Route path="/landing" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignUpPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/payment-status" element={<PaymentStatusPage />} />

          {/* Protected Admin Routes */}
          <Route element={<PrivateRoute />}>
            <Route
                path="/admin"
                element={
                    <SidebarProvider>
                        <div className="min-h-screen flex w-full bg-gray-50">
                            <AdminLayout />
                        </div>
                    </SidebarProvider>
                }
            >
                <Route index element={<AdminDashboard />} />
                <Route path="users" element={<Users />} />
                <Route path="ai-models" element={<AIModels />} />
                <Route path="usage-analytics" element={<AdminUsageAnalytics />} />
                <Route path="billing" element={<AdminBilling />} />
                <Route path="discounts" element={<Discounts />} />
            </Route>
          </Route>

            {/* Protected User Routes */}
            <Route element={<PrivateRoute />}>
                <Route path="/app" element={<UserLayout />}>
                    <Route index element={<UserDashboard />} />
                    <Route path="billing" element={<UserBillingPage />} />
                    <Route path="usage" element={<UserUsagePage />} />
                    <Route path="profile" element={<ProfileSettingsPage />} />
                    <Route path="discounts" element={<UserDiscountsPage />} /> {/* NEW: Add discount route */}
                </Route>
            </Route>

          {/* Catch-all for Not Found */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;