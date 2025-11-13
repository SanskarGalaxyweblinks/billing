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
import { Search, Filter, Loader2, Edit } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

// UPDATED User interface to match new backend model
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

interface Tier {
  id: number;
  name: string;
}

// NEW: AI Model interface for model assignment
interface AIModel {
  id: number;
  name: string;
  provider: string;
  status: string;
}

const Users = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [tiers, setTiers] = useState<Tier[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<Partial<User>>({});
  
  // NEW: States for model assignment
  const [availableModels, setAvailableModels] = useState<AIModel[]>([]);
  const [assignedModelIds, setAssignedModelIds] = useState<number[]>([]);
  
  const { toast } = useToast();

  const fetchInitialData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [usersResponse, tiersResponse] = await Promise.all([
        apiClient.get("/admin/users"),
        apiClient.get("/admin/subscription-tiers"),
      ]);
      setUsers(usersResponse.data);
      setTiers(tiersResponse.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setIsLoading(false);
    }
  };

  // NEW: Load available models
  const loadAvailableModels = async () => {
    try {
      const response = await apiClient.get("/admin/models");
      setAvailableModels(response.data.filter((m: AIModel) => m.status === 'active'));
    } catch (error) {
      console.error("Failed to load models:", error);
    }
  };

  // NEW: Load user's assigned models
  const loadUserModels = async (userId: number) => {
    try {
      const response = await apiClient.get(`/admin/users/${userId}/models`);
      const modelIds = response.data.assigned_models.map((m: any) => m.id);
      setAssignedModelIds(modelIds);
    } catch (error) {
      console.error("Failed to load user models:", error);
      setAssignedModelIds([]);
    }
  };

  // NEW: Handle model toggle
  const handleModelToggle = (modelId: number, checked: boolean) => {
    if (checked) {
      setAssignedModelIds(prev => [...prev, modelId]);
    } else {
      setAssignedModelIds(prev => prev.filter(id => id !== modelId));
    }
  };

  const handleUpdateUser = async () => {
    if (!currentUser.id) return;

    try {
        const payload = {
            ...currentUser,
            monthly_request_limit: Number(currentUser.monthly_request_limit) || null,
            monthly_token_limit: Number(currentUser.monthly_token_limit) || null,
            monthly_cost_limit: Number(currentUser.monthly_cost_limit) || null,
        };

        // Update user details
        await apiClient.put(`/admin/users/${currentUser.id}`, payload);
        
        // NEW: Update model assignments
        await apiClient.post(`/admin/users/${currentUser.id}/models`, {
          user_id: currentUser.id,
          model_ids: assignedModelIds
        });
        
        toast({ title: "User updated successfully!" });
        setIsDialogOpen(false);
        fetchInitialData();
    } catch (e: any) {
        toast({
            title: "Update failed",
            description: e.response?.data?.detail || "Could not update user.",
            variant: "destructive",
        });
    }
  };


  useEffect(() => {
    fetchInitialData();
  }, []);

  const openEditDialog = (user: User) => {
    setCurrentUser({ ...user });
    setIsDialogOpen(true);
    // NEW: Load models when dialog opens
    loadAvailableModels();
    loadUserModels(user.id);
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
    return users.filter((user) =>
      (user.full_name?.toLowerCase() || "").includes(searchTerm.toLowerCase()) ||
      (user.email?.toLowerCase() || "").includes(searchTerm.toLowerCase()) ||
      (user.organization_name?.toLowerCase() || "").includes(searchTerm.toLowerCase())
    );
  }, [users, searchTerm]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
        <span className="ml-4 text-lg text-gray-600">
          Loading Users...
        </span>
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
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Users</h1>
        <p className="text-gray-600 mt-2">
          Manage user accounts, subscriptions, and limits.
        </p>
      </div>

       <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit User: {currentUser.full_name}</DialogTitle>
            <DialogDescription>Make changes to the user's profile and limits.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
             <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Label htmlFor="full_name">Full Name</Label>
                    <Input id="full_name" value={currentUser.full_name || ""} onChange={handleFormChange} />
                </div>
                <div className="space-y-2">
                    <Label htmlFor="organization_name">Organization Name</Label>
                    <Input id="organization_name" value={currentUser.organization_name || ""} onChange={handleFormChange} />
                </div>
             </div>
             <div className="grid grid-cols-2 gap-4">
                 <div className="space-y-2">
                    <Label htmlFor="subscription_tier_id">Subscription Tier</Label>
                    <Select onValueChange={(v) => handleSelectChange('subscription_tier_id', v)} value={String(currentUser.subscription_tier_id || '')}>
                        <SelectTrigger><SelectValue placeholder="Select tier" /></SelectTrigger>
                        <SelectContent>
                            {tiers.map((tier) => (
                                <SelectItem key={tier.id} value={String(tier.id)}>{tier.name}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                 </div>
                 <div className="space-y-2">
                     <Label htmlFor="is_active">Status</Label>
                     <Select onValueChange={(v) => setCurrentUser(p => ({...p, is_active: v === 'true'}))} value={String(currentUser.is_active)}>
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
                  <Input id="monthly_request_limit" type="number" value={currentUser.monthly_request_limit ?? ""} onChange={handleFormChange} placeholder="10000" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="monthly_token_limit">Token Limit</Label>
                  <Input id="monthly_token_limit" type="number" value={currentUser.monthly_token_limit ?? ""} onChange={handleFormChange} placeholder="500000" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="monthly_cost_limit">Cost Limit ($)</Label>
                  <Input id="monthly_cost_limit" type="number" value={currentUser.monthly_cost_limit ?? ""} onChange={handleFormChange} placeholder="200" />
                </div>
              </div>

              {/* NEW: Model Assignment Section */}
              <Separator />
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">AI Model Access</h3>
                <p className="text-sm text-gray-600">
                  Select which AI models this user can access
                </p>
                
                <div className="grid grid-cols-1 gap-3 max-h-64 overflow-y-auto border rounded p-4">
                  {availableModels.map(model => (
                    <div key={model.id} className="flex items-center space-x-3">
                      <Checkbox
                        id={`model-${model.id}`}
                        checked={assignedModelIds.includes(model.id)}
                        onCheckedChange={(checked) => 
                          handleModelToggle(model.id, checked as boolean)
                        }
                      />
                      <label 
                        htmlFor={`model-${model.id}`}
                        className="flex-1 cursor-pointer"
                      >
                        <div className="font-medium">{model.name}</div>
                        <div className="text-sm text-gray-500">{model.provider}</div>
                      </label>
                    </div>
                  ))}
                </div>
                
                <p className="text-sm text-blue-600">
                  {assignedModelIds.length} model(s) selected
                </p>
              </div>

          </div>
          <DialogFooter>
            <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
            <Button onClick={handleUpdateUser}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>


      <Card className="border border-gray-200">
        <CardHeader>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
            <CardTitle>All Users ({users.length})</CardTitle>
            <div className="flex space-x-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Search users..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 w-64"
                />
              </div>
              <Button variant="outline" size="sm">
                <Filter className="h-4 w-4 mr-2" />
                Filter
              </Button>
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
                        {user.organization_name || <span className="text-gray-400">Not Set</span>}
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
                    <TableCell className="text-right">
                        <Button variant="outline" size="sm" onClick={() => openEditDialog(user)}>
                            <Edit className="h-4 w-4 mr-2" />
                            Edit
                        </Button>
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