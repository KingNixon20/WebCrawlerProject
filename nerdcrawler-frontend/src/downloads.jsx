"use client"

import { useState, useEffect } from "react"
import { AuroraText } from "./components/magicui/aurora-text"
import { useAuth } from "./auth/AuthContext"
import "./index.css"

export default function DownloadsPage() {
  const { user, isAuthenticated } = useAuth()
  const [downloads, setDownloads] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState("all")

  useEffect(() => {
    // Set real download data immediately
    setDownloads([
      {
        id: 1,
        name: "NerdCrawler Source Code",
        description:
          "Complete source code for the NerdCrawler search engine project including frontend, backend, and all components",
        version: "BETA V1",
        size: "~15 MB", // Estimate - you can update this with actual size
        category: "source-code",
        downloadUrl: "/webcrawlerproject-main.zip", // Update with actual download URL
        icon: "📦",
        downloads: 0, // Start with 0 downloads
        rating: 0, // No ratings yet
      },
    ])
    setIsLoading(false)
  }, [])

  const handleGoHome = () => {
    window.history.pushState({}, "", "/")
    window.dispatchEvent(new PopStateEvent("popstate"))
  }

  const categories = [
    { id: "all", label: "All Downloads", icon: "📦" },
    { id: "source-code", label: "Source Code", icon: "💻" },
  ]

  const filteredDownloads =
    selectedCategory === "all" ? downloads : downloads.filter((download) => download.category === selectedCategory)

  const handleDownload = (download) => {
    // Track download
    console.log(`Downloading: ${download.name}`)

    // Increment download count (you might want to send this to your backend)
    setDownloads((prev) => prev.map((d) => (d.id === download.id ? { ...d, downloads: d.downloads + 1 } : d)))

    // Trigger actual download
    if (download.downloadUrl && download.downloadUrl !== "#") {
      const link = document.createElement("a")
      link.href = download.downloadUrl
      link.download = `nerdcrawler-${download.version.toLowerCase().replace(/\s+/g, "-")}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    }

    // Show download notification
    const notification = document.createElement("div")
    notification.textContent = `✅ Started downloading ${download.name}`
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: rgba(76, 175, 80, 0.9);
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      z-index: 10000;
      font-size: 14px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      animation: slideInRight 0.3s ease-out;
    `
    document.body.appendChild(notification)
    setTimeout(() => notification.remove(), 3000)
  }

  return (
    <div
      className="downloads-page"
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
          <h1 style={{ margin: 0, fontSize: "2rem", fontWeight: "600" }}>Downloads</h1>
        </div>
        {isAuthenticated && (
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <span style={{ color: "#ccc" }}>Welcome, {user?.username}!</span>
            <button
              onClick={() => {
                window.history.pushState({}, "", "/dashboard")
                window.dispatchEvent(new PopStateEvent("popstate"))
              }}
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
              Dashboard
            </button>
          </div>
        )}
      </div>

      <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
        {/* Category Filter */}
        <div
          style={{
            display: "flex",
            gap: "1rem",
            marginBottom: "2rem",
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => setSelectedCategory(category.id)}
              style={{
                background: selectedCategory === category.id ? "rgba(79, 195, 247, 0.2)" : "rgba(255, 255, 255, 0.1)",
                border: selectedCategory === category.id ? "1px solid #4fc3f7" : "1px solid rgba(255, 255, 255, 0.2)",
                color: selectedCategory === category.id ? "#4fc3f7" : "#fff",
                padding: "0.75rem 1.5rem",
                borderRadius: "25px",
                cursor: "pointer",
                fontSize: "0.9rem",
                fontWeight: "500",
                transition: "all 0.2s ease",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <span>{category.icon}</span>
              {category.label}
            </button>
          ))}
        </div>

        {/* Downloads Grid */}
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
            <p>Loading downloads...</p>
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))",
              gap: "2rem",
            }}
          >
            {filteredDownloads.map((download) => (
              <div
                key={download.id}
                style={{
                  background: "rgba(20, 20, 20, 0.8)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  borderRadius: "12px",
                  padding: "2rem",
                  transition: "all 0.3s ease",
                  cursor: "pointer",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "translateY(-5px)"
                  e.currentTarget.style.borderColor = "#4fc3f7"
                  e.currentTarget.style.boxShadow = "0 8px 25px rgba(0, 0, 0, 0.4)"
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "translateY(0)"
                  e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.1)"
                  e.currentTarget.style.boxShadow = "none"
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "1rem",
                    marginBottom: "1.5rem",
                  }}
                >
                  <div
                    style={{
                      fontSize: "2.5rem",
                      background: "rgba(79, 195, 247, 0.1)",
                      padding: "0.5rem",
                      borderRadius: "8px",
                      border: "1px solid rgba(79, 195, 247, 0.3)",
                    }}
                  >
                    {download.icon}
                  </div>
                  <div style={{ flex: 1 }}>
                    <h3
                      style={{
                        margin: "0 0 0.5rem",
                        color: "#fff",
                        fontSize: "1.3rem",
                        fontWeight: "600",
                      }}
                    >
                      {download.name}
                    </h3>
                    <p
                      style={{
                        margin: "0 0 0.5rem",
                        color: "#ccc",
                        fontSize: "0.9rem",
                        lineHeight: "1.4",
                      }}
                    >
                      {download.description}
                    </p>
                    <div
                      style={{
                        display: "flex",
                        gap: "1rem",
                        fontSize: "0.8rem",
                        color: "#888",
                      }}
                    >
                      <span>Version: {download.version}</span>
                      <span>Size: {download.size}</span>
                    </div>
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "1rem",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "1rem",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.25rem",
                      }}
                    >
                      {[1, 2, 3, 4, 5].map((star) => (
                        <span
                          key={star}
                          style={{
                            color: "#333",
                            fontSize: "0.9rem",
                          }}
                        >
                          ⭐
                        </span>
                      ))}
                      <span
                        style={{
                          color: "#ccc",
                          fontSize: "0.8rem",
                          marginLeft: "0.5rem",
                        }}
                      >
                        No ratings yet
                      </span>
                    </div>
                    <span
                      style={{
                        color: "#888",
                        fontSize: "0.8rem",
                      }}
                    >
                      {download.downloads} downloads
                    </span>
                  </div>
                </div>

                <button onClick={() => handleDownload(download)} className="downloads-button" style={{ width: "100%" }}>
                  Download {download.name}
                </button>
              </div>
            ))}
          </div>
        )}

        {filteredDownloads.length === 0 && !isLoading && (
          <div
            style={{
              textAlign: "center",
              padding: "4rem",
              color: "#888",
            }}
          >
            <p style={{ fontSize: "1.2rem", marginBottom: "1rem" }}>No downloads found in this category</p>
            <button
              onClick={() => setSelectedCategory("all")}
              style={{
                background: "rgba(79, 195, 247, 0.1)",
                border: "1px solid #4fc3f7",
                color: "#4fc3f7",
                padding: "0.75rem 1.5rem",
                borderRadius: "8px",
                cursor: "pointer",
                fontSize: "0.9rem",
              }}
            >
              View All Downloads
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
