import React from "react";
import Navbar from "../components/Navbar.jsx";
import UploadDocument from "../components/UploadDocument.jsx";
import ChatBox from "../components/ChatBox.jsx";

const Dashboard = () => {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 p-6 max-w-5xl mx-auto">
        <UploadDocument />
        <ChatBox />
      </main>
    </div>
  );
};

export default Dashboard;

