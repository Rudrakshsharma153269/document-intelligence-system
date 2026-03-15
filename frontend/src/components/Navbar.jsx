import React from "react";
import { useNavigate } from "react-router-dom";

const Navbar = () => {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <nav className="bg-white shadow px-6 py-3 flex justify-between items-center">
      <div className="font-semibold text-lg">Document Intelligence</div>
      <button
        onClick={handleLogout}
        className="px-3 py-1 rounded bg-red-500 text-white text-sm hover:bg-red-600"
      >
        Logout
      </button>
    </nav>
  );
};

export default Navbar;

