"use client"

import { useState, useEffect } from "react"
import HomePage from "./HomePage"
import DashboardPage from "./DashboardPage"
import DownloadsPage from "./downloads"

export default function MainRouter() {
  const [currentRoute, setCurrentRoute] = useState("/")

  useEffect(() => {
    // Set initial route
    setCurrentRoute(window.location.pathname)

    // Listen for route changes
    const handleRouteChange = () => {
      setCurrentRoute(window.location.pathname)
    }

    window.addEventListener("popstate", handleRouteChange)

    return () => {
      window.removeEventListener("popstate", handleRouteChange)
    }
  }, [])

  // Route rendering logic
  const renderPage = () => {
    switch (currentRoute) {
      case "/":
        return <HomePage />
      case "/dashboard":
        return <DashboardPage />
      case "/downloads":
        return <DownloadsPage />
      default:
        return <HomePage />
    }
  }

  return <div className="app-container">{renderPage()}</div>
}
