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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ExternalLink } from "lucide-react";

interface User {
  id: number;
  organization_name: string | null;
}

// Add total_discount to the interface
interface BillingRecord {
    id: number;
    organization: string;
    year: number;
    month: number;
    total_cost: number;
    total_discount: number;
    status: string;
    generated_date: string;
    payment_due_date: string;
    paid_date: string | null;
    invoice_url: string | null;
}

const Billing = () => {
  const [selectedOrg, setSelectedOrg] = useState("all");
  const [users, setUsers] = useState<User[]>([]);
  const [billingData, setBillingData] = useState<BillingRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [billingRes, usersRes] = await Promise.all([
          apiClient.get("/admin/billing/overview"),
          apiClient.get("/admin/users"), 
        ]);
        setBillingData(billingRes.data);
        setUsers(usersRes.data);
      } catch (err) {
        console.error("Failed to fetch billing data", err);
        setError("Could not load billing information.");
      }
    };
    fetchInitialData();
  }, []);

  const organizations = useMemo(() => {
    const orgNames = new Set(users.map(user => user.organization_name).filter(Boolean));
    return Array.from(orgNames).sort();
  }, [users]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "paid":
        return "bg-green-100 text-green-800";
      case "unpaid":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const filteredData = billingData.filter(
    (item) => selectedOrg === "all" || item.organization === selectedOrg
  );

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Monthly Billing</h1>
        <p className="text-gray-600 mt-2">
          Manage billing records and payment status
        </p>
      </div>

      <Card className="border border-gray-200">
        <CardHeader>
           <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
            <CardTitle>Billing Records</CardTitle>
            <div className="flex space-x-2">
              <Select value={selectedOrg} onValueChange={setSelectedOrg}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Filter Organization" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Organizations</SelectItem>
                  {organizations.map((orgName) => (
                    <SelectItem key={orgName} value={orgName!}>
                      {orgName}
                    </SelectItem>
                  ))}
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
                  <TableHead>Organization</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Discount</TableHead>
                  <TableHead>Total Cost</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Generated</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Paid Date</TableHead>
                  <TableHead>Invoice</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredData.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium">
                      {item.organization}
                    </TableCell>
                    <TableCell>{`${item.month}/${item.year}`}</TableCell>
                    <TableCell className="text-green-600">
                      -${item.total_discount.toFixed(2)}
                    </TableCell>
                    <TableCell className="font-semibold">
                      ${item.total_cost.toFixed(2)}
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(item.status)}>
                        {item.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{item.generated_date}</TableCell>
                    <TableCell>{item.payment_due_date}</TableCell>
                    <TableCell>
                      {item.status === 'paid' ? item.paid_date : 'N/A'}
                    </TableCell>
                    <TableCell>
                      {item.invoice_url ? (
                        <Button variant="outline" size="sm" asChild>
                          <a href={item.invoice_url} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="h-4 w-4 mr-2" /> View
                          </a>
                        </Button>
                      ) : 'N/A'}
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

export default Billing;