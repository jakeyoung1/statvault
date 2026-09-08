import { useState } from "react";
import { auth } from "./api";
import Login from "./components/Login.jsx";
import DashboardLayout from "./components/DashboardLayout.jsx";

export default function App() {
  const [user, setUser] = useState(() => auth.getUser());

  function handleLogin(loggedInUser) {
    setUser(loggedInUser);
  }

  function handleLogout() {
    auth.clear();
    setUser(null);
  }

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }
  return <DashboardLayout user={user} onLogout={handleLogout} />;
}
