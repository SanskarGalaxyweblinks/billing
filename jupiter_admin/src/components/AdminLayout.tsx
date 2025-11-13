
import { Outlet } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";
import { AdminTopbar } from "./AdminTopbar";

const AdminLayout = () => {
  return (
    <>
      <AppSidebar />
      <div className="flex-1 flex flex-col">
        <AdminTopbar />
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </>
  );
};

export default AdminLayout;
