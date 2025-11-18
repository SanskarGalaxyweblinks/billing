import { useState, useEffect } from "react";
import apiClient from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Calendar,
  Clock,
  DollarSign,
  Loader2,
  AlertCircle,
  CheckCircle,
  Bot,
  User,
  Settings,
} from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

interface User {
  id: number;
  email: string;
  full_name: string;
  organization_name: string;
  is_active: boolean;
  monthly_request_limit: number | null;
  monthly_token_limit: number | null;
  monthly_cost_limit: number | null;
}

interface AIModel {
  id: number;
  name: string;
  provider: string;
  status: string;
  cost_calculation_type: string;
  request_cost: number;
  input_cost_per_1k_tokens: number;
  output_cost_per_1k_tokens: number;
  max_tokens: number;
  total_assignments: number;
  total_revenue: number;
}

interface ModelAssignment {
  id?: number;
  user_id: number;
  model_id: number;
  access_level: string;
  is_active: boolean;
  daily_request_limit?: number;
  monthly_request_limit?: number;
  daily_token_limit?: number;
  monthly_token_limit?: number;
  requests_per_minute?: number;
  requests_per_hour?: number;
  expires_at?: string;
  cost_multiplier?: number;
}

interface UserModelFormProps {
  userId?: number;
  modelId?: number;
  assignmentId?: number;
  mode: "create" | "edit" | "bulk";
  selectedUsers?: number[];
  selectedModels?: number[];
  onSuccess?: () => void;
  onCancel?: () => void;
  initialData?: Partial<ModelAssignment>;
}

const UserModelForm: React.FC<UserModelFormProps> = ({
  userId,
  modelId,
  assignmentId,
  mode,
  selectedUsers = [],
  selectedModels = [],
  onSuccess,
  onCancel,
  initialData,
}) => {
  const [users, setUsers] = useState<User[]>([]);
  const [models, setModels] = useState<AIModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const [formData, setFormData] = useState<ModelAssignment>({
    user_id: userId || 0,
    model_id: modelId || 0,
    access_level: "read_write",
    is_active: true,
    cost_multiplier: 1.0,
    ...initialData,
  });

  const [selectedUserIds, setSelectedUserIds] = useState<number[]>(
    mode === "bulk" ? selectedUsers : userId ? [userId] : []
  );
  const [selectedModelIds, setSelectedModelIds] = useState<number[]>(
    mode === "bulk" ? selectedModels : modelId ? [modelId] : []
  );

  const [validationErrors, setValidationErrors] = useState<{[key: string]: string}>({});
  const [costEstimate, setCostEstimate] = useState<number>(0);

  const { toast } = useToast();

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    calculateCostEstimate();
  }, [formData, selectedModelIds]);

  const loadInitialData = async () => {
    setIsLoading(true);
    try {
      const [usersResponse, modelsResponse] = await Promise.all([
        apiClient.get("/admin/users?is_active=true&limit=1000"),
        apiClient.get("/admin/models?status=active"),
      ]);
      
      setUsers(usersResponse.data);
      setModels(modelsResponse.data);

      // Load existing assignment data if editing
      if (mode === "edit" && assignmentId) {
        const assignmentResponse = await apiClient.get(`/admin/model-assignments/${assignmentId}`);
        const assignmentData = assignmentResponse.data;
        setFormData({
          ...assignmentData,
          expires_at: assignmentData.expires_at?.split('T')[0] || '',
        });
        setSelectedUserIds([assignmentData.user_id]);
        setSelectedModelIds([assignmentData.model_id]);
      }
    } catch (error) {
      console.error("Failed to load data:", error);
      toast({
        title: "Failed to load data",
        description: "Could not load users and models",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const calculateCostEstimate = () => {
    if (selectedModelIds.length === 0) {
      setCostEstimate(0);
      return;
    }

    const selectedModel = models.find(m => m.id === selectedModelIds[0]);
    if (!selectedModel) {
      setCostEstimate(0);
      return;
    }

    let estimate = 0;
    if (formData.monthly_request_limit) {
      if (selectedModel.cost_calculation_type === "request") {
        estimate = formData.monthly_request_limit * selectedModel.request_cost;
      } else {
        // Estimate based on average tokens per request (assume 1000 tokens)
        const avgTokensPerRequest = 1000;
        const tokensPerMonth = formData.monthly_request_limit * avgTokensPerRequest;
        estimate = (tokensPerMonth / 1000) * selectedModel.input_cost_per_1k_tokens;
      }
      
      if (formData.cost_multiplier) {
        estimate *= formData.cost_multiplier;
      }
    }

    setCostEstimate(estimate);
  };

  const validateForm = (): boolean => {
    const errors: {[key: string]: string} = {};

    if (mode !== "bulk") {
      if (!formData.user_id) errors.user = "User is required";
      if (!formData.model_id) errors.model = "Model is required";
    } else {
      if (selectedUserIds.length === 0) errors.users = "At least one user must be selected";
      if (selectedModelIds.length === 0) errors.models = "At least one model must be selected";
    }

    if (!formData.access_level) errors.access_level = "Access level is required";

    if (formData.daily_request_limit && formData.monthly_request_limit) {
      if (formData.daily_request_limit * 30 > formData.monthly_request_limit) {
        errors.limits = "Daily limit × 30 exceeds monthly limit";
      }
    }

    if (formData.expires_at && new Date(formData.expires_at) <= new Date()) {
      errors.expires_at = "Expiry date must be in the future";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      toast({
        title: "Validation Failed",
        description: "Please fix the errors below",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === "create") {
        await apiClient.post("/admin/model-assignments", {
          ...formData,
          expires_at: formData.expires_at ? `${formData.expires_at}T23:59:59Z` : undefined,
        });
        toast({ title: "Assignment created successfully!" });
      } else if (mode === "edit" && assignmentId) {
        await apiClient.put(`/admin/model-assignments/${assignmentId}`, {
          ...formData,
          expires_at: formData.expires_at ? `${formData.expires_at}T23:59:59Z` : undefined,
        });
        toast({ title: "Assignment updated successfully!" });
      } else if (mode === "bulk") {
        const assignments = [];
        for (const userId of selectedUserIds) {
          for (const modelId of selectedModelIds) {
            assignments.push({
              ...formData,
              user_id: userId,
              model_id: modelId,
              expires_at: formData.expires_at ? `${formData.expires_at}T23:59:59Z` : undefined,
            });
          }
        }
        
        await apiClient.post("/admin/model-assignments/bulk", { assignments });
        toast({ 
          title: "Bulk assignments created!", 
          description: `Created ${assignments.length} assignments` 
        });
      }

      onSuccess?.();
    } catch (error: any) {
      toast({
        title: "Failed to save assignment",
        description: error.response?.data?.detail || "Could not save assignment",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUserToggle = (userId: number, checked: boolean) => {
    if (checked) {
      setSelectedUserIds(prev => [...prev, userId]);
    } else {
      setSelectedUserIds(prev => prev.filter(id => id !== userId));
    }
  };

  const handleModelToggle = (modelId: number, checked: boolean) => {
    if (checked) {
      setSelectedModelIds(prev => [...prev, modelId]);
    } else {
      setSelectedModelIds(prev => prev.filter(id => id !== modelId));
    }
  };

  const getSelectedUser = () => users.find(u => u.id === formData.user_id);
  const getSelectedModel = () => models.find(m => m.id === formData.model_id);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
        <span className="ml-4">Loading...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">
          {mode === "create" && "Create Model Assignment"}
          {mode === "edit" && "Edit Model Assignment"}
          {mode === "bulk" && "Bulk Model Assignment"}
        </h3>
        <p className="text-sm text-gray-600 mt-1">
          {mode === "bulk" 
            ? "Assign multiple models to multiple users with the same configuration"
            : "Configure user access to AI models with specific permissions and limits"
          }
        </p>
      </div>

      <Tabs defaultValue="selection" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="selection">Selection</TabsTrigger>
          <TabsTrigger value="permissions">Permissions</TabsTrigger>
          <TabsTrigger value="limits">Limits & Pricing</TabsTrigger>
        </TabsList>

        <TabsContent value="selection" className="space-y-4">
          {mode === "bulk" ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* User Selection */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <User className="h-4 w-4" />
                    Select Users ({selectedUserIds.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {users.map(user => (
                      <div key={user.id} className="flex items-center space-x-2">
                        <Checkbox
                          id={`user-${user.id}`}
                          checked={selectedUserIds.includes(user.id)}
                          onCheckedChange={(checked) => 
                            handleUserToggle(user.id, checked as boolean)
                          }
                        />
                        <label 
                          htmlFor={`user-${user.id}`}
                          className="flex-1 cursor-pointer text-sm"
                        >
                          <div className="font-medium">{user.full_name}</div>
                          <div className="text-gray-500">{user.email} • {user.organization_name}</div>
                        </label>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Model Selection */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Bot className="h-4 w-4" />
                    Select Models ({selectedModelIds.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {models.map(model => (
                      <div key={model.id} className="flex items-center space-x-2">
                        <Checkbox
                          id={`model-${model.id}`}
                          checked={selectedModelIds.includes(model.id)}
                          onCheckedChange={(checked) => 
                            handleModelToggle(model.id, checked as boolean)
                          }
                        />
                        <label 
                          htmlFor={`model-${model.id}`}
                          className="flex-1 cursor-pointer text-sm"
                        >
                          <div className="font-medium">{model.name}</div>
                          <div className="text-gray-500">
                            {model.provider} • ${model.request_cost}/req • {model.total_assignments} assignments
                          </div>
                        </label>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>User *</Label>
                <Select 
                  value={formData.user_id.toString()} 
                  onValueChange={(v) => setFormData(prev => ({...prev, user_id: parseInt(v)}))}
                  disabled={mode === "edit" || !!userId}
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
                {validationErrors.user && (
                  <p className="text-sm text-red-600">{validationErrors.user}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label>AI Model *</Label>
                <Select 
                  value={formData.model_id.toString()} 
                  onValueChange={(v) => setFormData(prev => ({...prev, model_id: parseInt(v)}))}
                  disabled={mode === "edit" || !!modelId}
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
                {validationErrors.model && (
                  <p className="text-sm text-red-600">{validationErrors.model}</p>
                )}
              </div>
            </div>
          )}

          {/* Selection Summary */}
          <Card className="bg-blue-50">
            <CardContent className="pt-4">
              <div className="flex items-center gap-2 text-blue-800">
                <CheckCircle className="h-4 w-4" />
                <span className="font-medium">Selection Summary</span>
              </div>
              <div className="text-sm text-blue-700 mt-2">
                {mode === "bulk" ? (
                  <>
                    {selectedUserIds.length} user(s) × {selectedModelIds.length} model(s) = {selectedUserIds.length * selectedModelIds.length} assignment(s)
                  </>
                ) : (
                  <>
                    {getSelectedUser()?.full_name || "No user selected"} → {getSelectedModel()?.name || "No model selected"}
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="permissions" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Access Level *</Label>
              <Select 
                value={formData.access_level} 
                onValueChange={(v) => setFormData(prev => ({...prev, access_level: v}))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="read_only">
                    <div>
                      <div>Read Only</div>
                      <div className="text-xs text-gray-500">Can view model info only</div>
                    </div>
                  </SelectItem>
                  <SelectItem value="read_write">
                    <div>
                      <div>Read Write</div>
                      <div className="text-xs text-gray-500">Can make API calls and view info</div>
                    </div>
                  </SelectItem>
                  <SelectItem value="admin">
                    <div>
                      <div>Admin</div>
                      <div className="text-xs text-gray-500">Full access including configuration</div>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Status</Label>
              <Select 
                value={formData.is_active ? "active" : "inactive"} 
                onValueChange={(v) => setFormData(prev => ({...prev, is_active: v === "active"}))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Expiry Date (Optional)</Label>
            <Input 
              type="date"
              value={formData.expires_at || ''}
              onChange={(e) => setFormData(prev => ({
                ...prev, 
                expires_at: e.target.value
              }))}
              min={new Date().toISOString().split('T')[0]}
            />
            {validationErrors.expires_at && (
              <p className="text-sm text-red-600">{validationErrors.expires_at}</p>
            )}
            <p className="text-xs text-gray-500">
              Leave empty for permanent access
            </p>
          </div>
        </TabsContent>

        <TabsContent value="limits" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Request Limits
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Daily Request Limit</Label>
                  <Input 
                    type="number" 
                    placeholder="1000"
                    value={formData.daily_request_limit || ''}
                    onChange={(e) => setFormData(prev => ({
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
                    value={formData.monthly_request_limit || ''}
                    onChange={(e) => setFormData(prev => ({
                      ...prev, 
                      monthly_request_limit: e.target.value ? parseInt(e.target.value) : undefined
                    }))}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Requests per Minute</Label>
                  <Input 
                    type="number" 
                    placeholder="10"
                    value={formData.requests_per_minute || ''}
                    onChange={(e) => setFormData(prev => ({
                      ...prev, 
                      requests_per_minute: e.target.value ? parseInt(e.target.value) : undefined
                    }))}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Settings className="h-4 w-4" />
                  Token Limits
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Daily Token Limit</Label>
                  <Input 
                    type="number" 
                    placeholder="100000"
                    value={formData.daily_token_limit || ''}
                    onChange={(e) => setFormData(prev => ({
                      ...prev, 
                      daily_token_limit: e.target.value ? parseInt(e.target.value) : undefined
                    }))}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Monthly Token Limit</Label>
                  <Input 
                    type="number" 
                    placeholder="3000000"
                    value={formData.monthly_token_limit || ''}
                    onChange={(e) => setFormData(prev => ({
                      ...prev, 
                      monthly_token_limit: e.target.value ? parseInt(e.target.value) : undefined
                    }))}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Cost Multiplier</Label>
                  <Input 
                    type="number" 
                    step="0.1"
                    placeholder="1.0"
                    value={formData.cost_multiplier || ''}
                    onChange={(e) => setFormData(prev => ({
                      ...prev, 
                      cost_multiplier: e.target.value ? parseFloat(e.target.value) : undefined
                    }))}
                  />
                  <p className="text-xs text-gray-500">
                    Multiply base model costs (1.0 = normal pricing)
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {validationErrors.limits && (
            <div className="flex items-center gap-2 text-red-600 text-sm">
              <AlertCircle className="h-4 w-4" />
              {validationErrors.limits}
            </div>
          )}

          {/* Cost Estimate */}
          <Card className="bg-green-50">
            <CardContent className="pt-4">
              <div className="flex items-center gap-2 text-green-800">
                <DollarSign className="h-4 w-4" />
                <span className="font-medium">Estimated Monthly Cost</span>
              </div>
              <div className="text-2xl font-bold text-green-700 mt-1">
                ${costEstimate.toFixed(2)}
              </div>
              <div className="text-sm text-green-600 mt-1">
                Based on {formData.monthly_request_limit || 'unlimited'} monthly requests
                {formData.cost_multiplier !== 1.0 && (
                  <> with {formData.cost_multiplier}× cost multiplier</>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Action Buttons */}
      <div className="flex gap-3 pt-4 border-t">
        <Button 
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="flex-1"
        >
          {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          {mode === "create" && "Create Assignment"}
          {mode === "edit" && "Update Assignment"}
          {mode === "bulk" && `Create ${selectedUserIds.length * selectedModelIds.length} Assignments`}
        </Button>
        
        <Button 
          variant="outline" 
          onClick={onCancel}
          disabled={isSubmitting}
        >
          Cancel
        </Button>
      </div>
    </div>
  );
};

export default UserModelForm;