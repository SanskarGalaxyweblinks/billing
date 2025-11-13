import { useEffect, useState } from "react";
import apiClient from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

interface UserProfile {
    full_name: string;
    email: string;
    organization_name: string;
    subscription_tier_name: string;
}

const ProfileSettingsPage = () => {
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                setLoading(true);
                const response = await apiClient.get("/users/me");
                setProfile(response.data);
            } catch (error) {
                console.error("Failed to fetch profile", error);
            } finally {
                setLoading(false);
            }
        };
        fetchProfile();
    }, []);

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Profile & Settings</h1>
                <p className="text-gray-600 mt-1">View your account and organization details.</p>
            </div>
            <Card className="max-w-2xl">
                <CardHeader>
                    <CardTitle>Your Information</CardTitle>
                    <CardDescription>This information is managed by your organization.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {loading ? (
                        <>
                            <Skeleton className="h-8 w-1/3" />
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-8 w-1/3" />
                            <Skeleton className="h-10 w-full" />
                        </>
                    ) : (
                        <>
                            <div className="space-y-1">
                                <Label>Full Name</Label>
                                <Input value={profile?.full_name} readOnly />
                            </div>
                             <div className="space-y-1">
                                <Label>Email</Label>
                                <Input value={profile?.email} readOnly />
                            </div>
                            <div className="space-y-1">
                                <Label>Organization</Label>
                                <Input value={profile?.organization_name} readOnly />
                            </div>
                             <div className="space-y-1">
                                <Label>Subscription Plan</Label>
                                <Input value={profile?.subscription_tier_name || 'N/A'} readOnly />
                            </div>
                        </>
                    )}
                </CardContent>
            </Card>
        </div>
    );
};

export default ProfileSettingsPage;