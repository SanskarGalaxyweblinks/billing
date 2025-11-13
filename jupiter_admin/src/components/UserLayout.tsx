import { Outlet, Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { User, LogOut, LayoutDashboard, CreditCard, BarChart3 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import NotificationBadge from "@/components/NotificationBadge";

const UserLayout = () => {
    const navigate = useNavigate();

    const handleSignOut = () => {
        localStorage.removeItem("jwt_token");
        navigate("/login");
    };

  return (
    <div className="min-h-screen w-full flex flex-col bg-gray-50">
      <header className="h-16 border-b border-gray-200 bg-white flex items-center justify-between px-6 sticky top-0 z-10">
        <div className="flex items-center space-x-4">
            <Link to="/app" className="flex items-center space-x-2">
                 <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                    <span className="text-white font-bold text-sm">J</span>
                </div>
                <h1 className="font-semibold text-lg text-gray-900">Billing Portal</h1>
            </Link>
        </div>
        <div className="flex items-center space-x-4">
            <nav className="hidden md:flex items-center space-x-2">
                <Button variant="ghost" asChild><Link to="/app">Dashboard</Link></Button>
                <Button variant="ghost" asChild><Link to="/app/usage">Usage</Link></Button>
                <Button variant="ghost" asChild><Link to="/app/billing">Billing</Link></Button>
            </nav>
            
            {/* NEW: Notification Badge */}
            <NotificationBadge />
            
            <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="rounded-full">
                    <User className="h-5 w-5" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel>My Account</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate('/app/profile')}>Profile</DropdownMenuItem>
                
                {/* NEW: My Discounts menu item */}
                <DropdownMenuItem onClick={() => navigate('/app/discounts')}>
                    My Discounts
                </DropdownMenuItem>
                
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-red-600" onClick={handleSignOut}>
                    <LogOut className="mr-2 h-4 w-4" />
                    Sign Out
                </DropdownMenuItem>
            </DropdownMenuContent>
            </DropdownMenu>
        </div>
      </header>
      <main className="flex-1 p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  );
};

export default UserLayout;