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
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Plus, Edit, Trash2, Loader2, Users, Settings } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

interface DiscountRule {
  id: number;
  name: string;
  priority: number;
  user_id?: number;
  model_id?: number;
  min_requests: number;
  max_requests?: number;
  discount_percentage: number;
  is_active: boolean;
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

const Discounts = () => {
  const [rules, setRules] = useState<DiscountRule[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [models, setModels] = useState<AIModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [currentRule, setCurrentRule] = useState<Partial<DiscountRule> | null>(null);
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

  useEffect(() => {
    fetchAllData();
  }, []);

  const openDialog = (rule: Partial<DiscountRule> | null = null) => {
    setCurrentRule(rule ? { ...rule } : { is_active: true, priority: 100, min_requests: 0 });
    setIsDialogOpen(true);
  };

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { id, value, type } = e.target;
    setCurrentRule(prev => ({ ...prev, [id]: type === 'number' ? parseFloat(value) || 0 : value }));
  };
  
  const handleSelectChange = (id: string, value: string) => {
    setCurrentRule(prev => ({ ...prev, [id]: value === 'all' ? undefined : parseInt(value) }));
  };

  const handleSubmit = async () => {
    if (!currentRule) return;

    const payload = {
        ...currentRule,
        max_requests: currentRule.max_requests || null,
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
    if (window.confirm("Are you sure you want to delete this rule?")) {
        try {
            await apiClient.delete(`/admin/discounts/${ruleId}`);
            toast({ title: "Success", description: "Discount rule deleted." });
            fetchAllData();
        } catch (error: any) {
             toast({ title: "Error", description: "Failed to delete rule.", variant: "destructive" });
        }
    }
  }

  if (isLoading) return <Loader2 className="animate-spin" />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Discount Rules</h1>
          <p className="text-gray-600 mt-1">Create and manage custom discount rules for users and models.</p>
        </div>
        <Button onClick={() => openDialog()}>
          <Plus className="mr-2 h-4 w-4" /> Add Rule
        </Button>
      </div>

      <Card>
        <CardHeader><CardTitle>All Rules ({rules.length})</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Applies To</TableHead>
                <TableHead>Discount</TableHead>
                <TableHead>Request Tier</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rules.map(rule => (
                <TableRow key={rule.id}>
                  <TableCell className="font-medium">{rule.name} <span className="text-gray-400"> (P{rule.priority})</span></TableCell>
                  <TableCell>
                    {rule.user_id ? <Badge variant="outline"><Users className="h-3 w-3 mr-1"/>{userMap.get(rule.user_id) || `User ID: ${rule.user_id}`}</Badge> : 
                     rule.model_id ? <Badge variant="outline"><Settings className="h-3 w-3 mr-1"/>{modelMap.get(rule.model_id) || `Model ID: ${rule.model_id}`}</Badge> : 
                     <Badge>Global</Badge>}
                  </TableCell>
                  <TableCell className="font-semibold">{rule.discount_percentage}%</TableCell>
                  <TableCell>{rule.min_requests} - {rule.max_requests || '∞'}</TableCell>
                  <TableCell><Badge variant={rule.is_active ? "default" : "secondary"}>{rule.is_active ? "Active" : "Inactive"}</Badge></TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="icon" onClick={() => openDialog(rule)}><Edit className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="icon" className="text-red-500" onClick={() => handleDelete(rule.id)}><Trash2 className="h-4 w-4" /></Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{currentRule?.id ? "Edit" : "Create"} Discount Rule</DialogTitle>
            <DialogDescription>Define the conditions and discount for this rule.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Rule Name</Label>
              <Input id="name" value={currentRule?.name || ""} onChange={handleFormChange} />
            </div>
            <div className="grid grid-cols-2 gap-4">
               <div className="space-y-2">
                  <Label htmlFor="user_id">User (Optional)</Label>
                  <Select value={currentRule?.user_id?.toString() || "all"} onValueChange={(v) => handleSelectChange('user_id', v)}>
                    <SelectTrigger><SelectValue placeholder="All Users" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Users</SelectItem>
                      {users.map(user => <SelectItem key={user.id} value={user.id.toString()}>{user.full_name}</SelectItem>)}
                    </SelectContent>
                  </Select>
              </div>
              <div className="space-y-2">
                  <Label htmlFor="model_id">AI Model (Optional)</Label>
                  <Select value={currentRule?.model_id?.toString() || "all"} onValueChange={(v) => handleSelectChange('model_id', v)}>
                    <SelectTrigger><SelectValue placeholder="All Models" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Models</SelectItem>
                      {models.map(model => <SelectItem key={model.id} value={model.id.toString()}>{model.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
              </div>
            </div>
             <div className="grid grid-cols-2 gap-4">
                 <div className="space-y-2">
                    <Label htmlFor="min_requests">Min Requests</Label>
                    <Input id="min_requests" type="number" value={currentRule?.min_requests || 0} onChange={handleFormChange} />
                </div>
                 <div className="space-y-2">
                    <Label htmlFor="max_requests">Max Requests (Optional)</Label>
                    <Input id="max_requests" type="number" value={currentRule?.max_requests || ""} onChange={handleFormChange} placeholder="Leave empty for no limit"/>
                </div>
             </div>
             <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Label htmlFor="discount_percentage">Discount %</Label>
                    <Input id="discount_percentage" type="number" value={currentRule?.discount_percentage || 0} onChange={handleFormChange} />
                </div>
                <div className="space-y-2">
                    <Label htmlFor="priority">Priority</Label>
                    <Input id="priority" type="number" value={currentRule?.priority || 100} onChange={handleFormChange} />
                </div>
             </div>
             <div className="flex items-center space-x-2">
                <Switch id="is_active" checked={currentRule?.is_active} onCheckedChange={(c) => setCurrentRule(p => ({...p, is_active: c}))}/>
                <Label htmlFor="is_active">Rule is Active</Label>
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
            <Button onClick={handleSubmit}>Save Rule</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Discounts;