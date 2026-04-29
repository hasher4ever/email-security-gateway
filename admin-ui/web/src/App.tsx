import { Routes, Route, Navigate } from "react-router-dom";
import NavBar from "./components/NavBar";
import Quarantine from "./pages/Quarantine";
import Sim from "./pages/Sim";

export default function App() {
  return (
    <>
      <NavBar />
      <main className="page">
        <Routes>
          <Route path="/" element={<Navigate to="/quarantine" replace />} />
          <Route path="/quarantine" element={<Quarantine />} />
          <Route path="/sim" element={<Sim />} />
        </Routes>
      </main>
    </>
  );
}
