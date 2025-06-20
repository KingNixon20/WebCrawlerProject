"use client"
import "./App.css"
import { useState, useEffect } from "react"
import { AuthProvider } from "./auth/AuthContext"
import HomePage from "./HomePage"
import LoginPage from "./LoginPage"
import DashboardPage from "./DashboardPage"
import GamesPage from "./GamesPage"
import AnalyticsPage from "./AnalyticsPage"
import DownloadsPage from "./downloads"

function AppContent() {
  const [currentRoute, setCurrentRoute] = useState("")

  useEffect(() => {
    // Add Google Analytics gtag
    const addGoogleAnalytics = () => {
      // Check if gtag script is already loaded
      if (!window.gtag) {
        // Add the gtag script
        const gtagScript = document.createElement("script")
        gtagScript.async = true
        gtagScript.src = "https://www.googletagmanager.com/gtag/js?id=G-FLCSWSD2SX"
        document.head.appendChild(gtagScript)

        // Add the gtag configuration script
        const gtagConfigScript = document.createElement("script")
        gtagConfigScript.innerHTML = `
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', 'G-FLCSWSD2SX');
        `
        document.head.appendChild(gtagConfigScript)
      }
    }

    addGoogleAnalytics()

    const path = window.location.pathname
    setCurrentRoute(path)

    const handlePopState = () => {
      setCurrentRoute(window.location.pathname)
    }

    window.addEventListener("popstate", handlePopState)
    return () => window.removeEventListener("popstate", handlePopState)
  }, [])

  // Track page views when route changes
  useEffect(() => {
    if (window.gtag) {
      window.gtag("config", "G-FLCSWSD2SX", {
        page_path: currentRoute,
      })
    }
  }, [currentRoute])

  const renderCurrentPage = () => {
    console.log("Rendering page for route:", currentRoute)
    switch (currentRoute) {
      case "/login":
        return <LoginPage />
      case "/dashboard":
        return <DashboardPage />
      case "/games":
        return <GamesPage />
      case "/analytics":
        return <AnalyticsPage />
      case "/downloads":
        return <DownloadsPage />
      case "/":
      default:
        return <HomePage />
    }
  }

  return <div className="app">{renderCurrentPage()}</div>
}

export default function App() {
  console.log("App component rendering")
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
