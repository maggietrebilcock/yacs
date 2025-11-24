import './styles/globals.css';
import reportWebVitals from './reportWebVitals';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppThemeProvider } from './components/theme/ThemeProvider';
import App from './app/App';
import HomePage from "./pages/HomePage";
import FourYearPlannerPage from "./pages/FourYearPlannerPage";
import ProfilePage from "./pages/ProfilePage";
import { ScheduleProvider } from "./context/schedule-context";

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
  <React.StrictMode>
    <AppThemeProvider>
    <ScheduleProvider>
    <BrowserRouter>
      <Routes>
      <Route path="/" element={<App />}>
        <Route index element={<HomePage />} />
        <Route path="planner" element={<FourYearPlannerPage />} />
        <Route path="profile" element={<ProfilePage />} />
      </Route>
    </Routes>
    </BrowserRouter>
    </ScheduleProvider>
    </AppThemeProvider>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
