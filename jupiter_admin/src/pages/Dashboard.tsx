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
  Bot,
  Key,
  AlertTriangle,
  CheckCircle,
  Loader2,
  ArrowUpRight,
  ArrowDownRight,
  BarChart3,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

interface DashboardStats {
  total_users: number;
  active_users: number;
  inactive_users: number;
  users_with_models: number;
  users_with_api_keys: number;
  total_model_assignments: number;
  active_assignments: number;
  total_models: number;
  active_models: number;
  requests_this_month: number;
  revenue_this_month: number;
  tokens_this_month: number;
  avg_response_time: number;
  success_rate: number;
  
  // Billing system health
  processed_entries_24h: number;
  unprocessed_entries_24h: number;
  processing_rate: number;
  system_health: "healthy" | "degraded" | "unhealthy";
}

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

interface TopOrganization {
  organization_name: string;
  total_requests: number;
  total_cost: number;
  active_assignments: number;
  unique_models: number;
}

interface ModelPerformance {
  model_name: string;
  provider: string;
  total_requests: number;
  total_revenue: number;
  success_rate: number;
  avg_response_time: number;
}

interface RecentActivity {
  id: number;
  type: "assignment_created" | "model_added" | "user_registered" | "billing_processed";
  description: string;
  timestamp: string;
  user_email?: string;
  model_name?: string;
}

const Dashboard = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [unpaidBills, setUnpaidBills] = useState<UnpaidBill[]>([]);
  const [topOrganizations, setTopOrganizations] = useState<TopOrganization[]>([]);
  const [modelPerformance, setModelPerformance] = useState<ModelPerformance[]>([]);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      const [
        usersStatsRes,
        billingHealthRes,
        usageSummaryRes,
        modelPerformanceRes,
        unpaidBillsRes
      ] = await Promise.all([
        apiClient.get("/admin/users/stats"),
        apiClient.get("/admin/usage-summary/billing-health"),
        apiClient.get("/admin/usage-summary?include_unprocessed=false"),
        apiClient.get("/admin/usage-summary/model-performance?days=7"),
        apiClient.get("/admin/billing/overview/unpaid").catch(() => ({ data: [] }))
      ]);

      // Combine all stats
      const combinedStats: DashboardStats = {
        ...usersStatsRes.data,
        ...billingHealthRes.data.last_24_hours,
        system_health: billingHealthRes.data.system_health,
        requests_this_month: usageSummaryRes.data.global_summary.total_requests,
        revenue_this_month: usageSummaryRes.data.global_summary.total_cost,
        tokens_this_month: usageSummaryRes.data.global_summary.total_tokens,
        avg_response_time: usageSummaryRes.data.global_summary.avg_response_time,
        success_rate: usageSummaryRes.data.global_summary.success_rate,
        total_models: usageSummaryRes.data.global_model_wise_summary.length,
        active_models: usageSummaryRes.data.global_model_wise_summary.filter((m: any) => m.model_status === 'active').length,
      };

      setStats(combinedStats);
      setTopOrganizations(usageSummaryRes.data.organization_stats.slice(0, 5));
      setModelPerformance(modelPerformanceRes.data.model_performance.slice(0, 5));
      setUnpaidBills(unpaidBillsRes.data || []);

      // Generate some mock recent activity - in real app this would come from audit logs
      setRecentActivity([
        {
          id: 1,
          type: "assignment_created",
          description: "New model assignment created",
          timestamp: new Date().toISOString(),
          user_email: "user@example.com",
          model_name: "GPT-4"
        }
      ]);

    } catch (err: any) {
      console.error("Failed to fetch dashboard data:", err);
      setError(err.response?.data?.detail || err.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  const getHealthColor = (health: string) => {
    switch (health) {
      case "healthy": return "text-green-600 bg-green-50";
      case "degraded": return "text-yellow-600 bg-yellow-50";
      case "unhealthy": return "text-red-600 bg-red-50";
      default: return "text-gray-600 bg-gray-50";
    }
  };

  const getHealthIcon = (health: string) => {
    switch (health) {
      case "healthy": return CheckCircle;
      case "degraded": return AlertTriangle;
      case "unhealthy": return AlertTriangle;
      default: return Activity;
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
        <span className="ml-4 text-lg text-gray-600">Loading dashboard...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center min-h-screen text-red-600">
        <AlertTriangle className="h-6 w-6 mr-2" />
        <p>Error: {error}</p>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <p>No data available.</p>
      </div>
    );
  }

  const userEngagementRate = stats.total_users > 0 ? (stats.users_with_models / stats.total_users * 100) : 0;
  const assignmentUtilization = stats.total_model_assignments > 0 ? (stats.active_assignments / stats.total_model_assignments * 100) : 0;

  return (
    <div className="p-4 space-y-8">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-2">
            Overview of your JupiterBrains billing platform and Epic 1 foundation
          </p>
        </div>
        <Button onClick={fetchDashboardData} variant="outline">
          <Activity className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* System Health Alert */}
      {stats.system_health !== "healthy" && (
        <Card className="border-orange-200 bg-orange-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-orange-600" />
              <div>
                <h3 className="font-medium text-orange-900">System Health Alert</h3>
                <p className="text-sm text-orange-700">
                  Billing system is currently {stats.system_health}. Processing rate: {stats.processing_rate}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_users}</div>
            <div className="flex items-center text-sm text-gray-600 mt-1">
              <span className="text-green-600 font-medium">{stats.active_users} active</span>
              <span className="mx-1">•</span>
              <span>{stats.inactive_users} inactive</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Model Assignments</CardTitle>
            <Bot className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_model_assignments}</div>
            <div className="flex items-center text-sm text-gray-600 mt-1">
              <span className="text-green-600 font-medium">{stats.active_assignments} active</span>
              <span className="mx-1">•</span>
              <span>{assignmentUtilization.toFixed(1)}% utilization</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-emerald-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${stats.revenue_this_month.toFixed(2)}</div>
            <div className="flex items-center text-sm text-gray-600 mt-1">
              <span>{stats.requests_this_month.toLocaleString()} requests</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            {(() => {
              const HealthIcon = getHealthIcon(stats.system_health);
              return <HealthIcon className={`h-4 w-4 ${getHealthColor(stats.system_health).split(' ')[0]}`} />;
            })()}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold capitalize">{stats.system_health}</div>
            <div className="text-sm text-gray-600 mt-1">
              {stats.processing_rate.toFixed(1)}% processing rate
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Engagement Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">User Engagement</CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{userEngagementRate.toFixed(1)}%</div>
            <div className="text-sm text-gray-600 mt-1">
              {stats.users_with_models} of {stats.total_users} users have model access
            </div>
            <Progress value={userEngagementRate} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Key Usage</CardTitle>
            <Key className="h-4 w-4 text-cyan-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.users_with_api_keys}</div>
            <div className="text-sm text-gray-600 mt-1">
              Users with active API keys
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <BarChart3 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(stats.success_rate * 100).toFixed(1)}%</div>
            <div className="text-sm text-gray-600 mt-1">
              API request success rate
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <Clock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avg_response_time.toFixed(0)}ms</div>
            <div className="text-sm text-gray-600 mt-1">
              Average API response time
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Organizations */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-500" />
              Top Organizations by Usage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {topOrganizations.length === 0 ? (
                <p className="text-gray-500 text-sm">No usage data available.</p>
              ) : (
                topOrganizations.map((org, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{org.organization_name}</span>
                        <Badge variant="outline" className="text-xs">
                          {org.active_assignments} models
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-500">
                        {org.total_requests.toLocaleString()} requests • {org.unique_models} unique models
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="font-semibold text-gray-900">
                        ${org.total_cost.toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Model Performance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-purple-500" />
              Top Performing Models (7 days)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {modelPerformance.length === 0 ? (
                <p className="text-gray-500 text-sm">No performance data available.</p>
              ) : (
                modelPerformance.map((model, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{model.model_name}</span>
                        <Badge variant="outline" className="text-xs">
                          {model.provider}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-500">
                        {model.total_requests.toLocaleString()} requests • {(model.success_rate * 100).toFixed(1)}% success • {model.avg_response_time.toFixed(0)}ms
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="font-semibold text-gray-900">
                        ${model.total_revenue.toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Unpaid Bills */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ReceiptText className="h-5 w-5 text-red-500" />
              Unpaid Bills
              {unpaidBills.length > 0 && (
                <Badge variant="destructive">
                  {unpaidBills.length}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {unpaidBills.length === 0 ? (
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  <span className="text-sm">All bills are paid up to date!</span>
                </div>
              ) : (
                unpaidBills.map((bill) => (
                  <div
                    key={bill.id}
                    className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
                  >
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{bill.organization}</p>
                      <p className="text-sm text-gray-500 flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Bill for {bill.month}/{bill.year} • {bill.total_requests.toLocaleString()} requests
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="font-semibold text-red-600">
                        ${bill.total_cost.toFixed(2)}
                      </span>
                      <p className="text-xs text-gray-500">
                        Due: {new Date(bill.generated_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Billing System Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-green-500" />
              Billing System Health (24h)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Processing Rate</span>
                <span className="font-medium">{stats.processing_rate.toFixed(1)}%</span>
              </div>
              <Progress value={stats.processing_rate} className="mt-2" />
              
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <p className="text-sm text-gray-600">Processed Entries</p>
                  <p className="text-lg font-semibold text-green-600">{stats.processed_entries_24h}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Pending Entries</p>
                  <p className="text-lg font-semibold text-orange-600">{stats.unprocessed_entries_24h}</p>
                </div>
              </div>
              
              <div className={`px-3 py-2 rounded-lg flex items-center gap-2 ${getHealthColor(stats.system_health)}`}>
                {(() => {
                  const HealthIcon = getHealthIcon(stats.system_health);
                  return <HealthIcon className="h-4 w-4" />;
                })()}
                <span className="font-medium capitalize">{stats.system_health}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;