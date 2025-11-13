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
import { AlertCircle, ChevronDown } from "lucide-react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";

interface MonthlyUsage {
    month: string;
    total_requests: number;
    total_cost: number;
    total_tokens: number;
    success_rate: number;
    model_wise_summary: any[];
}

const UserUsagePage = () => {
    const [usageData, setUsageData] = useState<MonthlyUsage[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchUsage = async () => {
            try {
                setLoading(true);
                const response = await apiClient.get("/usage");
                setUsageData(response.data);
            } catch (err: any) {
                setError(err.response?.data?.detail || "Failed to fetch usage data.");
            } finally {
                setLoading(false);
            }
        };
        fetchUsage();
    }, []);

    const formatTokens = (tokens: number) => {
        if (tokens >= 1_000_000) {
            return `${(tokens / 1_000_000).toFixed(1)}M`;
        } else if (tokens >= 1000) {
            return `${(tokens / 1000).toFixed(1)}K`;
        }
        return tokens.toString();
    };

    if (loading) return <div>Loading usage history...</div>;

    if (error) return (
        <div className="flex flex-col items-center justify-center text-red-600 bg-red-50 p-6 rounded-lg">
            <AlertCircle className="h-12 w-12 mb-4" />
            <h2 className="text-xl font-semibold">Could not load usage data</h2>
            <p>{error}</p>
      </div>
    );

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Usage History</h1>
                <p className="text-gray-600 mt-1">Your monthly API usage summary.</p>
            </div>
            <Card>
                <CardHeader>
                    <CardTitle>Monthly Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Month</TableHead>
                                    <TableHead>Requests</TableHead>
                                    <TableHead>Tokens</TableHead>
                                    <TableHead>Success Rate</TableHead>
                                    <TableHead>Cost</TableHead>
                                    <TableHead className="text-right w-[100px]">Breakdown</TableHead>
                                </TableRow>
                            </TableHeader>

                            <Accordion type="single" collapsible asChild>
                                <TableBody>
                                    {usageData.map((row) => (
                                        <AccordionItem value={row.month} key={row.month} asChild>
                                            <>
                                                <TableRow>
                                                    <TableCell className="font-medium">{row.month}</TableCell>
                                                    <TableCell>{row.total_requests.toLocaleString()}</TableCell>
                                                    <TableCell>{formatTokens(row.total_tokens)}</TableCell>
                                                    <TableCell>{(row.success_rate * 100).toFixed(2)}%</TableCell>
                                                    <TableCell>${row.total_cost.toFixed(4)}</TableCell>
                                                    <TableCell className="text-right">
                                                        <AccordionTrigger>
                                                            <ChevronDown className="h-4 w-4" />
                                                        </AccordionTrigger>
                                                    </TableCell>
                                                </TableRow>
                                                <AccordionContent asChild>
                                                    <tr>
                                                        <td colSpan={7} className="p-4 bg-gray-50">
                                                            <h4 className="font-semibold mb-2 text-sm">Model-wise Breakdown for {row.month}</h4>
                                                            <Table>
                                                                <TableHeader>
                                                                    <TableRow>
                                                                        <TableHead>Model Name</TableHead>
                                                                        <TableHead>Requests</TableHead>
                                                                        <TableHead>Tokens</TableHead>
                                                                        <TableHead className="text-right">Cost</TableHead>
                                                                    </TableRow>
                                                                </TableHeader>
                                                                <TableBody>
                                                                    {row.model_wise_summary.map((model, index) => (
                                                                        <TableRow key={index}>
                                                                            <TableCell>{model.model_name}</TableCell>
                                                                            <TableCell>{model.total_requests.toLocaleString()}</TableCell>
                                                                            <TableCell>{formatTokens(model.total_tokens)}</TableCell>
                                                                            <TableCell className="text-right">${model.total_cost.toFixed(4)}</TableCell>
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
                            </Accordion>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default UserUsagePage;