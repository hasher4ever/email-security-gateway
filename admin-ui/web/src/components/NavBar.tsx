import { NavLink } from "react-router-dom";

export default function NavBar() {
  return (
    <nav className="nav">
      <span className="brand">Email Security Gateway</span>
      <NavLink to="/quarantine">Quarantine</NavLink>
      <NavLink to="/sim">Sim metrics</NavLink>
    </nav>
  );
}
