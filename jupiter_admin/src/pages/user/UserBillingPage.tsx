import { useEffect, useState } from "react";
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
import { Badge } from "@/components/ui/badge";
import { CreditCard, AlertCircle, Loader2, ExternalLink } from "lucide-react";

interface Bill {
  id: number;
  year: number;
  month: number;
  total_cost: number;
  status: 'paid' | 'unpaid';
  created_at: string;
  paid_at?: string;
  payment_due_date?: string;
  invoice_url?: string;
}

const UserBillingPage = () => {
  const [bills, setBills] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [payingBillId, setPayingBillId] = useState<number | null>(null);

  useEffect(() => {
    const fetchBills = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get("/billing");
        setBills(response.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || "Failed to fetch billing information.");
      } finally {
        setLoading(false);
      }
    };
    fetchBills();
  }, []);

  const handlePayBill = async (billId: number) => {
    setPayingBillId(billId);
    try {
      const response = await apiClient.post("/stripe/create-checkout-session", {
        bill_id: billId,
      });
      const { checkout_url } = response.data;
      if (checkout_url) {
        window.location.href = checkout_url;
      }
    } catch (err: any) {
      console.error("Failed to create checkout session:", err);
      alert("Could not initiate payment. Please try again.");
    } finally {
      setPayingBillId(null);
    }
  };

  if (loading) return <div>Loading billing information...</div>;

  return (
    <div className="space-y-6">
       <div>
        <h1 className="text-3xl font-bold text-gray-900">Billing</h1>
        <p className="text-gray-600 mt-1">View your invoice history and pay outstanding bills.</p>
      </div>
      
      {error && (
         <div className="flex flex-col items-center justify-center text-red-600 bg-red-50 p-6 rounded-lg">
            <AlertCircle className="h-12 w-12 mb-4" />
            <h2 className="text-xl font-semibold">Could not load billing data</h2>
            <p>{error}</p>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Invoice History</CardTitle>
        </CardHeader>
        <CardContent>
          {bills.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Billing Period</TableHead>
                  <TableHead>Generated</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Paid Date</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {bills.map((bill) => (
                  <TableRow key={bill.id}>
                    <TableCell className="font-medium">{`${bill.month}/${bill.year}`}</TableCell>
                    <TableCell>{new Date(bill.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>{new Date(bill.payment_due_date || '').toLocaleDateString()}</TableCell>
                    <TableCell className="font-semibold">${bill.total_cost.toFixed(2)}</TableCell>
                    <TableCell>
                      <Badge variant={bill.status === 'paid' ? 'default' : 'destructive'} className={bill.status === 'paid' ? 'bg-green-100 text-green-800' : ''}>
                        {bill.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {bill.status === 'paid' && bill.paid_at
                        ? new Date(bill.paid_at).toLocaleDateString()
                        : 'N/A'
                      }
                    </TableCell>
                    <TableCell className="text-right">
                      {bill.status === 'paid' ? (
                        <Button variant="outline" size="sm" asChild disabled={!bill.invoice_url}>
                           <a href={bill.invoice_url} target="_blank" rel="noopener noreferrer">
                              <ExternalLink className="mr-2 h-4 w-4" /> View Invoice
                           </a>
                        </Button>
                      ) : (
                        <Button onClick={() => handlePayBill(bill.id)} disabled={payingBillId === bill.id}>
                          {payingBillId === bill.id ? (
                             <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          ) : (
                             <CreditCard className="mr-2 h-4 w-4" />
                          )}
                          {payingBillId === bill.id ? 'Redirecting...' : 'Pay Now'}
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-center text-gray-500 py-8">
              You have no invoices yet.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default UserBillingPage;