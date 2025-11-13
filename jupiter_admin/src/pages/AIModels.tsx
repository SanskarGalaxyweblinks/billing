import React, { useState, useEffect } from "react";
import axios from "axios";

// UI Components from shadcn/ui - ensure these are correctly imported in your project
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Plus,
  Edit,
  Trash2,
  Settings,
  ArrowRight,
  DollarSign,
  Zap,
} from "lucide-react"; // Added DollarSign, Zap icons
import { Separator } from "@/components/ui/separator";
import apiClient from "@/lib/api";

//================================================================
// 1. API SERVICE LOGIC & TYPES (UNCHANGED)
//================================================================

const API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/admin`;

export type CostCalculationType = "tokens" | "request";

export interface AIModel {
  id: number;
  name: string;
  provider: string;
  model_identifier: string;
  input_cost_per_1k_tokens: number;
  output_cost_per_1k_tokens: number;
  max_tokens: number;
  context_window: number;
  capabilities: Record<string, any>;
  status: "active" | "inactive" | "under_updation";
  substitute_model_id?: number;
  created_at: string;
  request_cost: number;
  cost_calculation_type: CostCalculationType;
}

export type AIModelCreate = Omit<AIModel, "id" | "created_at">;
export type AIModelUpdate = Partial<AIModelCreate>;

const getAllModels = async (): Promise<AIModel[]> => {
  const response = await apiClient.get(`/admin/models`);
  return response.data;
};

const createModel = async (modelData: AIModelCreate): Promise<AIModel> => {
  const response = await apiClient.post(`/admin/models`, modelData);
  return response.data;
};

const updateModel = async (
  id: number,
  modelData: AIModelUpdate
): Promise<AIModel> => {
  const response = await apiClient.put(`/admin/models/${id}`, modelData);
  return response.data;
};

const deleteModel = async (id: number): Promise<void> => {
  await apiClient.delete(`/admin/models/${id}`);
};

//================================================================
// 2. DIALOG SUB-COMPONENTS (MODIFIED)
//================================================================

interface ModelFormDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  model: AIModel | null;
  onSuccess: () => void;
  allModels: AIModel[];
}

const ModelFormDialog = ({
  isOpen,
  onOpenChange,
  model,
  onSuccess,
  allModels,
}: ModelFormDialogProps) => {
  const [formData, setFormData] = useState<any>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [capabilitiesError, setCapabilitiesError] = useState<string | null>(
    null
  );
  // NEW STATE: To manage if 'Other' provider is selected and its custom value
  const [isCustomProvider, setIsCustomProvider] = useState(false);
  const [customProviderName, setCustomProviderName] = useState("");

  useEffect(() => {
    if (model) {
      // Check if the model's provider is one of the predefined ones
      const predefinedProviders = ["OpenAI", "Anthropic", "Google", "Meta"];
      const currentProvider = model.provider;
      const isPredefined = predefinedProviders.includes(currentProvider);

      setFormData({
        ...model,
        capabilities: JSON.stringify(model.capabilities, null, 2),
      });

      // Set custom provider state based on existing model's provider
      if (!isPredefined) {
        setIsCustomProvider(true);
        setCustomProviderName(currentProvider);
      } else {
        setIsCustomProvider(false);
        setCustomProviderName("");
      }
    } else {
      // Initialize for new model
      setFormData({
        name: "",
        provider: "OpenAI", // Default to a common one or first in list
        model_identifier: "",
        input_cost_per_1k_tokens: 0.0,
        output_cost_per_1k_tokens: 0.0,
        max_tokens: 4096,
        context_window: 8192,
        capabilities: "{}",
        status: "active",
        substitute_model_id: undefined,
        request_cost: 0.0,
        cost_calculation_type: "tokens",
      });
      setIsCustomProvider(false); // Reset for new model
      setCustomProviderName(""); // Reset for new model
    }
    setCapabilitiesError(null);
  }, [model, isOpen]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { id, value, type } = e.target;
    const isNumber =
      type === "number" ||
      id.includes("cost") ||
      id.includes("tokens") ||
      id.includes("window");

    if (id === "capabilities") {
      try {
        JSON.parse(value);
        setCapabilitiesError(null);
      } catch {
        setCapabilitiesError("Invalid JSON format");
      }
    }

    setFormData({ ...formData, [id]: isNumber ? parseFloat(value) : value });
  };

  const handleSelectChange = (id: string, value: string | number) => {
    if (id === "provider") {
      if (value === "Other") {
        setIsCustomProvider(true);
        setFormData({ ...formData, provider: "" }); // Clear provider to force custom input
      } else {
        setIsCustomProvider(false);
        setCustomProviderName(""); // Clear custom input
        setFormData({ ...formData, [id]: value });
      }
    } else {
      const newFormData = { ...formData, [id]: value };

      if (id === "status" && value !== "under_updation") {
        newFormData.substitute_model_id = undefined;
      }

      if (id === "cost_calculation_type") {
        if (value === "tokens") {
          newFormData.request_cost = 0.0;
        } else if (value === "request") {
          newFormData.input_cost_per_1k_tokens = 0.0;
          newFormData.output_cost_per_1k_tokens = 0.0;
        }
      }
      setFormData(newFormData);
    }
  };

  const handleCustomProviderChange = (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const { value } = e.target;
    setCustomProviderName(value);
    setFormData({ ...formData, provider: value }); // Update formData's provider directly
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setCapabilitiesError(null);

    // Validate custom provider if "Other" is selected
    if (isCustomProvider && !customProviderName.trim()) {
      alert("Please enter a custom provider name.");
      setIsSubmitting(false);
      return;
    }

    try {
      let capabilities;
      try {
        capabilities = JSON.parse(formData.capabilities as string);
      } catch {
        setCapabilitiesError("Capabilities must be valid JSON.");
        setIsSubmitting(false);
        return;
      }

      const payload: any = { ...formData, capabilities };

      // Ensure provider is correctly set if custom
      if (isCustomProvider) {
        payload.provider = customProviderName.trim();
      }

      delete payload.is_active;

      if (payload.status !== "under_updation") {
        delete payload.substitute_model_id;
      }

      if (payload.cost_calculation_type === "tokens") {
        delete payload.request_cost;
      } else if (payload.cost_calculation_type === "request") {
        delete payload.input_cost_per_1k_tokens;
        delete payload.output_cost_per_1k_tokens;
      }

      if (model) {
        await updateModel(model.id, payload as AIModelUpdate);
      } else {
        await createModel(payload as AIModelCreate);
      }
      onSuccess();
    } catch (error) {
      console.error("Failed to save model:", error);
      alert("An error occurred while saving the model.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {model ? "Edit AI Model" : "Add New AI Model"}
          </DialogTitle>
          <DialogDescription>
            {model
              ? "Make changes to the AI model here. Click save when you're done."
              : "Add a new AI model to your system. Fill in the details below."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="grid gap-4 py-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Model Name</Label>
              <Input
                id="name"
                value={formData.name || ""}
                onChange={handleChange}
                placeholder="GPT-4 Turbo"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="provider">Provider</Label>
              {/* Conditional rendering for Provider input */}
              {!isCustomProvider ? (
                <Select
                  value={formData.provider || ""} // Use formData.provider to reflect current selection
                  onValueChange={(v) => handleSelectChange("provider", v)}
                  required
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select provider" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="OpenAI">OpenAI</SelectItem>
                    <SelectItem value="Anthropic">Anthropic</SelectItem>
                    <SelectItem value="Google">Google</SelectItem>
                    <SelectItem value="Meta">Meta</SelectItem>
                    <SelectItem value="Other">Other (Specify)</SelectItem>
                  </SelectContent>
                </Select>
              ) : (
                <div className="flex items-center gap-2">
                  <Input
                    id="customProvider"
                    value={customProviderName}
                    onChange={handleCustomProviderChange}
                    placeholder="Enter custom provider name"
                    required
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setIsCustomProvider(false);
                      setCustomProviderName("");
                      setFormData({ ...formData, provider: "OpenAI" }); // Reset to a default pre-defined
                    }}
                  >
                    X
                  </Button>
                </div>
              )}
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="model_identifier">Model Identifier</Label>
            <Input
              id="model_identifier"
              value={formData.model_identifier || ""}
              onChange={handleChange}
              placeholder="gpt-4-turbo-preview"
              required
            />
          </div>

          <Separator className="my-2" />

          <div className="space-y-2">
            <Label htmlFor="cost_calculation_type">Cost Calculation Type</Label>
            <Select
              value={formData.cost_calculation_type || "tokens"}
              onValueChange={(v: CostCalculationType) =>
                handleSelectChange("cost_calculation_type", v)
              }
              required
            >
              <SelectTrigger id="cost_calculation_type">
                <SelectValue placeholder="Select cost type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tokens">Per Token</SelectItem>
                <SelectItem value="request">Per Request</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {formData.cost_calculation_type === "tokens" ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="input_cost_per_1k_tokens">
                  Input Cost ($/1K tokens)
                </Label>
                <Input
                  id="input_cost_per_1k_tokens"
                  type="number"
                  step="0.000001"
                  value={formData.input_cost_per_1k_tokens || 0}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="output_cost_per_1k_tokens">
                  Output Cost ($/1K tokens)
                </Label>
                <Input
                  id="output_cost_per_1k_tokens"
                  type="number"
                  step="0.000001"
                  value={formData.output_cost_per_1k_tokens || 0}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <Label htmlFor="request_cost">Request Cost ($/request)</Label>
              <Input
                id="request_cost"
                type="number"
                step="0.000001"
                value={formData.request_cost || 0}
                onChange={handleChange}
                required
              />
            </div>
          )}

          <Separator className="my-2" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="max_tokens">Max Tokens</Label>
              <Input
                id="max_tokens"
                type="number"
                value={formData.max_tokens || 0}
                onChange={handleChange}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="context_window">Context Window</Label>
              <Input
                id="context_window"
                type="number"
                value={formData.context_window || 0}
                onChange={handleChange}
                required
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="capabilities">Capabilities (JSON)</Label>
            <Textarea
              id="capabilities"
              value={formData.capabilities || "{}"}
              onChange={handleChange}
              className="h-24 font-mono"
            />
            {capabilitiesError && (
              <p className="text-red-500 text-sm mt-1">{capabilitiesError}</p>
            )}
          </div>

          <Separator className="my-2" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select
                value={formData.status || "active"}
                onValueChange={(v) => handleSelectChange("status", v)}
              >
                <SelectTrigger id="status">
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                  <SelectItem value="under_updation">Under Updation</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {formData.status === "under_updation" && (
              <div className="space-y-2">
                <Label htmlFor="substitute_model_id">Substitute Model</Label>
                <Select
                  value={formData.substitute_model_id?.toString() || ""}
                  onValueChange={(v) =>
                    handleSelectChange("substitute_model_id", Number(v))
                  }
                  required
                >
                  <SelectTrigger id="substitute_model_id">
                    <SelectValue placeholder="Select a substitute model" />
                  </SelectTrigger>
                  <SelectContent>
                    {allModels
                      .filter((m) => m.id !== model?.id)
                      .map((substitute) => (
                        <SelectItem
                          key={substitute.id}
                          value={substitute.id.toString()}
                        >
                          {substitute.name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>

          <DialogFooter className="pt-4 flex flex-col sm:flex-row sm:justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || !!capabilitiesError}
            >
              {isSubmitting ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

// --- Component for Delete Confirmation Dialog (Unchanged) ---
interface DeleteConfirmationDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onConfirm: () => void;
  modelName?: string;
}

const DeleteConfirmationDialog = ({
  isOpen,
  onOpenChange,
  onConfirm,
  modelName,
}: DeleteConfirmationDialogProps) => (
  <Dialog open={isOpen} onOpenChange={onOpenChange}>
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Are you absolutely sure?</DialogTitle>
        <DialogDescription>
          This action cannot be undone. This will permanently delete the{" "}
          <strong>{modelName}</strong> model.
        </DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)}>
          Cancel
        </Button>
        <Button variant="destructive" onClick={onConfirm}>
          Delete
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
);

//================================================================
// 3. MAIN AI MODELS COMPONENT (UNCHANGED)
//================================================================

const AIModels = () => {
  const [models, setModels] = useState<AIModel[]>([]);
  const [filteredModels, setFilteredModels] = useState<AIModel[]>([]);
  const [filterProvider, setFilterProvider] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterCostType, setFilterCostType] = useState("all");
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState<AIModel | null>(null);

  const fetchModels = async () => {
    try {
      const data = await getAllModels();
      setModels(
        data.sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
      );
    } catch (error) {
      console.error("Failed to fetch models:", error);
      alert(
        "Failed to fetch models. Please check the console for more details."
      );
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  useEffect(() => {
    const applyFilters = () => {
      let tempModels = models;

      if (filterProvider !== "all") {
        tempModels = tempModels.filter(
          (model) => model.provider === filterProvider
        );
      }

      if (filterStatus !== "all") {
        tempModels = tempModels.filter(
          (model) => model.status === filterStatus
        );
      }

      if (filterCostType !== "all") {
        tempModels = tempModels.filter(
          (model) => model.cost_calculation_type === filterCostType
        );
      }

      setFilteredModels(tempModels);
    };
    applyFilters();
  }, [filterProvider, filterStatus, filterCostType, models]);

  const handleAddModelClick = () => {
    setSelectedModel(null);
    setIsFormOpen(true);
  };

  const handleEditModelClick = (model: AIModel) => {
    setSelectedModel(model);
    setIsFormOpen(true);
  };

  const handleDeleteModelClick = (model: AIModel) => {
    setSelectedModel(model);
    setIsDeleteOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (selectedModel) {
      try {
        await deleteModel(selectedModel.id);
        fetchModels();
        setIsDeleteOpen(false);
        setSelectedModel(null);
      } catch (error) {
        console.error("Failed to delete model:", error);
        alert(
          "Failed to delete model. Please check the console for more details."
        );
      }
    }
  };

  const handleFormSuccess = () => {
    setIsFormOpen(false);
    fetchModels();
  };

  const getProviderColor = (provider: string) => {
    switch (provider) {
      case "OpenAI":
        return "bg-green-100 text-green-800";
      case "Anthropic":
        return "bg-orange-100 text-orange-800";
      case "Google":
        return "bg-blue-100 text-blue-800";
      case "Meta":
        return "bg-purple-100 text-purple-800";
      default:
        return "bg-gray-100 text-gray-800"; // Default for custom providers
    }
  };

  const getStatusBadge = (status: AIModel["status"]) => {
    switch (status) {
      case "active":
        return (
          <Badge className="bg-green-600 hover:bg-green-700">Active</Badge>
        );
      case "inactive":
        return <Badge variant="secondary">Inactive</Badge>;
      case "under_updation":
        return (
          <Badge
            variant="outline"
            className="border-orange-500 text-orange-600"
          >
            Under Updation
          </Badge>
        );
      default:
        return <Badge variant="destructive">Unknown</Badge>;
    }
  };

  const getCostDisplay = (model: AIModel) => {
    if (model.cost_calculation_type === "tokens") {
      return (
        <>
          <div className="flex items-center space-x-1">
            <DollarSign className="h-4 w-4 text-gray-500" />
            <p className="font-medium text-gray-700">Input Cost</p>
          </div>
          <p className="text-base font-semibold text-gray-900">
            ${model.input_cost_per_1k_tokens.toFixed(6)}
          </p>
          <p className="text-xs text-gray-500">per 1K tokens</p>
        </>
      );
    } else {
      return (
        <>
          <div className="flex items-center space-x-1">
            <DollarSign className="h-4 w-4 text-gray-500" />
            <p className="font-medium text-gray-700">Request Cost</p>
          </div>
          <p className="text-base font-semibold text-gray-900">
            ${model.request_cost.toFixed(6)}
          </p>
          <p className="text-xs text-gray-500">per request</p>
        </>
      );
    }
  };

  return (
    <div className="p-4 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AI Models</h1>
          <p className="text-gray-600 mt-1 text-sm sm:text-base">
            Manage AI models, pricing, and configurations
          </p>
        </div>
        <Button onClick={handleAddModelClick}>
          <Plus className="h-4 w-4 mr-2" />
          Add Model
        </Button>
      </div>

      <ModelFormDialog
        isOpen={isFormOpen}
        onOpenChange={setIsFormOpen}
        model={selectedModel}
        onSuccess={handleFormSuccess}
        allModels={models}
      />

      <DeleteConfirmationDialog
        isOpen={isDeleteOpen}
        onOpenChange={setIsDeleteOpen}
        onConfirm={handleDeleteConfirm}
        modelName={selectedModel?.name}
      />

      <Card className="border border-gray-200 shadow-sm">
        <CardHeader className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 p-4 sm:p-6">
          <CardTitle className="text-xl font-semibold">
            Models ({filteredModels.length})
          </CardTitle>
          <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
            {/* Filter by Cost Type */}
            <Select value={filterCostType} onValueChange={setFilterCostType}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue placeholder="Filter by cost type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Cost Types</SelectItem>
                <SelectItem value="tokens">Per Token</SelectItem>
                <SelectItem value="request">Per Request</SelectItem>
              </SelectContent>
            </Select>

            {/* Filter by Status */}
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="under_updation">Under Updation</SelectItem>
              </SelectContent>
            </Select>
            {/* Filter by Provider */}
            <Select value={filterProvider} onValueChange={setFilterProvider}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue placeholder="Filter by provider" />
              </SelectTrigger>
              <SelectContent>
                {/* Dynamically add existing providers and "Other" */}
                <SelectItem value="all">All Providers</SelectItem>
                <SelectItem value="OpenAI">OpenAI</SelectItem>
                <SelectItem value="Anthropic">Anthropic</SelectItem>
                <SelectItem value="Google">Google</SelectItem>
                <SelectItem value="Meta">Meta</SelectItem>
                {/* Optionally, you can dynamically add other existing unique providers from `models` here */}
                {Array.from(new Set(models.map((m) => m.provider)))
                  .sort()
                  .map(
                    (p) =>
                      !["OpenAI", "Anthropic", "Google", "Meta"].includes(
                        p
                      ) && (
                        <SelectItem key={p} value={p}>
                          {p}
                        </SelectItem>
                      )
                  )}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-4 sm:p-6 pt-0">
          <div className="grid gap-4">
            {filteredModels.length > 0 ? (
              filteredModels.map((model) => {
                const substituteModelName =
                  model.status === "under_updation" && model.substitute_model_id
                    ? models.find((m) => m.id === model.substitute_model_id)
                        ?.name
                    : null;

                return (
                  <Card
                    key={model.id}
                    className="border border-gray-100 shadow-sm hover:shadow-md transition-shadow duration-200"
                  >
                    <CardContent className="p-4 sm:p-6">
                      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 md:gap-2">
                        <div className="flex items-center space-x-3 flex-wrap gap-y-2">
                          <div className="p-2 bg-gray-50 rounded-lg">
                            <Settings className="h-5 w-5 text-gray-600" />
                          </div>
                          <div>
                            <h3 className="font-semibold text-lg text-gray-900">
                              {model.name}
                            </h3>
                            <p className="text-sm text-gray-500">
                              {model.model_identifier}
                            </p>
                          </div>
                          <Badge className={getProviderColor(model.provider)}>
                            {model.provider}
                          </Badge>
                          {getStatusBadge(model.status)}
                        </div>
                        <div className="flex space-x-2 flex-shrink-0">
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => handleEditModelClick(model)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8 text-red-600 hover:text-red-700"
                            onClick={() => handleDeleteModelClick(model)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      {substituteModelName && (
                        <div className="mt-4 flex items-center text-sm text-orange-600 bg-orange-50 border border-orange-200 rounded-md p-3">
                          <Zap className="h-4 w-4 mr-2 flex-shrink-0" />
                          <span>
                            Under Updation. Using substitute:{" "}
                            <strong className="font-semibold">
                              {substituteModelName}
                            </strong>
                          </span>
                        </div>
                      )}

                      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4 text-sm">
                        {/* Cost Display */}
                        <div className="space-y-1">{getCostDisplay(model)}</div>

                        {model.cost_calculation_type === "tokens" && (
                          <div className="space-y-1">
                            <div className="flex items-center space-x-1">
                              <DollarSign className="h-4 w-4 text-gray-500" />
                              <p className="font-medium text-gray-700">
                                Output Cost
                              </p>
                            </div>
                            <p className="text-base font-semibold text-gray-900">
                              ${model.output_cost_per_1k_tokens.toFixed(6)}
                            </p>
                            <p className="text-xs text-gray-500">
                              per 1K tokens
                            </p>
                          </div>
                        )}

                        <div className="space-y-1">
                          <p className="font-medium text-gray-700">
                            Max Tokens
                          </p>
                          <p className="text-base font-semibold text-gray-900">
                            {model.max_tokens}
                          </p>
                        </div>
                        <div className="space-y-1">
                          <p className="font-medium text-gray-700">
                            Context Window
                          </p>
                          <p className="text-base font-semibold text-gray-900">
                            {model.context_window}
                          </p>
                        </div>
                        <div className="space-y-1">
                          <p className="font-medium text-gray-700">
                            Created At
                          </p>
                          <p className="text-base font-semibold text-gray-900">
                            {new Date(model.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })
            ) : (
              <div className="text-center py-12 flex flex-col items-center justify-center">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    vectorEffect="non-scaling-stroke"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 13h6m-3-3v6m-9 1-2 2L4 23a1 1 0 01-1.414 0l-2.121-2.121a1 1 0 010-1.414L3 17l2-2h8a1 1 0 001-1V5a1 1 0 00-1-1H3a1 1 0 00-1 1v6z"
                  />
                </svg>
                <h3 className="mt-2 text-lg font-medium text-gray-900">
                  No AI Models
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  Get started by adding a new AI model.
                </p>
                <Button onClick={handleAddModelClick} className="mt-6">
                  <Plus className="h-4 w-4 mr-2" />
                  Add First Model
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AIModels;
