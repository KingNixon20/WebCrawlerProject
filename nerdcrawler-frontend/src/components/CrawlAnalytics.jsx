"use client"

import { useState, useEffect } from "react"

const CrawlAnalytics = () => {
  const [timeframe, setTimeframe] = useState("daily")
  const [analyticsData, setAnalyticsData] = useState(null)
  const [latestUrls, setLatestUrls] = useState([])
  const [crawlStats, setCrawlStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [urlsLoading, setUrlsLoading] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [pagination, setPagination] = useState(null)
  const [filters, setFilters] = useState({
    status: "all",
    domain: "",
    dateRange: 7, // days
  })

  useEffect(() => {
    loadAnalytics()
    loadCrawlStats()
  }, [timeframe])

  useEffect(() => {
    loadLatestUrls()
  }, [currentPage, filters])

  const loadAnalytics = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem("authToken")
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      }

      const response = await fetch(`/api/analytics/crawl-volume?timeframe=${timeframe}`, {
        headers,
      })

      if (response.ok) {
        const data = await response.json()
        setAnalyticsData(data)
      } else {
        console.error("Failed to load crawl analytics")
        setAnalyticsData(null)
      }
    } catch (error) {
      console.error("Failed to load analytics:", error)
      setAnalyticsData(null)
    } finally {
      setLoading(false)
    }
  }

  const loadLatestUrls = async () => {
    setUrlsLoading(true)
    try {
      const token = localStorage.getItem("authToken")
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      }

      const queryParams = new URLSearchParams({
        page: currentPage.toString(),
        limit: "20",
        status: filters.status !== "all" ? filters.status : "",
        domain: filters.domain,
        dateRange: filters.dateRange.toString(),
      })

      const response = await fetch(`/api/analytics/crawled-urls?${queryParams}`, { headers })

      if (response.ok) {
        const data = await response.json()
        setLatestUrls(data.urls || [])
        setPagination(data.pagination || {})
      } else {
        console.error("Failed to load crawled URLs")
        setLatestUrls([])
        setPagination({})
      }
    } catch (error) {
      console.error("Failed to load latest URLs:", error)
      setLatestUrls([])
      setPagination({})
    } finally {
      setUrlsLoading(false)
    }
  }

  const loadCrawlStats = async () => {
    try {
      const token = localStorage.getItem("authToken")
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      }

      const response = await fetch("/api/analytics/crawl-stats", { headers })

      if (response.ok) {
        const data = await response.json()
        setCrawlStats(data.stats)
      } else {
        console.error("Failed to load crawl stats")
        setCrawlStats(null)
      }
    } catch (error) {
      console.error("Failed to load crawl stats:", error)
      setCrawlStats(null)
    }
  }

  const formatNumber = (num) => {
    return new Intl.NumberFormat().format(num)
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString()
  }

  const getStatusColor = (status) => {
    switch (status) {
      case "success":
        return "status-success"
      case "error":
        return "status-error"
      case "pending":
        return "status-pending"
      default:
        return "status-unknown"
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case "success":
        return "✅"
      case "error":
        return "❌"
      case "pending":
        return "⏳"
      default:
        return "❓"
    }
  }

  return (
    <div className="crawl-analytics">
      {/* Stats Overview */}
      {crawlStats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">🌐</div>
            <div className="stat-content">
              <h3>Total Websites</h3>
              <p className="stat-number">{formatNumber(crawlStats.totalUrls)}</p>
              <p className="stat-timestamp">Last updated: {formatDate(crawlStats.lastCrawlTime)}</p>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">📈</div>
            <div className="stat-content">
              <h3>Today's Crawls</h3>
              <p className="stat-number">{formatNumber(crawlStats.todayUrls)}</p>
              <p className="stat-timestamp">Since midnight</p>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">⚡</div>
            <div className="stat-content">
              <h3>Active Workers</h3>
              <p className="stat-number">{crawlStats.activeWorkers}</p>
              <p className="stat-timestamp">Currently running</p>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">📊</div>
            <div className="stat-content">
              <h3>Success Rate</h3>
              <p className="stat-number">{crawlStats.successRate}%</p>
              <p className="stat-timestamp">Last 24 hours</p>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">⏱️</div>
            <div className="stat-content">
              <h3>Avg Response</h3>
              <p className="stat-number">{crawlStats.avgResponseTime}ms</p>
              <p className="stat-timestamp">Per request</p>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">📋</div>
            <div className="stat-content">
              <h3>Queue Size</h3>
              <p className="stat-number">{formatNumber(crawlStats.queueSize)}</p>
              <p className="stat-timestamp">Pending URLs</p>
            </div>
          </div>
        </div>
      )}

      {/* Scrollable Content Container */}
      <div className="analytics-content-scroll">
        {/* Timeframe Selector */}
        <div className="timeframe-selector">
          <h3>Crawl Volume Over Time</h3>
          <div className="timeframe-buttons">
            {["hourly", "daily", "weekly"].map((tf) => (
              <button
                key={tf}
                className={`timeframe-btn ${timeframe === tf ? "active" : ""}`}
                onClick={() => setTimeframe(tf)}
              >
                {tf.charAt(0).toUpperCase() + tf.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Analytics Chart */}
        {loading ? (
          <div className="loading-chart">
            <div className="loading-spinner"></div>
            <p>Loading analytics data...</p>
          </div>
        ) : analyticsData ? (
          <div className="analytics-chart">
            <div className="chart-summary">
              <div className="summary-item">
                <span className="summary-label">Total:</span>
                <span className="summary-value">{formatNumber(analyticsData.summary.total)}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Average:</span>
                <span className="summary-value">{formatNumber(analyticsData.summary.average)}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Peak:</span>
                <span className="summary-value">{formatNumber(analyticsData.summary.peak)}</span>
              </div>
            </div>

            <div className="chart-container">
              <div className="chart-bars">
                {analyticsData.data.map((item, index) => {
                  const height = (item.count / analyticsData.summary.peak) * 100
                  return (
                    <div key={index} className="chart-bar-container">
                      <div className="chart-bar" style={{ height: `${height}%` }} title={`${item.count} URLs`}></div>
                      <div className="chart-label">
                        {timeframe === "hourly"
                          ? `${item.hour}:00`
                          : timeframe === "daily"
                            ? `Day ${item.day}`
                            : `Week ${item.week}`}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="loading-chart">
            <p>No crawl data available</p>
          </div>
        )}

        {/* Latest Crawled URLs */}
        <div className="latest-urls-section">
          <h3>Latest Crawled URLs</h3>

          {/* Filters */}
          <div className="url-filters">
            <div className="filter-group">
              <label>Status:</label>
              <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
                <option value="all">All</option>
                <option value="success">Success</option>
                <option value="error">Error</option>
                <option value="pending">Pending</option>
              </select>
            </div>

            <div className="filter-group">
              <label>Domain:</label>
              <input
                type="text"
                placeholder="Filter by domain..."
                value={filters.domain}
                onChange={(e) => setFilters({ ...filters, domain: e.target.value })}
              />
            </div>

            <div className="filter-group">
              <label>Date Range:</label>
              <select
                value={filters.dateRange}
                onChange={(e) => setFilters({ ...filters, dateRange: Number.parseInt(e.target.value) })}
              >
                <option value={1}>Last 24 hours</option>
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
              </select>
            </div>

            <button className="refresh-btn" onClick={loadLatestUrls}>
              🔄 Refresh
            </button>
          </div>

          {/* URLs Table */}
          {urlsLoading ? (
            <div className="loading-urls">
              <div className="loading-spinner"></div>
              <p>Loading URLs...</p>
            </div>
          ) : (
            <>
              <div className="urls-table-container">
                <div className="urls-table">
                  <div className="table-header">
                    <div className="col-status">Status</div>
                    <div className="col-url">URL</div>
                    <div className="col-title">Title</div>
                    <div className="col-crawled">Crawled At</div>
                    <div className="col-response">Response Time</div>
                    <div className="col-size">Size</div>
                  </div>

                  {latestUrls.map((url) => (
                    <div key={url.id} className="table-row">
                      <div className="col-status">
                        <span className={`status-indicator ${getStatusColor(url.status)}`}>
                          {getStatusIcon(url.status)}
                        </span>
                      </div>
                      <div className="col-url">
                        <a href={url.url} target="_blank" rel="noopener noreferrer">
                          {url.url}
                        </a>
                      </div>
                      <div className="col-title" title={url.title}>
                        {url.title}
                      </div>
                      <div className="col-crawled">{formatDate(url.crawled_at)}</div>
                      <div className="col-response">{url.response_time}ms</div>
                      <div className="col-size">{(url.content_length / 1024).toFixed(1)}KB</div>
                    </div>
                  ))}

                  {latestUrls.length === 0 && (
                    <div style={{ textAlign: "center", padding: "2rem", color: "#888" }}>
                      No URLs found matching the current filters
                    </div>
                  )}
                </div>
              </div>

              {/* Pagination */}
              {pagination && pagination.totalPages > 1 && (
                <div className="pagination">
                  <button
                    className="page-btn"
                    disabled={currentPage === 1}
                    onClick={() => setCurrentPage(currentPage - 1)}
                  >
                    ← Previous
                  </button>

                  <span className="page-info">
                    Page {pagination.currentPage} of {pagination.totalPages} ({formatNumber(pagination.totalItems)}{" "}
                    total items)
                  </span>

                  <button
                    className="page-btn"
                    disabled={currentPage === pagination.totalPages}
                    onClick={() => setCurrentPage(currentPage + 1)}
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default CrawlAnalytics
