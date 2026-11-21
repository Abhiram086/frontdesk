import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./auth";
import LateReport from "./pages/LateReport";
import Login from "./pages/Login";
import PortalNew from "./pages/PortalNew";
import PortalTicket from "./pages/PortalTicket";
import TicketDetail from "./pages/TicketDetail";
import Tickets from "./pages/Tickets";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/tickets" element={<RequireAuth><Tickets /></RequireAuth>} />
        <Route path="/tickets/:id" element={<RequireAuth><TicketDetail /></RequireAuth>} />
        <Route path="/manager/late" element={<RequireAuth manager><LateReport /></RequireAuth>} />
        <Route path="/portal" element={<PortalNew />} />
        <Route path="/portal/t/:token" element={<PortalTicket />} />
        <Route path="*" element={<Navigate to="/tickets" replace />} />
      </Routes>
    </BrowserRouter>
  );
}