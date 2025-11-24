import React from "react";
import { Outlet } from "react-router-dom";
import Navbar from "../components/Navbar";
import CatalogLoader from "../components/CatalogLoader";


export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <CatalogLoader path="/test-schedule.csv" />
      <Navbar />
      <Outlet /> 
    </div>
  );
}
