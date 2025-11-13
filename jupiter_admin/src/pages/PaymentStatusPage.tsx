import { useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle2, XCircle } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

const PaymentStatusPage = () => {
  const [searchParams] = useSearchParams();
  const status = searchParams.get('status');
  const { toast } = useToast();

  useEffect(() => {
    if (status === 'success') {
      toast({
        title: "Payment Successful!",
        description: "Thank you for your payment. Your invoice has been updated.",
        variant: "default",
      });
    }
  }, [status, toast]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          {status === 'success' ? (
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
              <CheckCircle2 className="h-6 w-6 text-green-600" />
            </div>
          ) : (
             <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
              <XCircle className="h-6 w-6 text-red-600" />
            </div>
          )}
          <CardTitle className="mt-4 text-2xl font-semibold">
            {status === 'success' ? 'Payment Successful' : 'Payment Canceled'}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-muted-foreground">
            {status === 'success'
              ? 'Your payment has been processed successfully. You can now return to your dashboard.'
              : 'Your payment was not completed. You can try again from the billing page.'}
          </p>
          <Button asChild className="w-full">
            <Link to="/app/billing">Return to Billing</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

export default PaymentStatusPage;