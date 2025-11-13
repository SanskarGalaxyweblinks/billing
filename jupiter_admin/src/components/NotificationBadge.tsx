import { useEffect, useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Bell, Check, Gift, Clock, AlertCircle } from "lucide-react";
import apiClient from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";

interface Notification {
  id: number;
  title: string;
  message: string;
  notification_type: string;
  discount_rule_id?: number;
  metadata?: string;
  is_read: boolean;
  is_popup_shown: boolean;
  created_at: string;
  discount_name?: string;
  discount_percentage?: number;
}

interface NotificationBadgeProps {
  className?: string;
}

const NotificationBadge = ({ className = "" }: NotificationBadgeProps) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const fetchNotifications = async () => {
    try {
      const [notificationsRes, countRes] = await Promise.all([
        apiClient.get("/discounts/notifications"),
        apiClient.get("/discounts/notifications/unread-count"),
      ]);
      setNotifications(notificationsRes.data);
      setUnreadCount(countRes.data.unread_count);
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
    }
  };

  const markAsRead = async (notificationId: number) => {
    try {
      await apiClient.put(`/discounts/notifications/${notificationId}/mark-read`);
      setNotifications(prev => 
        prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error("Failed to mark notification as read:", error);
    }
  };

  const markAllAsRead = async () => {
    if (unreadCount === 0) return;
    
    setIsLoading(true);
    try {
      await apiClient.put("/discounts/notifications/mark-all-read");
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
      toast({ title: "Success", description: "All notifications marked as read" });
    } catch (error) {
      toast({ title: "Error", description: "Failed to mark all as read", variant: "destructive" });
    } finally {
      setIsLoading(false);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "discount":
        return <Gift className="h-4 w-4 text-green-500" />;
      case "billing":
        return <AlertCircle className="h-4 w-4 text-orange-500" />;
      default:
        return <Bell className="h-4 w-4 text-blue-500" />;
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) return "Just now";
    if (diffInHours < 24) return `${diffInHours}h ago`;
    
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) return `${diffInDays}d ago`;
    
    return date.toLocaleDateString();
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className={`relative ${className}`}
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 p-0 text-xs flex items-center justify-center"
            >
              {unreadCount > 99 ? "99+" : unreadCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 max-h-96 overflow-y-auto">
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>Notifications</span>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={markAllAsRead}
              disabled={isLoading}
              className="h-6 px-2 text-xs"
            >
              <Check className="h-3 w-3 mr-1" />
              Mark all read
            </Button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        
        {notifications.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No notifications yet</p>
          </div>
        ) : (
          <div className="max-h-72 overflow-y-auto">
            {notifications.slice(0, 10).map((notification) => (
              <DropdownMenuItem
                key={notification.id}
                className="p-0 focus:bg-transparent"
                onClick={(e) => e.preventDefault()}
              >
                <Card className={`w-full border-0 shadow-none ${!notification.is_read ? 'bg-blue-50' : ''}`}>
                  <CardContent className="p-3">
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0 mt-1">
                        {getNotificationIcon(notification.notification_type)}
                      </div>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center justify-between">
                          <h4 className={`text-sm font-medium ${!notification.is_read ? 'font-semibold' : ''}`}>
                            {notification.title}
                          </h4>
                          {!notification.is_read && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => markAsRead(notification.id)}
                              className="h-6 w-6 p-0 ml-2"
                            >
                              <Check className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 line-clamp-2">
                          {notification.message}
                        </p>
                        
                        {notification.discount_percentage && (
                          <div className="flex items-center space-x-2 pt-1">
                            <Badge variant="secondary" className="text-green-600">
                              {notification.discount_percentage}% OFF
                            </Badge>
                            {notification.discount_name && (
                              <span className="text-xs text-gray-500">
                                {notification.discount_name}
                              </span>
                            )}
                          </div>
                        )}
                        
                        <div className="flex items-center justify-between pt-1">
                          <span className="text-xs text-gray-400 flex items-center">
                            <Clock className="h-3 w-3 mr-1" />
                            {formatTimeAgo(notification.created_at)}
                          </span>
                          {!notification.is_read && (
                            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </DropdownMenuItem>
            ))}
            
            {notifications.length > 10 && (
              <DropdownMenuItem className="text-center py-2">
                <Button variant="ghost" size="sm" className="w-full">
                  View all notifications
                </Button>
              </DropdownMenuItem>
            )}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default NotificationBadge;