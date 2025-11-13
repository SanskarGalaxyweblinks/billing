import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Gift, Calendar, Target, CheckCircle, Clock, AlertCircle, Percent, Zap } from "lucide-react";
import apiClient from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";

interface AvailableDiscount {
  id: number;
  name: string;
  description?: string;
  discount_percentage: number;
  model_name?: string;
  min_requests: number;
  max_requests?: number;
  valid_until?: string;
  validity_days?: number;
  can_enroll: boolean;
  usage_progress: number;
}

interface EnrolledDiscount {
  id: number;
  discount_rule_id: number;
  discount_name: string;
  discount_percentage: number;
  enrolled_at: string;
  valid_until?: string;
  usage_count: number;
  is_active: boolean;
}

const UserDiscountsPage = () => {
  const [availableDiscounts, setAvailableDiscounts] = useState<AvailableDiscount[]>([]);
  const [enrolledDiscounts, setEnrolledDiscounts] = useState<EnrolledDiscount[]>([]);
  const [selectedDiscount, setSelectedDiscount] = useState<AvailableDiscount | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isEnrolling, setIsEnrolling] = useState(false);
  const { toast } = useToast();

  const fetchDiscounts = async () => {
    try {
      setIsLoading(true);
      const [availableRes, enrolledRes] = await Promise.all([
        apiClient.get("/discounts/available-discounts"),
        apiClient.get("/discounts/my-discounts"),
      ]);
      setAvailableDiscounts(availableRes.data);
      setEnrolledDiscounts(enrolledRes.data);
    } catch (error: any) {
      toast({
        title: "Error",
        description: "Failed to load discounts",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleEnrollment = async (discountId: number) => {
    setIsEnrolling(true);
    try {
      await apiClient.post(`/discounts/discounts/${discountId}/enroll`);
      toast({
        title: "Success!",
        description: "You've successfully enrolled in the discount!",
      });
      setIsDialogOpen(false);
      fetchDiscounts(); // Refresh data
    } catch (error: any) {
      toast({
        title: "Enrollment Failed",
        description: error.response?.data?.detail || "Failed to enroll in discount",
        variant: "destructive"
      });
    } finally {
      setIsEnrolling(false);
    }
  };

  const openEnrollmentDialog = (discount: AvailableDiscount) => {
    setSelectedDiscount(discount);
    setIsDialogOpen(true);
  };

  const calculateProgress = (current: number, target: number) => {
    return Math.min((current / target) * 100, 100);
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "No expiry";
    return new Date(dateString).toLocaleDateString();
  };

  const getProgressColor = (progress: number, canEnroll: boolean) => {
    if (!canEnroll) return "bg-gray-400";
    if (progress >= 100) return "bg-green-500";
    if (progress >= 75) return "bg-yellow-500";
    return "bg-blue-500";
  };

  useEffect(() => {
    fetchDiscounts();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500">Loading your discounts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">My Discounts</h1>
        <p className="text-gray-600 mt-1">
          View available offers and manage your enrolled discounts
        </p>
      </div>

      {/* Available Discounts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Gift className="h-5 w-5 mr-2 text-green-500" />
            Available Offers ({availableDiscounts.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {availableDiscounts.length === 0 ? (
            <div className="text-center py-8">
              <Gift className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No offers available</h3>
              <p className="text-gray-500">Check back later for new discount opportunities!</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {availableDiscounts.map((discount) => {
                const progress = calculateProgress(discount.usage_progress, discount.min_requests);
                const isEligible = progress >= 100;
                
                return (
                  <Card key={discount.id} className={`border-2 transition-all hover:shadow-md ${
                    isEligible ? 'border-green-200 bg-green-50' : 'border-gray-200'
                  }`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 mb-1">
                            {discount.name}
                          </h3>
                          {discount.model_name && (
                            <Badge variant="outline" className="text-xs">
                              {discount.model_name}
                            </Badge>
                          )}
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-green-600">
                            {discount.discount_percentage}%
                          </div>
                          <div className="text-xs text-gray-500">OFF</div>
                        </div>
                      </div>

                      {discount.description && (
                        <p className="text-sm text-gray-600 mb-3">
                          {discount.description}
                        </p>
                      )}

                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-500">Progress</span>
                          <span className={`font-medium ${isEligible ? 'text-green-600' : 'text-gray-600'}`}>
                            {discount.usage_progress} / {discount.min_requests} requests
                          </span>
                        </div>
                        
                        <Progress 
                          value={progress} 
                          className="h-2"
                        />

                        {isEligible ? (
                          <div className="flex items-center text-sm text-green-600 mt-2">
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Eligible for discount!
                          </div>
                        ) : (
                          <div className="flex items-center text-sm text-gray-500 mt-2">
                            <Target className="h-4 w-4 mr-1" />
                            {discount.min_requests - discount.usage_progress} more requests needed
                          </div>
                        )}
                      </div>

                      <div className="mt-4">
                        <Button 
                          onClick={() => openEnrollmentDialog(discount)}
                          disabled={!discount.can_enroll || !isEligible}
                          className="w-full"
                          variant={isEligible ? "default" : "secondary"}
                        >
                          {!discount.can_enroll ? "Already Enrolled" : 
                           !isEligible ? "Not Eligible Yet" : "Enroll Now"}
                        </Button>
                      </div>

                      {discount.valid_until && (
                        <div className="flex items-center text-xs text-gray-500 mt-2">
                          <Calendar className="h-3 w-3 mr-1" />
                          Expires: {formatDate(discount.valid_until)}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Enrolled Discounts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Percent className="h-5 w-5 mr-2 text-blue-500" />
            My Active Discounts ({enrolledDiscounts.filter(d => d.is_active).length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {enrolledDiscounts.length === 0 ? (
            <div className="text-center py-8">
              <Percent className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No enrolled discounts</h3>
              <p className="text-gray-500">Enroll in available offers to start saving!</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Discount</TableHead>
                  <TableHead>Savings</TableHead>
                  <TableHead>Enrolled</TableHead>
                  <TableHead>Valid Until</TableHead>
                  <TableHead>Usage</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {enrolledDiscounts.map((discount) => (
                  <TableRow key={discount.id}>
                    <TableCell>
                      <div className="font-medium">{discount.discount_name}</div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center">
                        <Badge variant="secondary" className="text-green-600">
                          {discount.discount_percentage}% OFF
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>{formatDate(discount.enrolled_at)}</TableCell>
                    <TableCell>
                      <div className="flex items-center">
                        <Calendar className="h-4 w-4 mr-1 text-gray-400" />
                        {formatDate(discount.valid_until)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center">
                        <Zap className="h-4 w-4 mr-1 text-blue-400" />
                        {discount.usage_count} times
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={discount.is_active ? "default" : "secondary"}>
                        {discount.is_active ? "Active" : "Expired"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Enrollment Confirmation Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center">
              <Gift className="h-5 w-5 mr-2 text-green-500" />
              Enroll in Discount
            </DialogTitle>
            <DialogDescription>
              Confirm your enrollment in this discount offer
            </DialogDescription>
          </DialogHeader>
          
          {selectedDiscount && (
            <div className="py-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-green-900">{selectedDiscount.name}</h3>
                  <div className="text-2xl font-bold text-green-600">
                    {selectedDiscount.discount_percentage}% OFF
                  </div>
                </div>
                {selectedDiscount.description && (
                  <p className="text-sm text-green-700 mb-2">{selectedDiscount.description}</p>
                )}
                {selectedDiscount.model_name && (
                  <Badge variant="outline" className="text-green-700">
                    {selectedDiscount.model_name}
                  </Badge>
                )}
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Your Progress:</span>
                  <span className="font-medium">
                    {selectedDiscount.usage_progress} / {selectedDiscount.min_requests} requests
                  </span>
                </div>
                {selectedDiscount.validity_days && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Valid For:</span>
                    <span className="font-medium">{selectedDiscount.validity_days} days</span>
                  </div>
                )}
                {selectedDiscount.valid_until && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Expires:</span>
                    <span className="font-medium">{formatDate(selectedDiscount.valid_until)}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button 
              onClick={() => selectedDiscount && handleEnrollment(selectedDiscount.id)}
              disabled={isEnrolling}
              className="bg-green-600 hover:bg-green-700"
            >
              {isEnrolling ? "Enrolling..." : "Enroll Now"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default UserDiscountsPage;