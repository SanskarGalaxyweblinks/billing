import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import { Key } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import apiClient from "@/lib/api";

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [adminUsername, setAdminUsername] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();

const handleLogin = async (
    e: React.FormEvent,
    loginType: "user" | "admin"
  ) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      let response;
      if (loginType === "user") {
        const formData = new URLSearchParams();
        formData.append("username", email);
        formData.append("password", password);
        response = await apiClient.post("/login/token", formData);
      } else {
        // ... admin login logic (unchanged)
        const formData = new URLSearchParams();
        formData.append("username", adminUsername);
        formData.append("password", adminPassword);
        response = await apiClient.post("/admin/token", formData);
      }

      const { access_token } = response.data;
      localStorage.setItem("jwt_token", access_token);

      toast({
        title: "Login Successful!",
        description: "Redirecting...",
      });
      navigate(loginType === "admin" ? "/admin" : "/app");

    } catch (error: any) {
        // UPDATED ERROR HANDLING
        const detail = error.response?.data?.detail || "An unexpected error occurred.";
        if (error.response?.status === 403 && detail.includes("Email not verified")) {
             toast({
                title: "Verification Required",
                description: "Your email is not verified. Redirecting you to the verification page.",
                variant: "default",
            });
            navigate('/verify-email', { state: { email } });
        } else {
            toast({
                title: "Login Error",
                description: detail,
                variant: "destructive",
            });
        }
        console.error("Login error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <Card className="w-full max-w-md rounded-xl shadow-2xl border-gray-200">
        <CardHeader className="space-y-3 text-center">
          <div className="flex justify-center">
            <div className="p-3 bg-blue-500 rounded-full shadow-md">
              <Key className="h-8 w-8 text-white" />
            </div>
          </div>
          <CardTitle className="text-4xl font-extrabold text-gray-900">
            Welcome Back
          </CardTitle>
          <CardDescription className="text-gray-600 text-base">
            Sign in to your Jupiter Billing account
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4">
          <Tabs defaultValue="user" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="user">User Login</TabsTrigger>
              <TabsTrigger value="admin">Admin Login</TabsTrigger>
            </TabsList>
            <TabsContent value="user">
              <form
                onSubmit={(e) => handleLogin(e, "user")}
                className="space-y-6 pt-4"
              >
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <Label htmlFor="password">Password</Label>
                        <Link to="/forgot-password" className="text-sm font-medium text-blue-600 hover:underline">
                            Forgot Password?
                        </Link>
                    </div>
                  <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                </div>
                <Button
                  type="submit"
                  className="w-full h-12 text-lg font-bold"
                  disabled={isLoading}
                >
                  {isLoading ? "Signing In..." : "Sign In"}
                </Button>
                 <div className="text-center text-sm text-gray-600">
                    Don't have an account?{" "}
                    <Link to="/signup" className="font-medium text-blue-600 hover:underline">
                        Sign Up
                    </Link>
                </div>
              </form>
            </TabsContent>
            <TabsContent value="admin">
              <form
                onSubmit={(e) => handleLogin(e, "admin")}
                className="space-y-6 pt-4"
              >
                <div className="space-y-2">
                  <Label htmlFor="adminUsername">Admin Username</Label>
                  <Input
                    id="adminUsername"
                    type="text"
                    placeholder="admin"
                    value={adminUsername}
                    onChange={(e) => setAdminUsername(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="adminPassword">Password</Label>
                  <Input
                    id="adminPassword"
                    type="password"
                    placeholder="••••••••"
                    value={adminPassword}
                    onChange={(e) => setAdminPassword(e.target.value)}
                    required
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full h-12 text-lg font-bold"
                  disabled={isLoading}
                >
                  {isLoading ? "Signing In..." : "Sign In as Admin"}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

export default LoginPage;