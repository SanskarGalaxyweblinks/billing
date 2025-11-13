import { useEffect, useState } from "react";
import apiClient from "@/lib/api"; 
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Users,
  Settings,
  Activity,
  DollarSign,
  TrendingUp,
  ReceiptText,
  Clock,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface UnpaidBill {
  id: number;
  organization: string;
  year: number;
  month: number;
  total_requests: number;
  total_tokens: number;
  usage_cost: number;
  subscription_cost: number;
  total_cost: number;
  status: "unpaid";
  bill_id: string | null;
  generated_date: string;
}

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [unpaidBills, setUnpaidBills] = useState<UnpaidBill[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [summaryRes, billsRes] = await Promise.all([
          apiClient.get("/admin/dashboard-summary"),
          apiClient.get("/admin/billing/overview/unpaid"),
        ]);

        setDashboardData(summaryRes.data);
        setUnpaidBills(billsRes.data);
      } catch (err: any) {
        console.error("Failed to fetch dashboard data:", err);
        const errorMessage = err.response?.data?.detail || err.message || "An unknown error occurred.";
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (loading)
    return (
      <div className="flex justify-center items-center min-h-screen">
        <p>Loading dashboard...</p>
      </div>
    );
  if (error)
    return (
      <div className="flex justify-center items-center min-h-screen text-red-600">
        <p>Error: {error}</p>
      </div>
    );
  if (!dashboardData || !unpaidBills)
    return (
      <div className="flex justify-center items-center min-h-screen">
        <p>No data available.</p>
      </div>
    );

  const { stats, top_organizations } = dashboardData;

  const statCards = [
    {
      title: "Total Users",
      value: stats.total_users,
      icon: Users,
      color: "text-blue-600",
      bgColor: "bg-blue-50",
      change: "+0%",
    },
    // REMOVED Total Organizations card
    {
      title: "Active Models",
      value: stats.active_models,
      icon: Settings,
      color: "text-purple-600",
      bgColor: "bg-purple-50",
      change: "+0%",
    },
    {
      title: "Requests This Month",
      value: stats.requests_this_month,
      icon: Activity,
      color: "text-orange-600",
      bgColor: "bg-orange-50",
      change: "+0%",
    },
    {
      title: "Revenue This Month",
      value: `$${stats.revenue_this_month.toFixed(3)}`,
      icon: DollarSign,
      color: "text-emerald-600",
      bgColor: "bg-emerald-50",
      change: "+0%",
    },
    {
      title: "Tokens This Month",
      value: `${(stats.tokens_this_month / 1000000).toFixed(2)}M`,
      icon: TrendingUp,
      color: "text-cyan-600",
      bgColor: "bg-cyan-50",
      change: "+0%",
    },
  ];

  return (
    <div className="p-4 space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">
          Overview of your Jupiter Billing platform
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {statCards.map((stat, index) => (
          <Card
            key={index}
            className="border border-gray-200 hover:shadow-md transition-shadow"
          >
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">
                {stat.title}
              </CardTitle>
              <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-900">
                {stat.value}
              </div>
              <div className="flex items-center space-x-1 text-sm">
                <span className="text-green-600 font-medium">
                  {stat.change}
                </span>
                <span className="text-gray-500">from last month</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border border-gray-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ReceiptText className="h-5 w-5 text-red-500" />
              Unpaid Bills
              {unpaidBills.length > 0 && (
                <Badge variant="destructive" className="ml-2">
                  {unpaidBills.length}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {unpaidBills.length === 0 ? (
                <p className="text-gray-500 text-sm">No unpaid bills found.</p>
              ) : (
                unpaidBills.map((bill) => (
                  <div
                    key={bill.id}
                    className="flex flex-col sm:flex-row items-start sm:items-center justify-between py-2 border-b border-gray-100 last:border-0"
                  >
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">
                        {bill.organization}
                      </p>
                      <p className="text-sm text-gray-500 flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Bill for {bill.month}/{bill.year}
                      </p>
                    </div>
                    <div className="flex flex-col sm:items-end mt-2 sm:mt-0">
                      <span className="font-semibold text-lg text-red-600">
                        ${bill.total_cost.toFixed(2)}
                      </span>
                      <span className="text-xs text-gray-500">
                        Generated: {bill.generated_date}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border border-gray-200">
          <CardHeader>
            <CardTitle>Top Organizations by Usage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {top_organizations.length === 0 ? (
                <p className="text-gray-500 text-sm">No usage data.</p>
              ) : (
                top_organizations.map((org: any, index: number) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-2"
                  >
                    <div>
                      <p className="font-medium text-gray-900">
                        {org.organization_name}
                      </p>
                      <p className="text-sm text-gray-500">
                        {org.total_requests} requests
                      </p>
                    </div>
                    <span className="font-semibold text-gray-900">
                      ${org.total_cost.toFixed(3)}
                    </span>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;