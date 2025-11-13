import { useEffect, useState, useMemo } from "react";
import apiClient from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Plus, Edit, Trash2, Loader2, Users, Settings, Calendar, Target, Bell } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

interface DiscountRule {
  id: number;
  name: string;
  description?: string;
  priority: number;
  user_id?: number;
  model_id?: number;
  min_requests: number;
  max_requests?: number;
  discount_percentage: number;
  discount_type: string;
  valid_from?: string;
  valid_until?: string;
  validity_days?: number;
  auto_apply: boolean;
  max_uses_per_user?: number;
  is_active: boolean;
  created_at?: string;
  user_name?: string;
  model_name?: string;
  enrollment_count: number;
}

interface User {
  id: number;
  full_name: string;
  organization_name: string;
}

interface AIModel {
  id: number;
  name: string;
}

interface EnrollmentStats {
  total_enrollments: number;
  active_enrollments: number;
  total_usage: number;
  users_enrolled: Array<{
    user_id: number;
    full_name: string;
    email: string;
    organization_name: string;
    enrolled_at: string;
    usage_count: number;
    is_active: boolean;
    valid_until?: string;
  }>;
}

const Discounts = () => {
  const [rules, setRules] = useState<DiscountRule[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [models, setModels] = useState<AIModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isStatsDialogOpen, setIsStatsDialogOpen] = useState(false);
  const [currentRule, setCurrentRule] = useState<Partial<DiscountRule> | null>(null);
  const [enrollmentStats, setEnrollmentStats] = useState<EnrollmentStats | null>(null);
  const { toast } = useToast();

  const userMap = useMemo(() => new Map(users.map(u => [u.id, u.full_name])), [users]);
  const modelMap = useMemo(() => new Map(models.map(m => [m.id, m.name])), [models]);

  const fetchAllData = async () => {
    setIsLoading(true);
    try {
      const [rulesRes, usersRes, modelsRes] = await Promise.all([
        apiClient.get("/admin/discounts"),
        apiClient.get("/admin/users"),
        apiClient.get("/admin/models"),
      ]);
      setRules(rulesRes.data);
      setUsers(usersRes.data);
      setModels(modelsRes.data);
    } catch (error) {
      toast({ title: "Error", description: "Failed to fetch necessary data.", variant: "destructive" });
    } finally {
      setIsLoading(false);
    }
  };

  const fetchEnrollmentStats = async (ruleId: number) => {
    try {
      const response = await apiClient.get(`/admin/discounts/${ruleId}/enrollments`);
      setEnrollmentStats(response.data);
      setIsStatsDialogOpen(true);
    } catch (error) {
      toast({ title: "Error", description: "Failed to fetch enrollment stats.", variant: "destructive" });
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  const openDialog = (rule: Partial<DiscountRule> | null = null) => {
    if (rule) {
      setCurrentRule({ 
        ...rule,
        valid_from: rule.valid_from ? new Date(rule.valid_from).toISOString().slice(0, 16) : "",
        valid_until: rule.valid_until ? new Date(rule.valid_until).toISOString().slice(0, 16) : ""
      });
    } else {
      setCurrentRule({
        is_active: true,
        priority: 100,
        min_requests: 0,
        discount_type: "percentage",
        auto_apply: false,
        valid_from: new Date().toISOString().slice(0, 16)
      });
    }
    setIsDialogOpen(true);
  };

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { id, value, type } = e.target;
    setCurrentRule(prev => ({ 
      ...prev, 
      [id]: type === 'number' ? parseFloat(value) || 0 : value 
    }));
  };
  
  const handleSelectChange = (id: string, value: string) => {
    setCurrentRule(prev => ({ 
      ...prev, 
      [id]: value === 'all' ? undefined : parseInt(value) 
    }));
  };

  const handleSubmit = async () => {
    if (!currentRule) return;

    // Prepare payload with proper date formatting
    const payload = {
      ...currentRule,
      max_requests: currentRule.max_requests || null,
      valid_from: currentRule.valid_from ? new Date(currentRule.valid_from).toISOString() : null,
      valid_until: currentRule.valid_until ? new Date(currentRule.valid_until).toISOString() : null,
    };

    try {
      if (currentRule.id) {
        await apiClient.put(`/admin/discounts/${currentRule.id}`, payload);
        toast({ title: "Success", description: "Discount rule updated." });
      } else {
        await apiClient.post("/admin/discounts", payload);
        toast({ title: "Success", description: "Discount rule created." });
      }
      setIsDialogOpen(false);
      fetchAllData();
    } catch (error: any) {
      toast({ title: "Error", description: error.response?.data?.detail || "Failed to save rule.", variant: "destructive" });
    }
  };
  
  const handleDelete = async (ruleId: number) => {
    if (window.confirm("Are you sure you want to delete this rule? This will also remove all enrollments.")) {
      try {
        await apiClient.delete(`/admin/discounts/${ruleId}`);
        toast({ title: "Success", description: "Discount rule deleted." });
        fetchAllData();
      } catch (error: any) {
        toast({ title: "Error", description: "Failed to delete rule.", variant: "destructive" });
      }
    }
  };

  const triggerNotifications = async (ruleId: number) => {
    try {
      const response = await apiClient.post(`/admin/discounts/${ruleId}/trigger-notifications`);
      toast({ title: "Success", description: response.data.message });
    } catch (error: any) {
      toast({ title: "Error", description: "Failed to trigger notifications.", variant: "destructive" });
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "No expiry";
    return new Date(dateString).toLocaleDateString();
  };

  if (isLoading) return <Loader2 className="animate-spin" />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Discount Rules</h1>
          <p className="text-gray-600 mt-1">Create and manage usage-based discount offers for users.</p>
        </div>
        <Button onClick={() => openDialog()}>
          <Plus className="mr-2 h-4 w-4" /> Add Discount Rule
        </Button>
      </div>

      <Card>
        <CardHeader><CardTitle>All Rules ({rules.length})</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Target</TableHead>
                <TableHead>Discount</TableHead>
                <TableHead>Usage Threshold</TableHead>
                <TableHead>Validity</TableHead>
                <TableHead>Enrollments</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rules.map(rule => (
                <TableRow key={rule.id}>
                  <TableCell>
                    <div>
                      <div className="font-medium">{rule.name}</div>
                      <div className="text-xs text-gray-500">Priority: {rule.priority}</div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {rule.user_id ? (
                      <Badge variant="outline">
                        <Users className="h-3 w-3 mr-1"/>
                        {rule.user_name || `User ID: ${rule.user_id}`}
                      </Badge>
                    ) : rule.model_id ? (
                      <Badge variant="outline">
                        <Settings className="h-3 w-3 mr-1"/>
                        {rule.model_name || `Model ID: ${rule.model_id}`}
                      </Badge>
                    ) : (
                      <Badge>Global</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="font-semibold text-green-600">
                      {rule.discount_percentage}% off
                    </div>
                    <div className="text-xs text-gray-500">
                      {rule.auto_apply ? "Auto-apply" : "Manual enrollment"}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      {rule.min_requests}+ requests
                    </div>
                    {rule.max_requests && (
                      <div className="text-xs text-gray-500">
                        Max: {rule.max_requests}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      {formatDate(rule.valid_until)}
                    </div>
                    {rule.validity_days && (
                      <div className="text-xs text-gray-500">
                        {rule.validity_days} days after enrollment
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => fetchEnrollmentStats(rule.id)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      {rule.enrollment_count} users
                    </Button>
                  </TableCell>
                  <TableCell>
                    <Badge variant={rule.is_active ? "default" : "secondary"}>
                      {rule.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end space-x-1">
                      <Button 
                        variant="ghost" 
                        size="icon"
                        onClick={() => triggerNotifications(rule.id)}
                        title="Trigger notifications"
                      >
                        <Bell className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => openDialog(rule)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="text-red-500" 
                        onClick={() => handleDelete(rule.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Create/Edit Discount Rule Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{currentRule?.id ? "Edit" : "Create"} Discount Rule</DialogTitle>
            <DialogDescription>
              Create usage-based discounts that will be offered to users when they reach specific milestones.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-6 py-4">
            {/* Basic Info */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Basic Information</h3>
              <div className="space-y-2">
                <Label htmlFor="name">Discount Name *</Label>
                <Input 
                  id="name" 
                  value={currentRule?.name || ""} 
                  onChange={handleFormChange}
                  placeholder="e.g., Document Classification Milestone Discount"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea 
                  id="description" 
                  value={currentRule?.description || ""} 
                  onChange={handleFormChange}
                  placeholder="Describe what this discount offers to users..."
                />
              </div>
            </div>

            <Separator />

            {/* Target Settings */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Target Settings</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="user_id">Specific User (Optional)</Label>
                  <Select 
                    value={currentRule?.user_id?.toString() || "all"} 
                    onValueChange={(v) => handleSelectChange('user_id', v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All Users" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Users</SelectItem>
                      {users.map(user => (
                        <SelectItem key={user.id} value={user.id.toString()}>
                          {user.full_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="model_id">AI Model (Optional)</Label>
                  <Select 
                    value={currentRule?.model_id?.toString() || "all"} 
                    onValueChange={(v) => handleSelectChange('model_id', v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="All Models" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Models</SelectItem>
                      {models.map(model => (
                        <SelectItem key={model.id} value={model.id.toString()}>
                          {model.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <Separator />

            {/* Usage Thresholds */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Usage Thresholds</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="min_requests">Minimum Requests *</Label>
                  <Input 
                    id="min_requests" 
                    type="number" 
                    value={currentRule?.min_requests || 0} 
                    onChange={handleFormChange}
                    placeholder="500"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="max_requests">Max Requests (Optional)</Label>
                  <Input 
                    id="max_requests" 
                    type="number" 
                    value={currentRule?.max_requests || ""} 
                    onChange={handleFormChange}
                    placeholder="1000"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="discount_percentage">Discount % *</Label>
                  <Input 
                    id="discount_percentage" 
                    type="number" 
                    value={currentRule?.discount_percentage || 0} 
                    onChange={handleFormChange}
                    placeholder="20"
                  />
                </div>
              </div>
            </div>

            <Separator />

            {/* Validity Period */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Validity Period</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="valid_from">Valid From</Label>
                  <Input 
                    id="valid_from" 
                    type="datetime-local" 
                    value={currentRule?.valid_from || ""} 
                    onChange={handleFormChange}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="valid_until">Valid Until (Optional)</Label>
                  <Input 
                    id="valid_until" 
                    type="datetime-local" 
                    value={currentRule?.valid_until || ""} 
                    onChange={handleFormChange}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="validity_days">Days Valid After Enrollment</Label>
                <Input 
                  id="validity_days" 
                  type="number" 
                  value={currentRule?.validity_days || ""} 
                  onChange={handleFormChange}
                  placeholder="30"
                />
                <p className="text-xs text-gray-500">
                  How many days the discount remains valid after user enrollment
                </p>
              </div>
            </div>

            <Separator />

            {/* Advanced Settings */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Settings</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="priority">Priority</Label>
                  <Input 
                    id="priority" 
                    type="number" 
                    value={currentRule?.priority || 100} 
                    onChange={handleFormChange}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="max_uses_per_user">Max Uses Per User</Label>
                  <Input 
                    id="max_uses_per_user" 
                    type="number" 
                    value={currentRule?.max_uses_per_user || ""} 
                    onChange={handleFormChange}
                    placeholder="Leave empty for unlimited"
                  />
                </div>
              </div>
              
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <Switch 
                    id="auto_apply" 
                    checked={currentRule?.auto_apply || false} 
                    onCheckedChange={(c) => setCurrentRule(p => ({...p, auto_apply: c}))}
                  />
                  <Label htmlFor="auto_apply">Auto-apply discount</Label>
                </div>
                <p className="text-xs text-gray-500">
                  If enabled, discount applies automatically. Otherwise, users must enroll manually.
                </p>
                
                <div className="flex items-center space-x-2">
                  <Switch 
                    id="is_active" 
                    checked={currentRule?.is_active || false} 
                    onCheckedChange={(c) => setCurrentRule(p => ({...p, is_active: c}))}
                  />
                  <Label htmlFor="is_active">Rule is Active</Label>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleSubmit}>
              {currentRule?.id ? "Update" : "Create"} Rule
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Enrollment Stats Dialog */}
      <Dialog open={isStatsDialogOpen} onOpenChange={setIsStatsDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Enrollment Statistics</DialogTitle>
            <DialogDescription>
              View users who have enrolled in this discount
            </DialogDescription>
          </DialogHeader>
          {enrollmentStats && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold">{enrollmentStats.total_enrollments}</div>
                    <div className="text-sm text-gray-500">Total Enrollments</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold">{enrollmentStats.active_enrollments}</div>
                    <div className="text-sm text-gray-500">Active Enrollments</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-2xl font-bold">{enrollmentStats.total_usage}</div>
                    <div className="text-sm text-gray-500">Total Usage</div>
                  </CardContent>
                </Card>
              </div>
              
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Organization</TableHead>
                    <TableHead>Enrolled</TableHead>
                    <TableHead>Usage Count</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {enrollmentStats.users_enrolled.map((enrollment) => (
                    <TableRow key={enrollment.user_id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{enrollment.full_name}</div>
                          <div className="text-sm text-gray-500">{enrollment.email}</div>
                        </div>
                      </TableCell>
                      <TableCell>{enrollment.organization_name || "N/A"}</TableCell>
                      <TableCell>{formatDate(enrollment.enrolled_at)}</TableCell>
                      <TableCell>{enrollment.usage_count}</TableCell>
                      <TableCell>
                        <Badge variant={enrollment.is_active ? "default" : "secondary"}>
                          {enrollment.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Close</Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Discounts;