import { useState, useEffect, useMemo } from "react";
import apiClient from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, Filter, Loader2, Edit, Eye, Key, BarChart3, AlertCircle } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

// Enhanced User interface to match new backend model
interface User {
  id: number;
  auth_id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string | null;
  organization_name: string | null;
  subscription_tier_id: number | null;
  monthly_request_limit: number | null;
  monthly_token_limit: number | null;
  monthly_cost_limit: number | null;
}

interface UserDetailed extends User {
  total_assigned_models: number;
  active_assignments: number;
  total_api_keys: number;
  active_api_keys: number;
  total_usage_cost: number;
  model_assignments: ModelAssignment[];
  api_keys: APIKey[];
}

interface ModelAssignment {
  assignment_id: number;
  model_id: number;
  model_name: string;
  access_level: string;
  is_active: boolean;
  total_requests: number;
  total_cost: number;
  last_used_at: string | null;
}

interface APIKey {
  id: number;
  key_name: string;
  api_key_prefix: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

interface Tier {
  id: number;
  name: string;
}

interface AIModel {
  id: number;
  name: string;
  provider: string;
  status: string;
  total_assignments: number;
  total_revenue: number;
}

interface UserStats {
  total_users: number;
  active_users: number;
  users_with_models: number;
  users_with_api_keys: number;
  total_model_assignments: number;
}

const Users = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [tiers, setTiers] = useState<Tier[]>([]);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterHasModels, setFilterHasModels] = useState<string>("all");
  
  // Dialog states
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<Partial<User>>({});
  const [selectedUserDetails, setSelectedUserDetails] = useState<UserDetailed | null>(null);
  
  // Model assignment states
  const [availableModels, setAvailableModels] = useState<AIModel[]>([]);
  const [selectedAssignments, setSelectedAssignments] = useState<{
    [modelId: number]: {
      assigned: boolean;
      access_level: string;
      daily_request_limit?: number;
      monthly_request_limit?: number;
    }
  }>({});
  
  const { toast } = useToast();

  const fetchInitialData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [usersResponse, tiersResponse, statsResponse] = await Promise.all([
        apiClient.get("/admin/users?limit=1000"),
        apiClient.get("/admin/subscription-tiers"),
        apiClient.get("/admin/users/stats"),
      ]);
      setUsers(usersResponse.data);
      setTiers(tiersResponse.data);
      setUserStats(statsResponse.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setIsLoading(false);
    }
  };

  const loadAvailableModels = async () => {
    try {
      const response = await apiClient.get("/admin/models?include_usage_stats=true");
      setAvailableModels(response.data.filter((m: AIModel) => m.status === 'active'));
    } catch (error) {
      console.error("Failed to load models:", error);
      toast({
        title: "Failed to load models",
        description: "Could not load available AI models",
        variant: "destructive",
      });
    }
  };

  const loadUserAssignments = async (userId: number) => {
    try {
      const response = await apiClient.get(`/admin/users/${userId}/model-assignments`);
      const assignments = response.data.assignments || [];
      
      // Convert assignments to the selection format
      const assignmentMap: typeof selectedAssignments = {};
      assignments.forEach((assignment: any) => {
        assignmentMap[assignment.model_id] = {
          assigned: assignment.is_active,
          access_level: assignment.access_level || 'read_write',
          daily_request_limit: assignment.daily_request_limit,
          monthly_request_limit: assignment.monthly_request_limit,
        };
      });
      
      setSelectedAssignments(assignmentMap);
    } catch (error) {
      console.error("Failed to load user assignments:", error);
      setSelectedAssignments({});
    }
  };

  const loadUserDetails = async (userId: number) => {
    try {
      const response = await apiClient.get(`/admin/users/${userId}`);
      setSelectedUserDetails(response.data);
    } catch (error) {
      console.error("Failed to load user details:", error);
      toast({
        title: "Failed to load user details",
        description: "Could not load detailed user information",
        variant: "destructive",
      });
    }
  };

  const handleAssignmentToggle = (modelId: number, assigned: boolean) => {
    setSelectedAssignments(prev => ({
      ...prev,
      [modelId]: {
        ...prev[modelId],
        assigned,
        access_level: prev[modelId]?.access_level || 'read_write',
      }
    }));
  };

  const handleAssignmentUpdate = (modelId: number, field: string, value: any) => {
    setSelectedAssignments(prev => ({
      ...prev,
      [modelId]: {
        ...prev[modelId],
        assigned: prev[modelId]?.assigned || false,
        [field]: value,
      }
    }));
  };

  const handleUpdateUser = async () => {
    if (!currentUser.id) return;

    try {
      // Update user details
      const userPayload = {
        ...currentUser,
        monthly_request_limit: Number(currentUser.monthly_request_limit) || null,
        monthly_token_limit: Number(currentUser.monthly_token_limit) || null,
        monthly_cost_limit: Number(currentUser.monthly_cost_limit) || null,
      };

      await apiClient.put(`/admin/users/${currentUser.id}`, userPayload);

      // Update model assignments
      const assignedModels = Object.entries(selectedAssignments)
        .filter(([_, assignment]) => assignment.assigned)
        .map(([modelId, assignment]) => ({
          user_id: currentUser.id,
          model_id: parseInt(modelId),
          access_level: assignment.access_level,
          daily_request_limit: assignment.daily_request_limit,
          monthly_request_limit: assignment.monthly_request_limit,
        }));

      // First, get existing assignments to deactivate
      const existingResponse = await apiClient.get(`/admin/users/${currentUser.id}/model-assignments`);
      const existingAssignments = existingResponse.data.assignments || [];

      // Deactivate assignments not in the new selection
      for (const existing of existingAssignments) {
        const isStillSelected = Object.entries(selectedAssignments).some(
          ([modelId, assignment]) => 
            parseInt(modelId) === existing.model_id && assignment.assigned
        );
        
        if (existing.is_active && !isStillSelected) {
          await apiClient.put(`/admin/model-assignments/${existing.assignment_id}`, {
            is_active: false
          });
        }
      }

      // Create new assignments
      for (const assignment of assignedModels) {
        const existingAssignment = existingAssignments.find(
          (existing: any) => existing.model_id === assignment.model_id
        );

        if (existingAssignment) {
          // Update existing assignment
          await apiClient.put(`/admin/model-assignments/${existingAssignment.assignment_id}`, {
            is_active: true,
            access_level: assignment.access_level,
            daily_request_limit: assignment.daily_request_limit,
            monthly_request_limit: assignment.monthly_request_limit,
          });
        } else {
          // Create new assignment
          await apiClient.post("/admin/model-assignments", assignment);
        }
      }

      toast({ title: "User updated successfully!" });
      setIsEditDialogOpen(false);
      fetchInitialData();
    } catch (e: any) {
      toast({
        title: "Update failed",
        description: e.response?.data?.detail || "Could not update user.",
        variant: "destructive",
      });
    }
  };

  const handleDeactivateAPIKeys = async (userId: number) => {
    try {
      await apiClient.post(`/admin/users/${userId}/deactivate-api-keys`);
      toast({ title: "API keys deactivated successfully!" });
      if (selectedUserDetails?.id === userId) {
        loadUserDetails(userId);
      }
    } catch (e: any) {
      toast({
        title: "Failed to deactivate API keys",
        description: e.response?.data?.detail || "Could not deactivate API keys.",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, []);

  const openEditDialog = async (user: User) => {
    setCurrentUser({ ...user });
    setIsEditDialogOpen(true);
    await loadAvailableModels();
    await loadUserAssignments(user.id);
  };

  const openDetailDialog = async (user: User) => {
    setIsDetailDialogOpen(true);
    await loadUserDetails(user.id);
  };

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value } = e.target;
    setCurrentUser((prev) => ({ ...prev, [id]: value }));
  };

  const handleSelectChange = (id: string, value: string) => {
    const isNumber = id.includes('_id');
    setCurrentUser((prev) => ({
      ...prev,
      [id]: isNumber ? parseInt(value, 10) : value,
    }));
  };

  const tierMap = useMemo(() => {
    return new Map(tiers.map((tier) => [tier.id, tier.name]));
  }, [tiers]);

  const filteredUsers = useMemo(() => {
    return users.filter((user) => {
      const matchesSearch = 
        (user.full_name?.toLowerCase() || "").includes(searchTerm.toLowerCase()) ||
        (user.email?.toLowerCase() || "").includes(searchTerm.toLowerCase()) ||
        (user.organization_name?.toLowerCase() || "").includes(searchTerm.toLowerCase());

      const matchesStatus = 
        filterStatus === "all" || 
        (filterStatus === "active" && user.is_active) ||
        (filterStatus === "inactive" && !user.is_active);

      // Note: For has_models filter, we'd need to fetch this data or include it in the user object
      // For now, we'll skip this filter
      const matchesModels = filterHasModels === "all";

      return matchesSearch && matchesStatus && matchesModels;
    });
  }, [users, searchTerm, filterStatus, filterHasModels]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
        <span className="ml-4 text-lg text-gray-600">Loading Users...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-600 bg-red-50 p-4 rounded-md">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Users</h1>
        <p className="text-gray-600 mt-2">
          Manage user accounts, subscriptions, model assignments, and limits.
        </p>
      </div>

      {/* Statistics Cards */}
      {userStats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Users</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{userStats.total_users}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Users</CardTitle>
              <Badge variant="default" className="bg-green-100 text-green-800">
                {userStats.active_users}
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{userStats.active_users}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">With Models</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{userStats.users_with_models}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">With API Keys</CardTitle>
              <Key className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{userStats.users_with_api_keys}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Assignments</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{userStats.total_model_assignments}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Edit User Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-[900px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit User: {currentUser.full_name}</DialogTitle>
            <DialogDescription>
              Update user profile, limits, and AI model assignments.
            </DialogDescription>
          </DialogHeader>
          
          <Tabs defaultValue="profile" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="profile">Profile & Limits</TabsTrigger>
              <TabsTrigger value="models">AI Model Access</TabsTrigger>
            </TabsList>

            <TabsContent value="profile" className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="full_name">Full Name</Label>
                  <Input 
                    id="full_name" 
                    value={currentUser.full_name || ""} 
                    onChange={handleFormChange} 
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="organization_name">Organization Name</Label>
                  <Input 
                    id="organization_name" 
                    value={currentUser.organization_name || ""} 
                    onChange={handleFormChange} 
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="subscription_tier_id">Subscription Tier</Label>
                  <Select 
                    onValueChange={(v) => handleSelectChange('subscription_tier_id', v)} 
                    value={String(currentUser.subscription_tier_id || '')}
                  >
                    <SelectTrigger><SelectValue placeholder="Select tier" /></SelectTrigger>
                    <SelectContent>
                      {tiers.map((tier) => (
                        <SelectItem key={tier.id} value={String(tier.id)}>
                          {tier.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="is_active">Status</Label>
                  <Select 
                    onValueChange={(v) => setCurrentUser(p => ({...p, is_active: v === 'true'}))} 
                    value={String(currentUser.is_active)}
                  >
                    <SelectTrigger><SelectValue/></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="true">Active</SelectItem>
                      <SelectItem value="false">Inactive</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="monthly_request_limit">Request Limit</Label>
                  <Input 
                    id="monthly_request_limit" 
                    type="number" 
                    value={currentUser.monthly_request_limit ?? ""} 
                    onChange={handleFormChange} 
                    placeholder="10000" 
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="monthly_token_limit">Token Limit</Label>
                  <Input 
                    id="monthly_token_limit" 
                    type="number" 
                    value={currentUser.monthly_token_limit ?? ""} 
                    onChange={handleFormChange} 
                    placeholder="500000" 
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="monthly_cost_limit">Cost Limit ($)</Label>
                  <Input 
                    id="monthly_cost_limit" 
                    type="number" 
                    value={currentUser.monthly_cost_limit ?? ""} 
                    onChange={handleFormChange} 
                    placeholder="200" 
                  />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="models" className="space-y-4">
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold">AI Model Access & Permissions</h3>
                  <p className="text-sm text-gray-600">
                    Configure which AI models this user can access and their permission levels.
                  </p>
                </div>
                
                <div className="space-y-3 max-h-96 overflow-y-auto border rounded-lg p-4">
                  {availableModels.map(model => {
                    const assignment = selectedAssignments[model.id] || { assigned: false, access_level: 'read_write' };
                    
                    return (
                      <div key={model.id} className="border rounded-lg p-4 space-y-3">
                        <div className="flex items-center space-x-3">
                          <Checkbox
                            id={`model-${model.id}`}
                            checked={assignment.assigned}
                            onCheckedChange={(checked) => 
                              handleAssignmentToggle(model.id, checked as boolean)
                            }
                          />
                          <div className="flex-1">
                            <label 
                              htmlFor={`model-${model.id}`}
                              className="cursor-pointer font-medium"
                            >
                              {model.name}
                            </label>
                            <div className="text-sm text-gray-500">
                              {model.provider} • {model.total_assignments} assignments • ${model.total_revenue} revenue
                            </div>
                          </div>
                        </div>
                        
                        {assignment.assigned && (
                          <div className="ml-6 grid grid-cols-3 gap-3">
                            <div className="space-y-1">
                              <Label className="text-xs">Access Level</Label>
                              <Select 
                                value={assignment.access_level}
                                onValueChange={(v) => handleAssignmentUpdate(model.id, 'access_level', v)}
                              >
                                <SelectTrigger className="h-8">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="read_only">Read Only</SelectItem>
                                  <SelectItem value="read_write">Read Write</SelectItem>
                                  <SelectItem value="admin">Admin</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs">Daily Limit</Label>
                              <Input 
                                type="number" 
                                placeholder="1000"
                                className="h-8"
                                value={assignment.daily_request_limit || ''}
                                onChange={(e) => handleAssignmentUpdate(
                                  model.id, 
                                  'daily_request_limit', 
                                  e.target.value ? parseInt(e.target.value) : undefined
                                )}
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs">Monthly Limit</Label>
                              <Input 
                                type="number" 
                                placeholder="10000"
                                className="h-8"
                                value={assignment.monthly_request_limit || ''}
                                onChange={(e) => handleAssignmentUpdate(
                                  model.id, 
                                  'monthly_request_limit', 
                                  e.target.value ? parseInt(e.target.value) : undefined
                                )}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                
                <div className="text-sm text-blue-600 bg-blue-50 p-2 rounded">
                  {Object.values(selectedAssignments).filter(a => a.assigned).length} model(s) assigned
                </div>
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleUpdateUser}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* User Details Dialog */}
      <Dialog open={isDetailDialogOpen} onOpenChange={setIsDetailDialogOpen}>
        <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>User Details: {selectedUserDetails?.full_name}</DialogTitle>
            <DialogDescription>
              Comprehensive view of user activity, assignments, and API keys.
            </DialogDescription>
          </DialogHeader>
          
          {selectedUserDetails && (
            <Tabs defaultValue="overview" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="models">Model Assignments</TabsTrigger>
                <TabsTrigger value="keys">API Keys</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Card>
                    <CardContent className="pt-6">
                      <div className="text-2xl font-bold">{selectedUserDetails.total_assigned_models}</div>
                      <p className="text-xs text-muted-foreground">Total Model Assignments</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <div className="text-2xl font-bold">${selectedUserDetails.total_usage_cost}</div>
                      <p className="text-xs text-muted-foreground">Total Usage Cost</p>
                    </CardContent>
                  </Card>
                </div>
                
                <div className="space-y-2">
                  <Label>User Information</Label>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>Email: {selectedUserDetails.email}</div>
                    <div>Organization: {selectedUserDetails.organization_name || 'Not set'}</div>
                    <div>Created: {new Date(selectedUserDetails.created_at || '').toLocaleDateString()}</div>
                    <div>Status: {selectedUserDetails.is_active ? 'Active' : 'Inactive'}</div>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="models" className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold">Model Assignments</h3>
                  <Badge variant="outline">
                    {selectedUserDetails.active_assignments} active
                  </Badge>
                </div>
                
                <div className="space-y-2">
                  {selectedUserDetails.model_assignments.map((assignment) => (
                    <Card key={assignment.assignment_id}>
                      <CardContent className="pt-4">
                        <div className="flex justify-between items-center">
                          <div>
                            <div className="font-medium">{assignment.model_name}</div>
                            <div className="text-sm text-gray-500">
                              {assignment.access_level} • {assignment.total_requests} requests • ${assignment.total_cost}
                            </div>
                          </div>
                          <Badge variant={assignment.is_active ? "default" : "secondary"}>
                            {assignment.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="keys" className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold">API Keys</h3>
                  <div className="flex gap-2">
                    <Badge variant="outline">{selectedUserDetails.active_api_keys} active</Badge>
                    <Button 
                      variant="destructive" 
                      size="sm"
                      onClick={() => handleDeactivateAPIKeys(selectedUserDetails.id)}
                    >
                      <AlertCircle className="h-4 w-4 mr-2" />
                      Deactivate All
                    </Button>
                  </div>
                </div>
                
                <div className="space-y-2">
                  {selectedUserDetails.api_keys.map((apiKey) => (
                    <Card key={apiKey.id}>
                      <CardContent className="pt-4">
                        <div className="flex justify-between items-center">
                          <div>
                            <div className="font-medium">{apiKey.key_name}</div>
                            <div className="text-sm text-gray-500 font-mono">
                              {apiKey.api_key_prefix}
                            </div>
                            <div className="text-xs text-gray-400">
                              Created: {new Date(apiKey.created_at).toLocaleDateString()}
                              {apiKey.last_used_at && (
                                <> • Last used: {new Date(apiKey.last_used_at).toLocaleDateString()}</>
                              )}
                            </div>
                          </div>
                          <Badge variant={apiKey.is_active ? "default" : "secondary"}>
                            {apiKey.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>
            </Tabs>
          )}

          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Close</Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Main Users Table */}
      <Card className="border border-gray-200">
        <CardHeader>
          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center space-y-4 lg:space-y-0">
            <CardTitle>All Users ({filteredUsers.length})</CardTitle>
            <div className="flex flex-wrap gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Search users..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 w-64"
                />
              </div>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Organization</TableHead>
                  <TableHead>Subscription Tier</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium text-gray-900">
                          {user.full_name}
                        </div>
                        <div className="text-sm text-gray-500">
                          {user.email}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-gray-900">
                        {user.organization_name || (
                          <span className="text-gray-400">Not Set</span>
                        )}
                      </span>
                    </TableCell>
                    <TableCell>
                      {user.subscription_tier_id ? (
                        tierMap.get(user.subscription_tier_id)
                      ) : (
                        <span className="text-gray-400">No Tier</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={user.is_active ? "default" : "secondary"}
                        className={
                          user.is_active
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-800"
                        }
                      >
                        {user.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-gray-500">
                        {user.created_at 
                          ? new Date(user.created_at).toLocaleDateString()
                          : 'Unknown'
                        }
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={() => openDetailDialog(user)}
                        >
                          <Eye className="h-4 w-4 mr-2" />
                          View
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={() => openEditDialog(user)}
                        >
                          <Edit className="h-4 w-4 mr-2" />
                          Edit
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Users;