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
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Search,
  Filter,
  Loader2,
  Plus,
  Edit,
  Trash2,
  User,
  Bot,
  Calendar,
  DollarSign,
  Activity,
  AlertTriangle,
} from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

interface User {
  id: number;
  email: string;
  full_name: string;
  organization_name: string;
  is_active: boolean;
}

interface AIModel {
  id: number;
  name: string;
  provider: string;
  status: string;
  cost_calculation_type: string;
  request_cost: number;
  input_cost_per_1k_tokens: number;
  total_assignments: number;
  total_revenue: number;
}

interface ModelAssignment {
  id: number;
  user_id: number;
  model_id: number;
  access_level: string;
  is_active: boolean;
  assigned_at: string;
  expires_at: string | null;
  last_used_at: string | null;
  daily_request_limit: number | null;
  monthly_request_limit: number | null;
  daily_token_limit: number | null;
  monthly_token_limit: number | null;
  total_requests_made: number;
  total_tokens_used: number;
  total_cost_incurred: number;
  
  // Related data
  user_email: string;
  user_organization: string;
  model_name: string;
  model_provider: string;
}

interface AssignmentStats {
  total_assignments: number;
  active_assignments: number;
  total_users: number;
  total_models: number;
  total_cost: number;
  assignments_today: number;
}

interface CreateAssignmentRequest {
  user_id: number;
  model_id: number;
  access_level: string;
  daily_request_limit?: number;
  monthly_request_limit?: number;
  daily_token_limit?: number;
  monthly_token_limit?: number;
  expires_at?: string;
}

const ModelAssignment = () => {
  const [assignments, setAssignments] = useState<ModelAssignment[]>([]);
  const [stats, setStats] = useState<AssignmentStats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [models, setModels] = useState<AIModel[]>([]);
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterModel, setFilterModel] = useState<string>("all");
  
  // Dialog states
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [currentAssignment, setCurrentAssignment] = useState<Partial<ModelAssignment>>({});
  const [newAssignment, setNewAssignment] = useState<CreateAssignmentRequest>({
    user_id: 0,
    model_id: 0,
    access_level: 'read_write',
  });
  
  const { toast } = useToast();

  const fetchAssignments = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.get("/admin/model-assignments?include_details=true");
      setAssignments(response.data.assignments || []);
      setStats(response.data.stats || null);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await apiClient.get("/admin/users?is_active=true&limit=1000");
      setUsers(response.data);
    } catch (error) {
      console.error("Failed to load users:", error);
    }
  };

  const fetchModels = async () => {
    try {
      const response = await apiClient.get("/admin/models?status=active");
      setModels(response.data);
    } catch (error) {
      console.error("Failed to load models:", error);
    }
  };

  const handleCreateAssignment = async () => {
    if (!newAssignment.user_id || !newAssignment.model_id) {
      toast({
        title: "Validation Error",
        description: "Please select both a user and a model.",
        variant: "destructive",
      });
      return;
    }

    try {
      await apiClient.post("/admin/model-assignments", newAssignment);
      toast({ title: "Assignment created successfully!" });
      setIsCreateDialogOpen(false);
      setNewAssignment({
        user_id: 0,
        model_id: 0,
        access_level: 'read_write',
      });
      fetchAssignments();
    } catch (e: any) {
      toast({
        title: "Failed to create assignment",
        description: e.response?.data?.detail || "Could not create assignment.",
        variant: "destructive",
      });
    }
  };

  const handleUpdateAssignment = async () => {
    if (!currentAssignment.id) return;

    try {
      const updateData = {
        access_level: currentAssignment.access_level,
        is_active: currentAssignment.is_active,
        daily_request_limit: currentAssignment.daily_request_limit,
        monthly_request_limit: currentAssignment.monthly_request_limit,
        daily_token_limit: currentAssignment.daily_token_limit,
        monthly_token_limit: currentAssignment.monthly_token_limit,
        expires_at: currentAssignment.expires_at,
      };

      await apiClient.put(`/admin/model-assignments/${currentAssignment.id}`, updateData);
      toast({ title: "Assignment updated successfully!" });
      setIsEditDialogOpen(false);
      fetchAssignments();
    } catch (e: any) {
      toast({
        title: "Failed to update assignment",
        description: e.response?.data?.detail || "Could not update assignment.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteAssignment = async (assignmentId: number) => {
    if (!confirm("Are you sure you want to delete this assignment?")) return;

    try {
      await apiClient.delete(`/admin/model-assignments/${assignmentId}`);
      toast({ title: "Assignment deleted successfully!" });
      fetchAssignments();
    } catch (e: any) {
      toast({
        title: "Failed to delete assignment",
        description: e.response?.data?.detail || "Could not delete assignment.",
        variant: "destructive",
      });
    }
  };

  const handleBulkAction = async (action: string, selectedIds: number[]) => {
    if (selectedIds.length === 0) {
      toast({
        title: "No assignments selected",
        description: "Please select assignments to perform bulk actions.",
        variant: "destructive",
      });
      return;
    }

    try {
      const payload = {
        assignment_ids: selectedIds,
        action: action,
      };

      await apiClient.post("/admin/model-assignments/bulk-action", payload);
      toast({ title: `Bulk ${action} completed successfully!` });
      fetchAssignments();
    } catch (e: any) {
      toast({
        title: `Bulk ${action} failed`,
        description: e.response?.data?.detail || "Could not perform bulk action.",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    fetchAssignments();
    fetchUsers();
    fetchModels();
  }, []);

  const openEditDialog = (assignment: ModelAssignment) => {
    setCurrentAssignment({ ...assignment });
    setIsEditDialogOpen(true);
  };

  const filteredAssignments = useMemo(() => {
    return assignments.filter((assignment) => {
      const matchesSearch = 
        assignment.user_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        assignment.user_organization.toLowerCase().includes(searchTerm.toLowerCase()) ||
        assignment.model_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        assignment.model_provider.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesStatus = 
        filterStatus === "all" || 
        (filterStatus === "active" && assignment.is_active) ||
        (filterStatus === "inactive" && !assignment.is_active) ||
        (filterStatus === "expired" && assignment.expires_at && new Date(assignment.expires_at) < new Date());

      const matchesModel = 
        filterModel === "all" || 
        assignment.model_id.toString() === filterModel;

      return matchesSearch && matchesStatus && matchesModel;
    });
  }, [assignments, searchTerm, filterStatus, filterModel]);

  const getStatusBadge = (assignment: ModelAssignment) => {
    if (!assignment.is_active) {
      return <Badge variant="secondary">Inactive</Badge>;
    }
    
    if (assignment.expires_at && new Date(assignment.expires_at) < new Date()) {
      return <Badge variant="destructive">Expired</Badge>;
    }
    
    if (assignment.expires_at && new Date(assignment.expires_at) < new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)) {
      return <Badge variant="outline" className="border-orange-500 text-orange-600">Expiring Soon</Badge>;
    }
    
    return <Badge variant="default" className="bg-green-100 text-green-800">Active</Badge>;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
        <span className="ml-4 text-lg text-gray-600">Loading Assignments...</span>
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
        <h1 className="text-3xl font-bold text-gray-900">Model Assignments</h1>
        <p className="text-gray-600 mt-2">
          Manage user access to AI models with permissions and usage limits.
        </p>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Assignments</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_assignments}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{stats.active_assignments}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Users</CardTitle>
              <User className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_users}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Models</CardTitle>
              <Bot className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_models}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${stats.total_cost.toFixed(2)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Today</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.assignments_today}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Create Assignment Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Create Model Assignment</DialogTitle>
            <DialogDescription>
              Assign an AI model to a user with specific permissions and limits.
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>User</Label>
                <Select 
                  value={newAssignment.user_id.toString()} 
                  onValueChange={(v) => setNewAssignment(prev => ({...prev, user_id: parseInt(v)}))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select user" />
                  </SelectTrigger>
                  <SelectContent>
                    {users.map((user) => (
                      <SelectItem key={user.id} value={user.id.toString()}>
                        {user.full_name} ({user.email})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>AI Model</Label>
                <Select 
                  value={newAssignment.model_id.toString()} 
                  onValueChange={(v) => setNewAssignment(prev => ({...prev, model_id: parseInt(v)}))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select model" />
                  </SelectTrigger>
                  <SelectContent>
                    {models.map((model) => (
                      <SelectItem key={model.id} value={model.id.toString()}>
                        {model.name} ({model.provider})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Access Level</Label>
              <Select 
                value={newAssignment.access_level} 
                onValueChange={(v) => setNewAssignment(prev => ({...prev, access_level: v}))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="read_only">Read Only</SelectItem>
                  <SelectItem value="read_write">Read Write</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Separator />

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Daily Request Limit</Label>
                <Input 
                  type="number" 
                  placeholder="1000"
                  value={newAssignment.daily_request_limit || ''}
                  onChange={(e) => setNewAssignment(prev => ({
                    ...prev, 
                    daily_request_limit: e.target.value ? parseInt(e.target.value) : undefined
                  }))}
                />
              </div>
              <div className="space-y-2">
                <Label>Monthly Request Limit</Label>
                <Input 
                  type="number" 
                  placeholder="30000"
                  value={newAssignment.monthly_request_limit || ''}
                  onChange={(e) => setNewAssignment(prev => ({
                    ...prev, 
                    monthly_request_limit: e.target.value ? parseInt(e.target.value) : undefined
                  }))}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Expiry Date (Optional)</Label>
              <Input 
                type="date"
                value={newAssignment.expires_at || ''}
                onChange={(e) => setNewAssignment(prev => ({
                  ...prev, 
                  expires_at: e.target.value || undefined
                }))}
              />
            </div>
          </div>

          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleCreateAssignment}>Create Assignment</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Assignment Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Edit Assignment</DialogTitle>
            <DialogDescription>
              Update assignment permissions and limits.
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>User</Label>
                <Input value={currentAssignment.user_email || ''} disabled />
              </div>
              <div className="space-y-2">
                <Label>Model</Label>
                <Input value={`${currentAssignment.model_name} (${currentAssignment.model_provider})` || ''} disabled />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Access Level</Label>
                <Select 
                  value={currentAssignment.access_level || 'read_write'} 
                  onValueChange={(v) => setCurrentAssignment(prev => ({...prev, access_level: v}))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="read_only">Read Only</SelectItem>
                    <SelectItem value="read_write">Read Write</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Status</Label>
                <Select 
                  value={currentAssignment.is_active ? "true" : "false"} 
                  onValueChange={(v) => setCurrentAssignment(prev => ({...prev, is_active: v === "true"}))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="true">Active</SelectItem>
                    <SelectItem value="false">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Separator />

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Daily Request Limit</Label>
                <Input 
                  type="number"
                  value={currentAssignment.daily_request_limit || ''}
                  onChange={(e) => setCurrentAssignment(prev => ({
                    ...prev, 
                    daily_request_limit: e.target.value ? parseInt(e.target.value) : null
                  }))}
                />
              </div>
              <div className="space-y-2">
                <Label>Monthly Request Limit</Label>
                <Input 
                  type="number"
                  value={currentAssignment.monthly_request_limit || ''}
                  onChange={(e) => setCurrentAssignment(prev => ({
                    ...prev, 
                    monthly_request_limit: e.target.value ? parseInt(e.target.value) : null
                  }))}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Expiry Date</Label>
              <Input 
                type="date"
                value={currentAssignment.expires_at?.split('T')[0] || ''}
                onChange={(e) => setCurrentAssignment(prev => ({
                  ...prev, 
                  expires_at: e.target.value ? `${e.target.value}T23:59:59Z` : null
                }))}
              />
            </div>

            <Separator />

            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <div className="font-medium">Total Requests</div>
                <div className="text-gray-500">{currentAssignment.total_requests_made || 0}</div>
              </div>
              <div>
                <div className="font-medium">Total Cost</div>
                <div className="text-gray-500">${(currentAssignment.total_cost_incurred || 0).toFixed(4)}</div>
              </div>
              <div>
                <div className="font-medium">Last Used</div>
                <div className="text-gray-500">
                  {currentAssignment.last_used_at 
                    ? new Date(currentAssignment.last_used_at).toLocaleDateString()
                    : 'Never'
                  }
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleUpdateAssignment}>Update Assignment</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Main Table */}
      <Card className="border border-gray-200">
        <CardHeader>
          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center space-y-4 lg:space-y-0">
            <CardTitle>Model Assignments ({filteredAssignments.length})</CardTitle>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => setIsCreateDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                New Assignment
              </Button>
              <div className="flex gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                  <Input
                    placeholder="Search assignments..."
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
                    <SelectItem value="expired">Expired</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={filterModel} onValueChange={setFilterModel}>
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="All Models" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Models</SelectItem>
                    {models.map((model) => (
                      <SelectItem key={model.id} value={model.id.toString()}>
                        {model.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>AI Model</TableHead>
                  <TableHead>Access Level</TableHead>
                  <TableHead>Usage</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Assigned</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAssignments.map((assignment) => (
                  <TableRow key={assignment.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{assignment.user_email}</div>
                        <div className="text-sm text-gray-500">{assignment.user_organization}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div>
                        <div className="font-medium">{assignment.model_name}</div>
                        <div className="text-sm text-gray-500">{assignment.model_provider}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{assignment.access_level.replace('_', ' ')}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <div>{assignment.total_requests_made} requests</div>
                        <div className="text-gray-500">${assignment.total_cost_incurred.toFixed(4)}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {getStatusBadge(assignment)}
                      {assignment.expires_at && (
                        <div className="text-xs text-gray-500 mt-1">
                          Expires: {new Date(assignment.expires_at).toLocaleDateString()}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="text-sm text-gray-500">
                        {new Date(assignment.assigned_at).toLocaleDateString()}
                        {assignment.last_used_at && (
                          <div>Last used: {new Date(assignment.last_used_at).toLocaleDateString()}</div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={() => openEditDialog(assignment)}
                        >
                          <Edit className="h-4 w-4 mr-2" />
                          Edit
                        </Button>
                        <Button 
                          variant="destructive" 
                          size="sm" 
                          onClick={() => handleDeleteAssignment(assignment.id)}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
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

export default ModelAssignment;