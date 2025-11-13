import React, { useState, useEffect } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { useToast } from "@/components/ui/use-toast";
import apiClient from "@/lib/api";
import { MailCheck } from "lucide-react";

const VerifyEmailPage = () => {
  const [otp, setOtp] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const email = location.state?.email;

  useEffect(() => {
    if (!email) {
      // If no email is in the state, redirect to signup
      navigate("/signup");
    }
  }, [email, navigate]);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await apiClient.post("/verify-email", {
        email: email,
        token: otp,
      });
      toast({
        title: "Verification Successful!",
        description: "Your email has been verified. Please log in.",
      });
      navigate("/login");
    } catch (error: any) {
      toast({
        title: "Verification Failed",
        description: error.response?.data?.detail || "An error occurred.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleResendOtp = async () => {
    setIsResending(true);
    try {
        await apiClient.post('/resend-verification-email', { email });
        toast({
            title: "OTP Resent",
            description: "A new verification code has been sent to your email."
        });
    } catch (error: any) {
        toast({
            title: "Failed to Resend OTP",
            description: error.response?.data?.detail || "An error occurred.",
            variant: "destructive"
        })
    } finally {
        setIsResending(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center">
            <div className="p-3 bg-blue-500 rounded-full shadow-md">
                <MailCheck className="h-8 w-8 text-white" />
            </div>
          </div>
          <CardTitle className="text-3xl font-bold">Check your email</CardTitle>
          <CardDescription>
            We've sent a 6-digit code to <strong>{email}</strong>. The code expires shortly, so please enter it soon.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleVerify} className="space-y-6">
            <div className="flex justify-center">
              <InputOTP maxLength={6} value={otp} onChange={(value) => setOtp(value)}>
                <InputOTPGroup>
                  <InputOTPSlot index={0} />
                  <InputOTPSlot index={1} />
                  <InputOTPSlot index={2} />
                  <InputOTPSlot index={3} />
                  <InputOTPSlot index={4} />
                  <InputOTPSlot index={5} />
                </InputOTPGroup>
              </InputOTP>
            </div>
            <Button type="submit" className="w-full" disabled={isLoading || otp.length < 6}>
              {isLoading ? "Verifying..." : "Verify Account"}
            </Button>
          </form>
           <div className="text-center text-sm text-gray-600 mt-4">
              Didn't get a code?{" "}
              <Button variant="link" className="p-0 h-auto" onClick={handleResendOtp} disabled={isResending}>
                {isResending ? 'Sending...' : 'Click to resend'}
              </Button>
            </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default VerifyEmailPage;