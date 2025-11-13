import { useEffect, useState } from "react";
import apiClient from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Activity, DollarSign, Zap, AlertCircle, Settings } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

// Interface for assigned models
interface AssignedModel {
  id: number;
  name: string;
  provider: string;
  status: string;
  granted_at: string;
}

const UserDashboard = () => {
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [usageHistory, setUsageHistory] = useState<any[]>([]);
  const [assignedModels, setAssignedModels] = useState<AssignedModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null); // NEW: Track selected model
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [dashboardRes, historyRes, modelsRes] = await Promise.all([
          apiClient.get("/dashboard"),
          apiClient.get("/dashboard/usage-history?days=7"),
          apiClient.get("/users/my-models"),
        ]);
        setDashboardData(dashboardRes.data);
        setUsageHistory(historyRes.data);
        setAssignedModels(modelsRes.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to fetch dashboard data.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // NEW: Handle model selection
  const handleModelClick = (modelName: string) => {
    setSelectedModel(selectedModel === modelName ? null : modelName);
  };

  // NEW: Filter model usage data based on selection
  const filteredModelUsage = selectedModel 
    ? dashboardData?.model_wise_summary?.filter((model: any) => model.model_name === selectedModel) || []
    : dashboardData?.model_wise_summary || [];

  // NEW: Calculate filtered stats for selected model
  const getFilteredStats = () => {
    if (!selectedModel || !dashboardData) return dashboardData;
    
    const modelData = dashboardData.model_wise_summary?.find((model: any) => model.model_name === selectedModel);
    if (!modelData) return dashboardData;

    return {
      ...dashboardData,
      total_requests: modelData.total_requests,
      total_cost: modelData.total_cost,
      // Keep other stats as original since they're not model-specific
    };
  };

  const displayData = getFilteredStats();

  if (loading) return <div>Loading dashboard...</div>;
  
  if (error) return (
      <div className="flex flex-col items-center justify-center text-red-600 bg-red-50 p-6 rounded-lg">
          <AlertCircle className="h-12 w-12 mb-4" />
          <h2 className="text-xl font-semibold">Could not load dashboard data</h2>
          <p>{error}</p>
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Your Dashboard</h1>
        <p className="text-gray-600 mt-1">
          {selectedModel ? `${selectedModel} usage summary` : "Today's summary of your API usage."}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{displayData?.total_requests?.toLocaleString() || 0}</div>
            <p className="text-xs text-muted-foreground">
              {selectedModel ? `${selectedModel} only` : "Today"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${displayData?.total_cost?.toFixed(4) || "0.0000"}</div>
            <p className="text-xs text-muted-foreground">
              {selectedModel ? `${selectedModel} only` : "Today"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Avg. Response Time</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData?.avg_response_time?.toFixed(0) || 0} ms</div>
            <p className="text-xs text-muted-foreground">Today's average</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{((dashboardData?.success_rate || 0) * 100).toFixed(2)}%</div>
            <p className="text-xs text-muted-foreground">Today</p>
          </CardContent>
        </Card>
      </div>

        {/* Available Models Section with Click Functionality */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>My Available Models</CardTitle>
            <div className="flex items-center space-x-2">
              <Settings className="h-4 w-4 text-muted-foreground" />
              {selectedModel && (
                <button 
                  onClick={() => setSelectedModel(null)}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  View All
                </button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {assignedModels.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {assignedModels.map((model) => (
                  <div 
                    key={model.id} 
                    className={`flex items-center justify-between p-3 border rounded-lg cursor-pointer transition-all hover:border-blue-300 ${
                      selectedModel === model.name 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                    onClick={() => handleModelClick(model.name)}
                  >
                    <div>
                      <div className={`font-medium text-sm ${
                        selectedModel === model.name ? 'text-blue-700' : 'text-gray-900'
                      }`}>
                        {model.name}
                      </div>
                      <div className="text-xs text-gray-500">{model.provider}</div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant="outline" className="text-xs">
                        {model.status}
                      </Badge>
                      {selectedModel === model.name && (
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-gray-500">
                <Settings className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p className="text-sm">No models assigned yet</p>
                <p className="text-xs">Contact your administrator to get access to AI models</p>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
                <CardHeader>
                    <CardTitle>Usage Last 7 Days</CardTitle>
                </CardHeader>
                <CardContent>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={usageHistory}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="usage_date" />
                            <YAxis yAxisId="left" stroke="#8884d8" />
                            <YAxis yAxisId="right" orientation="right" stroke="#82ca9d" />
                            <Tooltip />
                            <Bar yAxisId="left" dataKey="total_requests" fill="#8884d8" name="Requests" />
                            <Bar yAxisId="right" dataKey="total_cost" fill="#82ca9d" name="Cost ($)" />
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
            <Card>
                <CardHeader>
                    <CardTitle>
                      {selectedModel ? `${selectedModel} Usage` : "This Month's Model Usage"}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Model</TableHead>
                                <TableHead>Requests</TableHead>
                                <TableHead>Cost</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filteredModelUsage.map((model: any, index: number) => (
                                <TableRow key={index}>
                                    <TableCell className="font-medium">{model.model_name}</TableCell>
                                    <TableCell>{model.total_requests.toLocaleString()}</TableCell>
                                    <TableCell>${model.total_cost.toFixed(5)}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    </div>
  );
};

export default UserDashboard;