// src/pages/UsageAnalytics.tsx
import React, { useEffect, useState } from "react";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BarChart3, ChevronDown } from "lucide-react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const UsageAnalytics = () => {
  const now = new Date();
  const defaultMonth = `${now.getFullYear()}-${String(
    now.getMonth() + 1
  ).padStart(2, "0")}`;
  const [selectedMonth, setSelectedMonth] = useState(defaultMonth);
  const [usageSummary, setUsageSummary] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUsageSummary = async () => {
      setUsageSummary(null);
      setError(null);
      try {
        const [year, month] = selectedMonth.split("-");
        const start_date = `${year}-${month}-01`;
        const end_date_obj = new Date(parseInt(year), parseInt(month), 0);
        const end_date = end_date_obj.toISOString().split("T")[0];

        const response = await apiClient.get("/admin/usage-summary", {
          params: { start_date, end_date },
        });

        setUsageSummary(response.data);
      } catch (err: any) {
        console.error("Failed to fetch usage summary", err);
        setError(err.response?.data?.detail || "Failed to fetch usage summary");
      }
    };

    fetchUsageSummary();
  }, [selectedMonth]);

  const getLastMonths = (count = 6) => {
    const months = [];
    const today = new Date();
    for (let i = 0; i < count; i++) {
      const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
      const monthValue = `${d.getFullYear()}-${String(
        d.getMonth() + 1
      ).padStart(2, "0")}`;
      const monthLabel = d.toLocaleString("default", {
        month: "long",
        year: "numeric",
      });
      months.push({ value: monthValue, label: monthLabel });
    }
    return months;
  };

  const monthOptions = getLastMonths();

  const formatTokens = (tokens: number) => {
    if (tokens >= 1_000_000) {
      return `${(tokens / 1_000_000).toFixed(1)}M`;
    } else if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toString();
  };

  if (error) return <p className="text-red-500">Error: {error}</p>;
  if (!usageSummary) return <p>Loading usage summary...</p>;

  const { global_summary, organization_stats, global_model_wise_summary } = usageSummary;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Usage Analytics</h1>
        <p className="text-gray-600 mt-2">
          Monitor API usage, costs, and performance metrics
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="border border-gray-200">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tokens</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatTokens(global_summary.total_tokens)}
            </div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
        <Card className="border border-gray-200">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${global_summary.total_cost.toFixed(3)}
            </div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
        <Card className="border border-gray-200">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Avg Response Time
            </CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {global_summary.avg_response_time.toFixed(2)} ms
            </div>
            <p className="text-xs text-muted-foreground">Average</p>
          </CardContent>
        </Card>
        <Card className="border border-gray-200">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(global_summary.success_rate * 100).toFixed(2)}%
            </div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border border-gray-200">
        <CardHeader>
          <CardTitle>Global Model-wise Usage</CardTitle>
        </CardHeader>
        <CardContent>
          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="global-model-usage">
              <AccordionTrigger>View Details</AccordionTrigger>
              <AccordionContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Model Name</TableHead>
                      <TableHead>Total Requests</TableHead>
                      <TableHead>Total Tokens</TableHead>
                      <TableHead>Total Cost</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {global_model_wise_summary.map((model: any, index: number) => (
                      <TableRow key={index}>
                        <TableCell>{model.model_name}</TableCell>
                        <TableCell>{model.total_requests}</TableCell>
                        <TableCell>{formatTokens(model.total_tokens)}</TableCell>
                        <TableCell>${model.total_cost.toFixed(3)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      </Card>

      <Card className="border border-gray-200">
        <CardHeader>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
            <CardTitle>Organization Usage Logs</CardTitle>
            <div className="flex space-x-2">
              <Select value={selectedMonth} onValueChange={setSelectedMonth}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Select month" />
                </SelectTrigger>
                <SelectContent>
                  {monthOptions.map((month) => (
                    <SelectItem key={month.value} value={month.value}>
                      {month.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-x-auto">
            <Accordion type="single" collapsible className="w-full">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Organization</TableHead>
                    <TableHead>Total Requests</TableHead>
                    <TableHead>Total Tokens</TableHead>
                    <TableHead>Total Cost</TableHead>
                    <TableHead>Avg Response Time</TableHead>
                    <TableHead>Success Rate</TableHead>
                    <TableHead className="w-[1px] p-0"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {organization_stats.map((org: any, index: number) => (
                    <AccordionItem value={`item-${index}`} asChild key={index}>
                      <>
                        <TableRow>
                          <TableCell className="font-medium">
                            {org.organization_name}
                          </TableCell>
                          <TableCell>{org.total_requests}</TableCell>
                          <TableCell>{formatTokens(org.total_tokens)}</TableCell>
                          <TableCell>${org.total_cost.toFixed(3)}</TableCell>
                          <TableCell>{org.avg_response_time.toFixed(2)} ms</TableCell>
                          <TableCell>
                            {(org.success_rate * 100).toFixed(2)}%
                          </TableCell>
                          <TableCell className="p-0">
                            <AccordionTrigger className="p-4" />
                          </TableCell>
                        </TableRow>
                        <AccordionContent asChild>
                          <tr>
                            <td colSpan={7} className="p-4 bg-gray-50">
                              <h4 className="font-semibold mb-2 text-sm">Model-wise Breakdown</h4>
                              <Table>
                                <TableHeader>
                                  <TableRow>
                                    <TableHead>Model Name</TableHead>
                                    <TableHead>Total Requests</TableHead>
                                    <TableHead>Total Tokens</TableHead>
                                    <TableHead>Total Cost</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {org.model_wise_summary.map((model: any, modelIndex: number) => (
                                    <TableRow key={modelIndex}>
                                      <TableCell>{model.model_name}</TableCell>
                                      <TableCell>{model.total_requests}</TableCell>
                                      <TableCell>{formatTokens(model.total_tokens)}</TableCell>
                                      <TableCell>${model.total_cost.toFixed(3)}</TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </td>
                          </tr>
                        </AccordionContent>
                      </>
                    </AccordionItem>
                  ))}
                </TableBody>
              </Table>
            </Accordion>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default UsageAnalytics;