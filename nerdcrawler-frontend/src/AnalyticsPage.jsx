"use client"

import { useState, useEffect } from "react"
import { AuroraText } from "./components/magicui/aurora-text"
import { useAuth } from "./auth/AuthContext"
import "./index.css"

export default function AnalyticsPage() {
  const { user, isAuthenticated } = useAuth()
  const [analyticsData, setAnalyticsData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedTab, setSelectedTab] = useState("overview")
  const [searchQueryPeriod, setSearchQueryPeriod] = useState("7d")
  const [visitorFilters, setVisitorFilters] = useState({
    ipAddress: "",
    username: "",
    pagePath: "",
    location: "",
    deviceType: "",
    browser: "",
    dateFrom: "",
    dateTo: "",
  })

  // Remove the mock data functions and replace with real data fetching
  const [visitorTrendData, setVisitorTrendData] = useState({ days: [], visitors: [] })
  const [searchTrendData, setSearchTrendData] = useState({ labels: [], values: [] })
  const [combinedTrendData, setCombinedTrendData] = useState({ days: [], visitors: [], searches: [] })
  const [chartsLoading, setChartsLoading] = useState(false)

  // Add this function to fetch chart data
  const fetchChartData = async () => {
    try {
      setChartsLoading(true)
      const token = localStorage.getItem("authToken")
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      }

      // Fetch visitor trends
      const visitorResponse = await fetch("https://projectkryptos.xyz/api/analytics/visitor-trends?days=7", {
        headers,
      })
      if (visitorResponse.ok) {
        const visitorData = await visitorResponse.json()
        setVisitorTrendData(visitorData)
      }

      // Fetch search trends
      const searchResponse = await fetch(
        `https://projectkryptos.xyz/api/analytics/search-trends?period=${searchQueryPeriod}`,
        {
          headers,
        },
      )
      if (searchResponse.ok) {
        const searchData = await searchResponse.json()
        setSearchTrendData(searchData)
      }

      // Fetch combined trends
      const combinedResponse = await fetch("https://projectkryptos.xyz/api/analytics/combined-trends?days=7", {
        headers,
      })
      if (combinedResponse.ok) {
        const combinedData = await combinedResponse.json()
        setCombinedTrendData(combinedData)
      }
    } catch (error) {
      console.error("Error fetching chart data:", error)
    } finally {
      setChartsLoading(false)
    }
  }

  // Update the useEffect to fetch chart data
  useEffect(() => {
    if (!isAuthenticated || user?.privilege_level !== "godmode") {
      window.history.pushState({}, "", "/")
      window.dispatchEvent(new PopStateEvent("popstate"))
      return
    }

    fetchAnalytics()
    fetchChartData()
  }, [isAuthenticated, user])

  // Add effect to refetch search data when period changes
  useEffect(() => {
    if (isAuthenticated && user?.privilege_level === "godmode") {
      fetchChartData()
    }
  }, [searchQueryPeriod])

  const fetchAnalytics = async () => {
    try {
      setIsLoading(true)
      const token = localStorage.getItem("authToken")

      const response = await fetch("https://projectkryptos.xyz/api/analytics/dashboard", {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      })

      if (response.ok) {
        const data = await response.json()
        setAnalyticsData(data)
      } else {
        setError("Failed to fetch analytics data")
      }
    } catch (error) {
      console.error("Error fetching analytics:", error)
      setError("Network error occurred")
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoHome = () => {
    window.history.pushState({}, "", "/")
    window.dispatchEvent(new PopStateEvent("popstate"))
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString()
  }

  const getCountryFlag = (country) => {
    const flags = {
      "United States": "🇺🇸",
      "United Kingdom": "🇬🇧",
      Canada: "🇨🇦",
      Germany: "🇩🇪",
      France: "🇫🇷",
      Japan: "🇯🇵",
      Australia: "🇦🇺",
      Brazil: "🇧🇷",
      India: "🇮🇳",
      China: "🇨🇳",
      Local: "🏠",
      Unknown: "🌍",
    }
    return flags[country] || "🌍"
  }

  const getBrowserIcon = (browser) => {
    const icons = {
      Chrome: "🌐",
      Firefox: "🦊",
      Safari: "🧭",
      Edge: "🔷",
      Opera: "🎭",
    }
    return icons[browser] || "🌐"
  }

  // Simple line chart component
  const LineChart = ({ data, title, color = "#4fc3f7", height = 200 }) => {
    const { labels, values } = data
    const maxValue = Math.max(...values)
    const minValue = Math.min(...values)
    const range = maxValue - minValue || 1

    const points = values
      .map((value, index) => {
        const x = (index / (values.length - 1)) * 100
        const y = 100 - ((value - minValue) / range) * 80 - 10
        return `${x},${y}`
      })
      .join(" ")

    return (
      <div
        style={{
          background: "rgba(20, 20, 20, 0.8)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          borderRadius: "12px",
          padding: "1.5rem",
        }}
      >
        <h3 style={{ margin: "0 0 1rem", color: color }}>{title}</h3>
        <div style={{ position: "relative", height: `${height}px` }}>
          <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">
            {/* Grid lines */}
            {[0, 25, 50, 75, 100].map((y) => (
              <line key={y} x1="0" y1={y} x2="100" y2={y} stroke="rgba(255, 255, 255, 0.1)" strokeWidth="0.2" />
            ))}

            {/* Area under curve */}
            <polygon points={`0,100 ${points} 100,100`} fill={`${color}20`} stroke="none" />

            {/* Line */}
            <polyline
              points={points}
              fill="none"
              stroke={color}
              strokeWidth="0.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Data points */}
            {values.map((value, index) => {
              const x = (index / (values.length - 1)) * 100
              const y = 100 - ((value - minValue) / range) * 80 - 10
              return <circle key={index} cx={x} cy={y} r="0.8" fill={color} stroke="#fff" strokeWidth="0.3" />
            })}
          </svg>

          {/* Labels */}
          <div
            style={{
              position: "absolute",
              bottom: "-25px",
              left: 0,
              right: 0,
              display: "flex",
              justifyContent: "space-between",
              fontSize: "0.7rem",
              color: "#888",
            }}
          >
            {labels.map((label, index) => (
              <span key={index}>{label}</span>
            ))}
          </div>

          {/* Values on hover */}
          <div
            style={{
              position: "absolute",
              top: "-25px",
              right: 0,
              fontSize: "0.8rem",
              color: color,
              fontWeight: "600",
            }}
          >
            Max: {maxValue.toLocaleString()}
          </div>
        </div>
      </div>
    )
  }

  const filterVisitors = (visitors) => {
    if (!visitors) return []

    return visitors.filter((visit) => {
      const matchesIP =
        !visitorFilters.ipAddress || visit.ip_address.toLowerCase().includes(visitorFilters.ipAddress.toLowerCase())

      const matchesUsername =
        !visitorFilters.username || visit.username.toLowerCase().includes(visitorFilters.username.toLowerCase())

      const matchesPage =
        !visitorFilters.pagePath || visit.page_path.toLowerCase().includes(visitorFilters.pagePath.toLowerCase())

      const matchesLocation =
        !visitorFilters.location || visit.location.toLowerCase().includes(visitorFilters.location.toLowerCase())

      const matchesDevice =
        !visitorFilters.deviceType || visit.device_type.toLowerCase().includes(visitorFilters.deviceType.toLowerCase())

      const matchesBrowser =
        !visitorFilters.browser || visit.browser.toLowerCase().includes(visitorFilters.browser.toLowerCase())

      const visitDate = new Date(visit.visit_time)
      const matchesDateFrom = !visitorFilters.dateFrom || visitDate >= new Date(visitorFilters.dateFrom)

      const matchesDateTo = !visitorFilters.dateTo || visitDate <= new Date(visitorFilters.dateTo + "T23:59:59")

      return (
        matchesIP &&
        matchesUsername &&
        matchesPage &&
        matchesLocation &&
        matchesDevice &&
        matchesBrowser &&
        matchesDateFrom &&
        matchesDateTo
      )
    })
  }

  const clearFilters = () => {
    setVisitorFilters({
      ipAddress: "",
      username: "",
      pagePath: "",
      location: "",
      deviceType: "",
      browser: "",
      dateFrom: "",
      dateTo: "",
    })
  }

  const updateFilter = (key, value) => {
    setVisitorFilters((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  if (!isAuthenticated || user?.privilege_level !== "godmode") {
    return null
  }

  return (
    <div
      className="analytics-page"
      style={{
        minHeight: "100vh",
        background: "#0f0f0f",
        color: "#fff",
        padding: "2rem",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "3rem",
          borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
          paddingBottom: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "2rem" }}>
          <button
            onClick={handleGoHome}
            style={{
              background: "none",
              border: "none",
              color: "#4fc3f7",
              fontSize: "1.5rem",
              cursor: "pointer",
              textDecoration: "none",
            }}
          >
            <span style={{ color: "#4285f4", fontWeight: "600" }}>Nerd</span>
            <AuroraText style={{ color: "#4fc3f7", fontWeight: "500" }}>Crawler</AuroraText>
          </button>
          <h1 style={{ margin: 0, fontSize: "2rem", fontWeight: "600" }}>📊 Site Analytics</h1>
          <div
            style={{
              background: "rgba(255, 215, 0, 0.1)",
              border: "1px solid #ffd700",
              color: "#ffd700",
              padding: "0.25rem 0.75rem",
              borderRadius: "12px",
              fontSize: "0.8rem",
              fontWeight: "600",
            }}
          >
            GODMODE
          </div>
        </div>
        <button
          onClick={handleGoHome}
          style={{
            background: "rgba(79, 195, 247, 0.1)",
            border: "1px solid #4fc3f7",
            color: "#4fc3f7",
            padding: "0.5rem 1rem",
            borderRadius: "8px",
            cursor: "pointer",
            fontSize: "0.9rem",
          }}
        >
          ← Back to Search
        </button>
      </div>

      {isLoading ? (
        <div style={{ textAlign: "center", padding: "4rem" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              border: "3px solid rgba(79, 195, 247, 0.3)",
              borderTop: "3px solid #4fc3f7",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
              margin: "0 auto 1rem",
            }}
          ></div>
          <p>Loading analytics data...</p>
        </div>
      ) : error ? (
        <div
          style={{
            textAlign: "center",
            padding: "4rem",
            background: "rgba(255, 68, 68, 0.1)",
            border: "1px solid #ff4444",
            borderRadius: "12px",
          }}
        >
          <p style={{ color: "#ff4444", fontSize: "1.2rem" }}>❌ {error}</p>
          <button
            onClick={fetchAnalytics}
            style={{
              background: "#ff4444",
              border: "none",
              color: "#fff",
              padding: "0.75rem 1.5rem",
              borderRadius: "8px",
              cursor: "pointer",
              marginTop: "1rem",
            }}
          >
            Retry
          </button>
        </div>
      ) : (
        <div style={{ maxWidth: "1400px", margin: "0 auto" }}>
          {/* Tabs */}
          <div
            style={{
              display: "flex",
              gap: "1rem",
              marginBottom: "2rem",
              borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
            }}
          >
            {[
              { id: "overview", label: "📊 Overview", icon: "📊" },
              { id: "charts", label: "📈 Charts", icon: "📈" },
              { id: "visitors", label: "👥 Visitors", icon: "👥" },
              { id: "locations", label: "🌍 Locations", icon: "🌍" },
              { id: "technology", label: "💻 Technology", icon: "💻" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedTab(tab.id)}
                style={{
                  background: selectedTab === tab.id ? "rgba(79, 195, 247, 0.2)" : "none",
                  border: selectedTab === tab.id ? "1px solid #4fc3f7" : "1px solid transparent",
                  color: selectedTab === tab.id ? "#4fc3f7" : "#ccc",
                  padding: "0.75rem 1.5rem",
                  borderRadius: "8px 8px 0 0",
                  cursor: "pointer",
                  fontSize: "0.9rem",
                  fontWeight: "500",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Overview Tab */}
          {selectedTab === "overview" && (
            <>
              {/* Stats Cards */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                  gap: "1.5rem",
                  marginBottom: "3rem",
                }}
              >
                <div
                  style={{
                    background: "rgba(79, 195, 247, 0.1)",
                    border: "1px solid rgba(79, 195, 247, 0.3)",
                    borderRadius: "12px",
                    padding: "1.5rem",
                    textAlign: "center",
                  }}
                >
                  <h3 style={{ margin: "0 0 0.5rem", color: "#4fc3f7", fontSize: "0.9rem" }}>Daily Visits</h3>
                  <p style={{ fontSize: "2rem", fontWeight: "bold", margin: 0 }}>
                    {analyticsData?.stats?.daily?.total_visits || 0}
                  </p>
                </div>
                <div
                  style={{
                    background: "rgba(76, 175, 80, 0.1)",
                    border: "1px solid rgba(76, 175, 80, 0.3)",
                    borderRadius: "12px",
                    padding: "1.5rem",
                    textAlign: "center",
                  }}
                >
                  <h3 style={{ margin: "0 0 0.5rem", color: "#4caf50", fontSize: "0.9rem" }}>Unique Visitors</h3>
                  <p style={{ fontSize: "2rem", fontWeight: "bold", margin: 0 }}>
                    {analyticsData?.stats?.daily?.unique_visitors || 0}
                  </p>
                </div>
                <div
                  style={{
                    background: "rgba(255, 152, 0, 0.1)",
                    border: "1px solid rgba(255, 152, 0, 0.3)",
                    borderRadius: "12px",
                    padding: "1.5rem",
                    textAlign: "center",
                  }}
                >
                  <h3 style={{ margin: "0 0 0.5rem", color: "#ff9800", fontSize: "0.9rem" }}>Weekly Visits</h3>
                  <p style={{ fontSize: "2rem", fontWeight: "bold", margin: 0 }}>
                    {analyticsData?.stats?.weekly?.total_visits || 0}
                  </p>
                </div>
                <div
                  style={{
                    background: "rgba(156, 39, 176, 0.1)",
                    border: "1px solid rgba(156, 39, 176, 0.3)",
                    borderRadius: "12px",
                    padding: "1.5rem",
                    textAlign: "center",
                  }}
                >
                  <h3 style={{ margin: "0 0 0.5rem", color: "#9c27b0", fontSize: "0.9rem" }}>Registered Users</h3>
                  <p style={{ fontSize: "2rem", fontWeight: "bold", margin: 0 }}>
                    {analyticsData?.stats?.daily?.registered_users || 0}
                  </p>
                </div>
              </div>

              {/* Top Pages */}
              <div
                style={{
                  background: "rgba(20, 20, 20, 0.8)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  borderRadius: "12px",
                  padding: "1.5rem",
                  marginBottom: "2rem",
                }}
              >
                <h3 style={{ margin: "0 0 1rem", color: "#4fc3f7" }}>📄 Top Pages (Last 7 Days)</h3>
                <div style={{ display: "grid", gap: "0.5rem" }}>
                  {analyticsData?.top_pages?.slice(0, 5).map((page, index) => (
                    <div
                      key={index}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "0.75rem",
                        background: "rgba(255, 255, 255, 0.05)",
                        borderRadius: "8px",
                      }}
                    >
                      <span style={{ color: "#ccc" }}>{page.page}</span>
                      <span style={{ color: "#4fc3f7", fontWeight: "600" }}>{page.visits} visits</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Charts Tab */}
          {selectedTab === "charts" && (
            <>
              {chartsLoading ? (
                <div style={{ textAlign: "center", padding: "4rem" }}>
                  <div
                    style={{
                      width: "40px",
                      height: "40px",
                      border: "3px solid rgba(79, 195, 247, 0.3)",
                      borderTop: "3px solid #4fc3f7",
                      borderRadius: "50%",
                      animation: "spin 1s linear infinite",
                      margin: "0 auto 1rem",
                    }}
                  ></div>
                  <p>Loading chart data...</p>
                </div>
              ) : (
                <>
                  {/* Visitor Trend Chart */}
                  <div style={{ marginBottom: "3rem" }}>
                    <LineChart
                      data={{
                        labels: visitorTrendData.days,
                        values: visitorTrendData.visitors,
                      }}
                      title="👥 Daily Visitors (Last 7 Days)"
                      color="#4fc3f7"
                      height={250}
                    />
                  </div>

                  {/* Search Queries Chart */}
                  <div>
                    <div
                      style={{
                        background: "rgba(20, 20, 20, 0.8)",
                        border: "1px solid rgba(255, 255, 255, 0.1)",
                        borderRadius: "12px",
                        padding: "1.5rem",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          marginBottom: "1rem",
                        }}
                      >
                        <h3 style={{ margin: 0, color: "#4caf50" }}>🔍 Search Queries</h3>
                        <div style={{ display: "flex", gap: "0.5rem" }}>
                          {[
                            { value: "1d", label: "24h" },
                            { value: "7d", label: "7d" },
                            { value: "30d", label: "30d" },
                            { value: "90d", label: "90d" },
                          ].map((period) => (
                            <button
                              key={period.value}
                              onClick={() => setSearchQueryPeriod(period.value)}
                              style={{
                                background: searchQueryPeriod === period.value ? "#4caf50" : "rgba(255, 255, 255, 0.1)",
                                border: "1px solid rgba(255, 255, 255, 0.2)",
                                color: searchQueryPeriod === period.value ? "#fff" : "#ccc",
                                padding: "0.25rem 0.75rem",
                                borderRadius: "4px",
                                cursor: "pointer",
                                fontSize: "0.8rem",
                              }}
                            >
                              {period.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div style={{ position: "relative", height: "250px" }}>
                        <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">
                          {/* Grid lines */}
                          {[0, 25, 50, 75, 100].map((y) => (
                            <line
                              key={y}
                              x1="0"
                              y1={y}
                              x2="100"
                              y2={y}
                              stroke="rgba(255, 255, 255, 0.1)"
                              strokeWidth="0.2"
                            />
                          ))}

                          {/* Bar chart */}
                          {searchTrendData.values.map((value, index) => {
                            const maxValue = Math.max(...searchTrendData.values) || 1
                            const barWidth = 80 / searchTrendData.values.length
                            const barHeight = (value / maxValue) * 80
                            const x = 10 + index * (80 / searchTrendData.values.length)
                            const y = 90 - barHeight

                            return (
                              <rect
                                key={index}
                                x={x}
                                y={y}
                                width={barWidth * 0.8}
                                height={barHeight}
                                fill="#4caf50"
                                opacity="0.8"
                                rx="0.5"
                              />
                            )
                          })}
                        </svg>

                        {/* Labels */}
                        <div
                          style={{
                            position: "absolute",
                            bottom: "-25px",
                            left: 0,
                            right: 0,
                            display: "flex",
                            justifyContent: "space-around",
                            fontSize: "0.7rem",
                            color: "#888",
                            paddingLeft: "10%",
                            paddingRight: "10%",
                          }}
                        >
                          {searchTrendData.labels.map((label, index) => (
                            <span key={index}>{label}</span>
                          ))}
                        </div>

                        {/* Max value indicator */}
                        <div
                          style={{
                            position: "absolute",
                            top: "-25px",
                            right: 0,
                            fontSize: "0.8rem",
                            color: "#4caf50",
                            fontWeight: "600",
                          }}
                        >
                          Peak: {Math.max(...searchTrendData.values).toLocaleString()} queries
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Combined trend chart */}
                  <div style={{ marginTop: "3rem" }}>
                    <div
                      style={{
                        background: "rgba(20, 20, 20, 0.8)",
                        border: "1px solid rgba(255, 255, 255, 0.1)",
                        borderRadius: "12px",
                        padding: "1.5rem",
                      }}
                    >
                      <h3 style={{ margin: "0 0 1rem", color: "#ff9800" }}>📊 Combined Trends (Last 7 Days)</h3>
                      <div style={{ position: "relative", height: "250px" }}>
                        <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">
                          {/* Grid lines */}
                          {[0, 25, 50, 75, 100].map((y) => (
                            <line
                              key={y}
                              x1="0"
                              y1={y}
                              x2="100"
                              y2={y}
                              stroke="rgba(255, 255, 255, 0.1)"
                              strokeWidth="0.2"
                            />
                          ))}

                          {/* Visitors line */}
                          {combinedTrendData.visitors.length > 0 &&
                            (() => {
                              const maxVisitors = Math.max(...combinedTrendData.visitors) || 1
                              const minVisitors = Math.min(...combinedTrendData.visitors) || 0
                              const rangeVisitors = maxVisitors - minVisitors || 1

                              const visitorPoints = combinedTrendData.visitors
                                .map((value, index) => {
                                  const x = (index / (combinedTrendData.visitors.length - 1)) * 100
                                  const y = 100 - ((value - minVisitors) / rangeVisitors) * 80 - 10
                                  return `${x},${y}`
                                })
                                .join(" ")

                              return (
                                <>
                                  <polyline
                                    points={visitorPoints}
                                    fill="none"
                                    stroke="#4fc3f7"
                                    strokeWidth="1"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                  />
                                  {combinedTrendData.visitors.map((value, index) => {
                                    const x = (index / (combinedTrendData.visitors.length - 1)) * 100
                                    const y = 100 - ((value - minVisitors) / rangeVisitors) * 80 - 10
                                    return <circle key={`visitor-${index}`} cx={x} cy={y} r="1" fill="#4fc3f7" />
                                  })}
                                </>
                              )
                            })()}

                          {/* Searches line */}
                          {combinedTrendData.searches.length > 0 &&
                            (() => {
                              const maxSearches = Math.max(...combinedTrendData.searches) || 1
                              const minSearches = Math.min(...combinedTrendData.searches) || 0
                              const rangeSearches = maxSearches - minSearches || 1

                              const searchPoints = combinedTrendData.searches
                                .map((value, index) => {
                                  const x = (index / (combinedTrendData.searches.length - 1)) * 100
                                  const y = 100 - ((value - minSearches) / rangeSearches) * 80 - 10
                                  return `${x},${y}`
                                })
                                .join(" ")

                              return (
                                <>
                                  <polyline
                                    points={searchPoints}
                                    fill="none"
                                    stroke="#4caf50"
                                    strokeWidth="1"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeDasharray="2,2"
                                  />
                                  {combinedTrendData.searches.map((value, index) => {
                                    const x = (index / (combinedTrendData.searches.length - 1)) * 100
                                    const y = 100 - ((value - minSearches) / rangeSearches) * 80 - 10
                                    return <circle key={`search-${index}`} cx={x} cy={y} r="1" fill="#4caf50" />
                                  })}
                                </>
                              )
                            })()}
                        </svg>

                        {/* Legend */}
                        <div
                          style={{
                            position: "absolute",
                            top: "10px",
                            right: "10px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "0.5rem",
                            fontSize: "0.7rem",
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                            <div style={{ width: "12px", height: "2px", background: "#4fc3f7" }}></div>
                            <span style={{ color: "#4fc3f7" }}>Visitors</span>
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                            <div
                              style={{
                                width: "12px",
                                height: "2px",
                                background: "#4caf50",
                                borderTop: "1px dashed #4caf50",
                              }}
                            ></div>
                            <span style={{ color: "#4caf50" }}>Searches</span>
                          </div>
                        </div>

                        {/* Labels */}
                        <div
                          style={{
                            position: "absolute",
                            bottom: "-25px",
                            left: 0,
                            right: 0,
                            display: "flex",
                            justifyContent: "space-between",
                            fontSize: "0.7rem",
                            color: "#888",
                          }}
                        >
                          {combinedTrendData.days.map((day, index) => (
                            <span key={index}>{day}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          {/* Visitors Tab */}
          {selectedTab === "visitors" && (
            <div
              style={{
                background: "rgba(20, 20, 20, 0.8)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                borderRadius: "12px",
                padding: "1.5rem",
              }}
            >
              <div
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}
              >
                <h3 style={{ margin: 0, color: "#4fc3f7" }}>👥 All Visitors</h3>
                <div style={{ color: "#888", fontSize: "0.9rem" }}>
                  Showing {filterVisitors(analyticsData?.recent_visits).length} of{" "}
                  {analyticsData?.recent_visits?.length || 0} visitors
                </div>
              </div>

              {/* Filter Controls */}
              <div
                style={{
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  borderRadius: "8px",
                  padding: "1rem",
                  marginBottom: "1rem",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "1rem",
                  }}
                >
                  <h4 style={{ margin: 0, color: "#4fc3f7", fontSize: "0.9rem" }}>🔍 Filter Visitors</h4>
                  <button
                    onClick={clearFilters}
                    style={{
                      background: "rgba(255, 68, 68, 0.2)",
                      border: "1px solid #ff4444",
                      color: "#ff4444",
                      padding: "0.25rem 0.75rem",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "0.8rem",
                    }}
                  >
                    Clear All
                  </button>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                    gap: "1rem",
                  }}
                >
                  <div>
                    <label style={{ color: "#ccc", fontSize: "0.8rem", display: "block", marginBottom: "0.25rem" }}>
                      IP Address
                    </label>
                    <input
                      type="text"
                      placeholder="Filter by IP..."
                      value={visitorFilters.ipAddress}
                      onChange={(e) => updateFilter("ipAddress", e.target.value)}
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "rgba(255, 255, 255, 0.1)",
                        border: "1px solid rgba(255, 255, 255, 0.2)",
                        borderRadius: "4px",
                        color: "#fff",
                        fontSize: "0.8rem",
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ color: "#ccc", fontSize: "0.8rem", display: "block", marginBottom: "0.25rem" }}>
                      Username
                    </label>
                    <input
                      type="text"
                      placeholder="Filter by user..."
                      value={visitorFilters.username}
                      onChange={(e) => updateFilter("username", e.target.value)}
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "rgba(255, 255, 255, 0.1)",
                        border: "1px solid rgba(255, 255, 255, 0.2)",
                        borderRadius: "4px",
                        color: "#fff",
                        fontSize: "0.8rem",
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ color: "#ccc", fontSize: "0.8rem", display: "block", marginBottom: "0.25rem" }}>
                      Page Path
                    </label>
                    <input
                      type="text"
                      placeholder="Filter by page..."
                      value={visitorFilters.pagePath}
                      onChange={(e) => updateFilter("pagePath", e.target.value)}
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "rgba(255, 255, 255, 0.1)",
                        border: "1px solid rgba(255, 255, 255, 0.2)",
                        borderRadius: "4px",
                        color: "#fff",
                        fontSize: "0.8rem",
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ color: "#ccc", fontSize: "0.8rem", display: "block", marginBottom: "0.25rem" }}>
                      Location
                    </label>
                    <input
                      type="text"
                      placeholder="Filter by location..."
                      value={visitorFilters.location}
                      onChange={(e) => updateFilter("location", e.target.value)}
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "rgba(255, 255, 255, 0.1)",
                        border: "1px solid rgba(255, 255, 255, 0.2)",
                        borderRadius: "4px",
                        color: "#fff",
                        fontSize: "0.8rem",
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ color: "#ccc", fontSize: "0.8rem", display: "block", marginBottom: "0.25rem" }}>
                      Device Type
                    </label>
                    <select
                      value={visitorFilters.deviceType}
                      onChange={(e) => updateFilter("deviceType", e.target.value)}
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "rgba(255, 255, 255, 0.1)",
                        border: "1px solid rgba(255, 255, 255, 0.2)",
                        borderRadius: "4px",
                        color: "#fff",
                        fontSize: "0.8rem",
                      }}
                    >
                      <option value="" style={{ background: "#333" }}>
                        All Devices
                      </option>
                      <option value="Desktop" style={{ background: "#333" }}>
                        Desktop
                      </option>
                      <option value="Mobile" style={{ background: "#333" }}>
                        Mobile
                      </option>
                      <option value="Tablet" style={{ background: "#333" }}>
                        Tablet
                      </option>
                    </select>
                  </div>

                  <div>
                    <label style={{ color: "#ccc", fontSize: "0.8rem", display: "block", marginBottom: "0.25rem" }}>
                      Browser
                    </label>
                    <input
                      type="text"
                      placeholder="Filter by browser..."
                      value={visitorFilters.browser}
                      onChange={(e) => updateFilter("browser", e.target.value)}
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "rgba(255, 255, 255, 0.1)",
                        border: "1px solid rgba(255, 255, 255, 0.2)",
                        borderRadius: "4px",
                        color: "#fff",
                        fontSize: "0.8rem",
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ color: "#ccc", fontSize: "0.8rem", display: "block", marginBottom: "0.25rem" }}>
                      Date From
                    </label>
                    <input
                      type="date"
                      value={visitorFilters.dateFrom}
                      onChange={(e) => updateFilter("dateFrom", e.target.value)}
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "rgba(255, 255, 255, 0.1)",
                        border: "1px solid rgba(255, 255, 255, 0.2)",
                        borderRadius: "4px",
                        color: "#fff",
                        fontSize: "0.8rem",
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ color: "#ccc", fontSize: "0.8rem", display: "block", marginBottom: "0.25rem" }}>
                      Date To
                    </label>
                    <input
                      type="date"
                      value={visitorFilters.dateTo}
                      onChange={(e) => updateFilter("dateTo", e.target.value)}
                      style={{
                        width: "100%",
                        padding: "0.5rem",
                        background: "rgba(255, 255, 255, 0.1)",
                        border: "1px solid rgba(255, 255, 255, 0.2)",
                        borderRadius: "4px",
                        color: "#fff",
                        fontSize: "0.8rem",
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Visitors Table */}
              <div
                style={{
                  overflowX: "auto",
                  overflowY: "auto",
                  maxHeight: "600px",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  borderRadius: "8px",
                }}
              >
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr
                      style={{
                        borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
                        position: "sticky",
                        top: 0,
                        background: "rgba(20, 20, 20, 0.95)",
                        zIndex: 1,
                      }}
                    >
                      <th style={{ padding: "0.75rem", textAlign: "left", color: "#4fc3f7" }}>IP Address</th>
                      <th style={{ padding: "0.75rem", textAlign: "left", color: "#4fc3f7" }}>User</th>
                      <th style={{ padding: "0.75rem", textAlign: "left", color: "#4fc3f7" }}>Page</th>
                      <th style={{ padding: "0.75rem", textAlign: "left", color: "#4fc3f7" }}>Location</th>
                      <th style={{ padding: "0.75rem", textAlign: "left", color: "#4fc3f7" }}>Device</th>
                      <th style={{ padding: "0.75rem", textAlign: "left", color: "#4fc3f7" }}>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filterVisitors(analyticsData?.recent_visits).map((visit, index) => (
                      <tr
                        key={visit.id}
                        style={{
                          borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                          background: index % 2 === 0 ? "rgba(255, 255, 255, 0.02)" : "transparent",
                        }}
                      >
                        <td style={{ padding: "0.75rem", color: "#ccc", fontFamily: "monospace" }}>
                          {visit.ip_address}
                        </td>
                        <td style={{ padding: "0.75rem", color: visit.username === "Anonymous" ? "#888" : "#4caf50" }}>
                          {visit.username}
                        </td>
                        <td style={{ padding: "0.75rem", color: "#ccc" }}>{visit.page_path}</td>
                        <td style={{ padding: "0.75rem", color: "#ccc" }}>{visit.location}</td>
                        <td style={{ padding: "0.75rem", color: "#ccc" }}>
                          {visit.device_type} • {visit.browser}
                        </td>
                        <td style={{ padding: "0.75rem", color: "#888", fontSize: "0.8rem" }}>
                          {formatDate(visit.visit_time)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {filterVisitors(analyticsData?.recent_visits).length === 0 && (
                  <div
                    style={{
                      textAlign: "center",
                      padding: "2rem",
                      color: "#888",
                      fontStyle: "italic",
                    }}
                  >
                    No visitors match the current filters
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Locations Tab */}
          {selectedTab === "locations" && (
            <div
              style={{
                background: "rgba(20, 20, 20, 0.8)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                borderRadius: "12px",
                padding: "1.5rem",
              }}
            >
              <h3 style={{ margin: "0 0 1rem", color: "#4fc3f7" }}>🌍 Top Countries (Last 7 Days)</h3>
              <div style={{ display: "grid", gap: "0.75rem" }}>
                {analyticsData?.top_countries?.map((country, index) => (
                  <div
                    key={index}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "1rem",
                      background: "rgba(255, 255, 255, 0.05)",
                      borderRadius: "8px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                      <span style={{ fontSize: "1.5rem" }}>{getCountryFlag(country.country)}</span>
                      <span style={{ color: "#ccc", fontSize: "1.1rem" }}>{country.country}</span>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ color: "#4fc3f7", fontWeight: "600", fontSize: "1.2rem" }}>{country.visits}</div>
                      <div style={{ color: "#888", fontSize: "0.8rem" }}>visits</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Technology Tab */}
          {selectedTab === "technology" && (
            <div
              style={{
                background: "rgba(20, 20, 20, 0.8)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                borderRadius: "12px",
                padding: "1.5rem",
              }}
            >
              <h3 style={{ margin: "0 0 1rem", color: "#4fc3f7" }}>💻 Top Browsers (Last 7 Days)</h3>
              <div style={{ display: "grid", gap: "0.75rem" }}>
                {analyticsData?.top_browsers?.map((browser, index) => (
                  <div
                    key={index}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "1rem",
                      background: "rgba(255, 255, 255, 0.05)",
                      borderRadius: "8px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                      <span style={{ fontSize: "1.5rem" }}>{getBrowserIcon(browser.browser)}</span>
                      <span style={{ color: "#ccc", fontSize: "1.1rem" }}>{browser.browser}</span>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ color: "#4fc3f7", fontWeight: "600", fontSize: "1.2rem" }}>{browser.visits}</div>
                      <div style={{ color: "#888", fontSize: "0.8rem" }}>visits</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
