import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { initializeEnhancements } from "./enhancements";
import "./styles.css";
import "./polish.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

initializeEnhancements();
