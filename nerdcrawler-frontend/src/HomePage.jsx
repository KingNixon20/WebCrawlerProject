"use client"

import { useEffect, useState } from "react"
import { AuroraText } from "./components/magicui/aurora-text"
import { useAuth } from "./auth/AuthContext"
import IndexedPagesCount from "./components/IndexedPagesCount"
import "./index.css"

// Add this after the imports and before the component
const trackPageVisit = async (page) => {
  try {
    const token = localStorage.getItem("authToken")
    const headers = {
      "Content-Type": "application/json",
    }

    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    await fetch("https://projectkryptos.xyz/api/analytics/track", {
      method: "POST",
      headers,
      body: JSON.stringify({ page }),
    })
  } catch (error) {
    console.error("Analytics tracking failed:", error)
  }
}

export default function HomePage() {
  const { user, isAuthenticated, logout } = useAuth()
  const [search, setSearch] = useState("")
  const [results, setResults] = useState([])
  const [imageResults, setImageResults] = useState([])
  const [searchType, setSearchType] = useState("web")
  const [viewMode, setViewMode] = useState("list")
  const [simpleView, setSimpleView] = useState(false)
  const [advancedView, setAdvancedView] = useState(false)
  const [perPage, setPerPage] = useState(25)
  const [page, setPage] = useState(1)
  const [searchTime, setSearchTime] = useState(0)
  const [showSettingsDropdown, setShowSettingsDropdown] = useState(false)
  const [showSettingsModal, setShowSettingsModal] = useState(false)
  const [currentWallpaper, setCurrentWallpaper] = useState("/bg2.jpg")
  const [blurIntensity, setBlurIntensity] = useState(10)
  const [accentColor, setAccentColor] = useState("#4fc3f7")
  const [isSearching, setIsSearching] = useState(false)

  // Smart Filtering States
  const [showSmartFilters, setShowSmartFilters] = useState(false)
  const [selectedFileTypes, setSelectedFileTypes] = useState([])
  const [selectedDateRange, setSelectedDateRange] = useState("any")
  const [selectedPageLength, setSelectedPageLength] = useState("any")
  const [selectedTechStack, setSelectedTechStack] = useState([])
  const [savedResults, setSavedResults] = useState([])
  const [resultRatings, setResultRatings] = useState({})
  const [previewResult, setPreviewResult] = useState(null)

  const [showRedditAccordion, setShowRedditAccordion] = useState(true)
  const [expandedRedditItems, setExpandedRedditItems] = useState({})

  useEffect(() => {
    // Check if the meta tag already exists
    const existingMeta = document.querySelector('meta[name="google-site-verification"]')
    if (!existingMeta) {
      const meta = document.createElement("meta")
      meta.name = "google-site-verification"
      meta.content = "oqXoenPBo3BvlgajZf0p6YvsR6GBt-_QBShmivxvOaU"
      document.head.appendChild(meta)
    }
  }, [])
  // Cookie consent state
  const [showCookieConsent, setShowCookieConsent] = useState(false)

  // Add Google site verification meta tag
  useEffect(() => {
    // Check if the meta tag already exists
    const existingMeta = document.querySelector('meta[name="google-site-verification"]')
    if (!existingMeta) {
      const meta = document.createElement("meta")
      meta.name = "google-site-verification"
      meta.content = "oqXoenPBo3BvlgajZf0p6YvsR6GBt-_QBShmivxvOaU"
      document.head.appendChild(meta)
    }
  }, [])

  // Check if user has already accepted cookies
  useEffect(() => {
    const cookieConsent = localStorage.getItem("cookieConsent")
    if (!cookieConsent) {
      setTimeout(() => {
        setShowCookieConsent(true)
      }, 2000)
    }
  }, [])

  const handleAcceptCookies = () => {
    localStorage.setItem("cookieConsent", "accepted")
    setShowCookieConsent(false)
  }

  useEffect(() => {
    // Track homepage visit
    trackPageVisit("/")

    setViewMode("list")
    setSimpleView(document.cookie.includes("simpleView=true"))
    setAdvancedView(document.cookie.includes("advancedView=true"))

    const urlParams = new URLSearchParams(window.location.search)
    const q = urlParams.get("q")
    const type = urlParams.get("type") || "web"
    if (q) {
      setSearch(q)
      setSearchType(type)
      fetchResults(null, q, type)
    }

    // Load saved settings
    const savedWallpaper = localStorage.getItem("wallpaper")
    const savedBlur = localStorage.getItem("blurIntensity")
    const savedAccent = localStorage.getItem("accentColor")
    const savedResultsList = localStorage.getItem("savedResults")
    const savedRatings = localStorage.getItem("resultRatings")

    if (savedWallpaper) setCurrentWallpaper(savedWallpaper)
    if (savedBlur) setBlurIntensity(Number.parseInt(savedBlur))
    if (savedAccent) setAccentColor(savedAccent)
    if (savedResultsList) setSavedResults(JSON.parse(savedResultsList))
    if (savedRatings) setResultRatings(JSON.parse(savedRatings))
  }, [])

  useEffect(() => {
    document.documentElement.style.setProperty("--bg-image-url", `url("${currentWallpaper}")`)
    document.documentElement.style.setProperty("--bg-blur", `${blurIntensity}px`)
    document.documentElement.style.setProperty("--accent", accentColor)
  }, [currentWallpaper, blurIntensity, accentColor])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        showSettingsDropdown &&
        !event.target.closest("#settings-container") &&
        !event.target.closest("#settings-dropdown")
      ) {
        setShowSettingsDropdown(false)
      }
    }

    if (showSettingsDropdown) {
      setTimeout(() => {
        document.addEventListener("mousedown", handleClickOutside)
      }, 100)
    }

    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [showSettingsDropdown])

  const fetchResults = async (e, overrideSearch = null, overrideType = null, overridePage = null) => {
    if (e) e.preventDefault()
    const query = overrideSearch ?? search
    const type = overrideType ?? searchType
    const currentPage = overridePage ?? page

    setIsSearching(true) // Add this line

    const startTime = performance.now()

    // Include auth token if user is logged in
    const headers = {
      "Content-Type": "application/json",
    }

    const token = localStorage.getItem("authToken")
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    try {
      const endpoint = type === "images" ? "/api/search/images" : "/api/search"
      const res = await fetch(
        `https://projectkryptos.xyz${endpoint}?q=${encodeURIComponent(query)}&page=${currentPage}&per_page=${perPage}`,
        { headers },
      )
      const data = await res.json()
      const endTime = performance.now()

      setSearchTime(endTime - startTime)

      if (type === "images") {
        setImageResults(data.results)
        setResults([])
      } else {
        setResults(data.results)
        setImageResults([])
      }

      if (typeof document !== "undefined") {
        const hasResults = (data.results?.length ?? 0) > 0
        if (hasResults) {
          document.body.classList.add("results-active")
        } else {
          document.body.classList.remove("results-active")
        }
      }

      const url = new URL(window.location)
      url.searchParams.set("q", query)
      url.searchParams.set("type", type)
      url.searchParams.set("page", currentPage.toString())
      window.history.pushState({}, "", url)
    } catch (error) {
      console.error("Search failed:", error)
    } finally {
      setIsSearching(false) // Add this line
    }
  }

  const handleLogout = async () => {
    await logout()
    setShowSettingsDropdown(false)
    // Optionally show a logout success message
    const notification = document.createElement("div")
    notification.className = "logout-notification"
    notification.textContent = "✅ Logged out successfully!"
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

  const switchSearchType = (newType) => {
    setSearchType(newType)
    if (search) {
      fetchResults(null, search, newType)
    }
  }

  const toggleViewMode = (mode) => {
    setViewMode(mode)
    document.cookie = `${mode}View=true; path=/`
  }

  const handleSettingsClick = (e) => {
    e.stopPropagation()
    setShowSettingsDropdown(!showSettingsDropdown)
  }

  const handleSettingsModalOpen = () => {
    setShowSettingsModal(true)
    setShowSettingsDropdown(false)
  }

  const handleWallpaperChange = (wallpaper) => {
    setCurrentWallpaper(wallpaper)
    localStorage.setItem("wallpaper", wallpaper)
  }

  const handleCustomWallpaperUpload = (event) => {
    const file = event.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => {
        const dataUrl = e.target.result
        setCurrentWallpaper(dataUrl)
        localStorage.setItem("wallpaper", dataUrl)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleBlurChange = (blur) => {
    setBlurIntensity(blur)
    localStorage.setItem("blurIntensity", blur.toString())
  }

  const handleAccentColorChange = (color) => {
    setAccentColor(color)
    localStorage.setItem("accentColor", color)
  }

  // Smart Filtering Functions
  const toggleFileType = (fileType) => {
    setSelectedFileTypes((prev) =>
      prev.includes(fileType) ? prev.filter((type) => type !== fileType) : [...prev, fileType],
    )
  }

  const toggleTechStack = (tech) => {
    setSelectedTechStack((prev) => (prev.includes(tech) ? prev.filter((t) => t !== tech) : [...prev, tech]))
  }

  const saveResult = (result) => {
    const newSavedResults = [...savedResults, { ...result, savedAt: Date.now() }]
    setSavedResults(newSavedResults)
    localStorage.setItem("savedResults", JSON.stringify(newSavedResults))
  }

  const unsaveResult = (resultUrl) => {
    const newSavedResults = savedResults.filter((r) => r.url !== resultUrl)
    setSavedResults(newSavedResults)
    localStorage.setItem("savedResults", JSON.stringify(newSavedResults))
  }

  // Rating functions (keeping existing functionality)
  const fetchCommunityRatings = async (url) => {
    await new Promise((resolve) => setTimeout(resolve, 100))
    const mockBackendRatings = {
      "example.com": [4, 5, 3, 4, 5],
      "github.com": [5, 4, 5, 4, 5, 3, 4],
      "stackoverflow.com": [5, 5, 4, 5, 4, 5],
    }
    const domain = url
      .replace(/^https?:\/\//, "")
      .replace(/^www\./, "")
      .split("/")[0]
    return mockBackendRatings[domain] || []
  }

  const postRatingToBackend = async (url, rating) => {
    await new Promise((resolve) => setTimeout(resolve, 200))
    return {
      success: true,
      message: "Rating saved successfully",
      newAverage: 4.2,
      totalRatings: 15,
    }
  }

  const getAverageRating = (url) => {
    const domain = url
      .replace(/^https?:\/\//, "")
      .replace(/^www\./, "")
      .split("/")[0]
    const mockRatings = {
      "example.com": 4.2,
      "github.com": 4.4,
      "stackoverflow.com": 4.7,
    }
    return mockRatings[domain] || 0
  }

  const getCommunityRatingCount = (url) => {
    const domain = url
      .replace(/^https?:\/\//, "")
      .replace(/^www\./, "")
      .split("/")[0]
    const mockCounts = {
      "example.com": 5,
      "github.com": 7,
      "stackoverflow.com": 6,
    }
    return mockCounts[domain] || 0
  }

  const rateResult = async (resultUrl, rating) => {
    const newRatings = { ...resultRatings, [resultUrl]: rating }
    setResultRatings(newRatings)
    localStorage.setItem("resultRatings", JSON.stringify(newRatings))

    try {
      const response = await postRatingToBackend(resultUrl, rating)
      if (response.success) {
        const notification = document.createElement("div")
        notification.className = "rating-notification"
        notification.textContent = "✅ Your rating has been saved and shared with the community!"
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
    } catch (error) {
      console.error("Failed to save rating:", error)
    }
  }

  const previewResultContent = (result) => {
    setPreviewResult(result)
  }

  const predefinedWallpapers = [
    "/bg2.jpg",
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1920&h=1080&fit=crop",
    "https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?w=1920&h=1080&fit=crop",
    "https://images.unsplash.com/photo-1446776877081-d282a0f896e2?w=1920&h=1080&fit=crop",
    "https://images.unsplash.com/photo-1502134249126-9f3755a50d78?w=1920&h=1080&fit=crop",
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1920&h=1080&fit=crop",
  ]

  const accentColors = ["#4fc3f7", "#ff5722", "#4caf50", "#9c27b0", "#ff9800", "#f44336", "#2196f3", "#795548"]

  const fileTypes = [
    { type: "pdf", label: "PDF", icon: "📄" },
    { type: "doc", label: "Word", icon: "📝" },
    { type: "ppt", label: "PowerPoint", icon: "📊" },
    { type: "xls", label: "Excel", icon: "📈" },
    { type: "txt", label: "Text", icon: "📋" },
    { type: "html", label: "Web Page", icon: "🌐" },
  ]

  const techStacks = [
    { tech: "react", label: "React", color: "#61dafb" },
    { tech: "vue", label: "Vue.js", color: "#4fc08d" },
    { tech: "angular", label: "Angular", color: "#dd0031" },
    { tech: "node", label: "Node.js", color: "#339933" },
    { tech: "python", label: "Python", color: "#3776ab" },
    { tech: "javascript", label: "JavaScript", color: "#f7df1e" },
    { tech: "typescript", label: "TypeScript", color: "#3178c6" },
    { tech: "php", label: "PHP", color: "#777bb4" },
  ]

  const getRedditResults = (searchQuery) => {
    const mockRedditResults = [
      {
        id: 1,
        title: `r/webdev: Best practices for ${searchQuery} development`,
        summary: `Community discussion about modern approaches to ${searchQuery}, including tips from experienced developers and common pitfalls to avoid.`,
        url: `https://reddit.com/r/webdev/comments/example1`,
        subreddit: "webdev",
        upvotes: 234,
      },
      {
        id: 2,
        title: `r/programming: ${searchQuery} vs alternatives - comprehensive comparison`,
        summary: `In-depth analysis comparing ${searchQuery} with other similar technologies, covering performance, ease of use, and community support.`,
        url: `https://reddit.com/r/programming/comments/example2`,
        subreddit: "programming",
        upvotes: 189,
      },
      {
        id: 3,
        title: `r/learnprogramming: Getting started with ${searchQuery} - beginner guide`,
        summary: `Step-by-step tutorial for beginners looking to learn ${searchQuery}, including recommended resources and learning path.`,
        url: `https://reddit.com/r/learnprogramming/comments/example3`,
        subreddit: "learnprogramming",
        upvotes: 156,
      },
      {
        id: 4,
        title: `r/technology: ${searchQuery} trends and future outlook`,
        summary: `Discussion about current trends in ${searchQuery} technology and predictions for future developments in the field.`,
        url: `https://reddit.com/r/technology/comments/example4`,
        subreddit: "technology",
        upvotes: 298,
      },
      {
        id: 5,
        title: `r/askreddit: What's your experience with ${searchQuery}?`,
        summary: `Community members share their personal experiences, success stories, and challenges when working with ${searchQuery}.`,
        url: `https://reddit.com/r/askreddit/comments/example5`,
        subreddit: "askreddit",
        upvotes: 445,
      },
    ]
    return mockRedditResults
  }

  const toggleRedditItem = (itemId) => {
    setExpandedRedditItems((prev) => ({
      ...prev,
      [itemId]: !prev[itemId],
    }))
  }

  const renderRedditAccordion = () => {
    if (!showRedditAccordion || searchType === "images") return null

    return (
      <div className="reddit-discussions">
        {getRedditResults(search).map((redditResult) => (
          <div key={redditResult.id} className="reddit-item">
            <button className="reddit-item-header" onClick={() => toggleRedditItem(redditResult.id)}>
              <div className="reddit-item-title">
                <span className="reddit-item-text">{redditResult.title}</span>
                <div className="reddit-item-meta">
                  <span className="reddit-upvotes">↑ {redditResult.upvotes}</span>
                  <span className="reddit-subreddit">r/{redditResult.subreddit}</span>
                </div>
              </div>
              <div className={`reddit-chevron ${expandedRedditItems[redditResult.id] ? "expanded" : ""}`}>▼</div>
            </button>

            {expandedRedditItems[redditResult.id] && (
              <div className="reddit-item-content">
                <p className="reddit-summary">{redditResult.summary}</p>
                <a href={redditResult.url} target="_blank" rel="noopener noreferrer" className="reddit-link">
                  View on Reddit →
                </a>
              </div>
            )}
          </div>
        ))}
      </div>
    )
  }

  const handlePerPageChange = (newPerPage) => {
    setPerPage(newPerPage)
    setPage(1)
    if (search) {
      fetchResults(null, search, searchType, 1)
    }
  }

  const handleNextPage = () => {
    const nextPage = page + 1
    setPage(nextPage)
    if (search) {
      fetchResults(null, search, searchType, nextPage)
    }
    const resultsContainer = document.getElementById("results-container")
    if (resultsContainer) {
      resultsContainer.scrollTop = 0
    }
  }

  const currentResults = searchType === "images" ? imageResults : results
  const hasResults = currentResults.length > 0

  return (
    <div className={`homepage ${hasResults ? "results-active" : ""}`}>
      <div id="main-content">
        {!hasResults && (
          <>
            <a href="/" id="nerdcrawler-link">
              <span className="full-text">
                <span className="nerd">Nerd</span>
                <AuroraText className="crawler">Crawler</AuroraText>
              </span>
              <span className="short-text">NC</span>
            </a>

            <div id="search-container">
              <form onSubmit={fetchResults}>
                <div className="search-bar-wrapper">
                  <input
                    type="text"
                    id="search-input"
                    placeholder="Type to search..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                  <button type="submit" id="search-button" disabled={isSearching}>
                    {isSearching ? (
                      <div className="loading-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    ) : (
                      <img src="/search.png" alt="Search" />
                    )}
                  </button>
                </div>
              </form>
            </div>

            {/* Add the indexed pages count component here */}
            <IndexedPagesCount />

            <div id="settings-container" className="homepage-settings">
              <button id="settings-icon" onClick={handleSettingsClick}>
                <img src="/settings.png" alt="Settings" />
              </button>
              {showSettingsDropdown && (
                <div id="settings-dropdown" className="visible" onMouseDown={(e) => e.stopPropagation()}>
                  <button
                    onMouseDown={(e) => {
                      e.stopPropagation()
                      e.preventDefault()
                      setShowSettingsModal(true)
                      setShowSettingsDropdown(false)
                    }}
                    style={{
                      width: "100%",
                      padding: "12px 16px",
                      background: "none",
                      border: "none",
                      color: "#fff",
                      fontSize: "14px",
                      textAlign: "left",
                      cursor: "pointer",
                      borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                    }}
                  >
                    Settings
                  </button>
                  <button
                    onMouseDown={(e) => {
                      e.stopPropagation()
                      e.preventDefault()
                      window.history.pushState({}, "", "/games")
                      window.dispatchEvent(new PopStateEvent("popstate"))
                    }}
                    style={{
                      width: "100%",
                      padding: "12px 16px",
                      background: "none",
                      border: "none",
                      color: "#fff",
                      fontSize: "14px",
                      textAlign: "left",
                      cursor: "pointer",
                      borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                    }}
                  >
                    🎮 Games
                  </button>
                  {isAuthenticated ? (
                    <>
                      <div
                        style={{
                          padding: "8px 16px",
                          borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                          fontSize: "12px",
                          color: "#4fc3f7",
                        }}
                      >
                        Welcome, {user?.username}!
                      </div>
                      <button
                        onMouseDown={(e) => {
                          e.stopPropagation()
                          e.preventDefault()
                          window.history.pushState({}, "", "/dashboard")
                          window.dispatchEvent(new PopStateEvent("popstate"))
                        }}
                        style={{
                          width: "100%",
                          padding: "12px 16px",
                          background: "none",
                          border: "none",
                          color: "#4fc3f7",
                          fontSize: "14px",
                          textAlign: "left",
                          cursor: "pointer",
                          borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                        }}
                      >
                        📊 Dashboard
                      </button>
                      {user?.privilege_level === "godmode" && (
                        <button
                          onMouseDown={(e) => {
                            e.stopPropagation()
                            e.preventDefault()
                            window.history.pushState({}, "", "/analytics")
                            window.dispatchEvent(new PopStateEvent("popstate"))
                          }}
                          style={{
                            width: "100%",
                            padding: "12px 16px",
                            background: "none",
                            border: "none",
                            color: "#ffd700",
                            fontSize: "14px",
                            textAlign: "left",
                            cursor: "pointer",
                            borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                          }}
                        >
                          📊 Analytics
                        </button>
                      )}
                      <button
                        onMouseDown={(e) => {
                          e.stopPropagation()
                          e.preventDefault()
                          handleLogout()
                        }}
                        style={{
                          width: "100%",
                          padding: "12px 16px",
                          background: "none",
                          border: "none",
                          color: "#ff4444",
                          fontSize: "14px",
                          textAlign: "left",
                          cursor: "pointer",
                        }}
                      >
                        Logout
                      </button>
                    </>
                  ) : (
                    <button
                      onMouseDown={(e) => {
                        e.stopPropagation()
                        e.preventDefault()
                        window.history.pushState({}, "", "/login")
                        window.dispatchEvent(new PopStateEvent("popstate"))
                      }}
                      style={{
                        width: "100%",
                        padding: "12px 16px",
                        background: "none",
                        border: "none",
                        color: "#fff",
                        fontSize: "14px",
                        textAlign: "left",
                        cursor: "pointer",
                      }}
                    >
                      Login/Signup
                    </button>
                  )}
                </div>
              )}
            </div>
          </>
        )}

        {hasResults && (
          <>
            <div id="top-bar-aligned">
              <a href="/" id="nerdcrawler-link" className="results-aligned">
                <span className="full-text">
                  <span className="nerd">Nerd</span>
                  <AuroraText className="crawler">Crawler</AuroraText>
                </span>
                <span className="short-text">NC</span>
              </a>

              <div id="search-container" className="results-aligned">
                <form onSubmit={fetchResults}>
                  <div className="search-bar-wrapper">
                    <input
                      type="text"
                      id="search-input"
                      placeholder="Type to search..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                    <button type="submit" id="search-button" disabled={isSearching}>
                      {isSearching ? (
                        <div className="loading-dots">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      ) : (
                        <img src="/search.png" alt="Search" />
                      )}
                    </button>
                  </div>
                </form>
              </div>

              <div id="settings-container" className="results-aligned">
                <button id="settings-icon" onClick={handleSettingsClick}>
                  <img src="/settings.png" alt="Settings" />
                </button>
                {showSettingsDropdown && (
                  <div id="settings-dropdown" className="visible" onMouseDown={(e) => e.stopPropagation()}>
                    <button
                      onMouseDown={(e) => {
                        e.stopPropagation()
                        e.preventDefault()
                        setShowSettingsModal(true)
                        setShowSettingsDropdown(false)
                      }}
                      style={{
                        width: "100%",
                        padding: "12px 16px",
                        background: "none",
                        border: "none",
                        color: "#fff",
                        fontSize: "14px",
                        textAlign: "left",
                        cursor: "pointer",
                        borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                      }}
                    >
                      Settings
                    </button>
                    <button
                      onMouseDown={(e) => {
                        e.stopPropagation()
                        e.preventDefault()
                        window.history.pushState({}, "", "/games")
                        window.dispatchEvent(new PopStateEvent("popstate"))
                      }}
                      style={{
                        width: "100%",
                        padding: "12px 16px",
                        background: "none",
                        border: "none",
                        color: "#fff",
                        fontSize: "14px",
                        textAlign: "left",
                        cursor: "pointer",
                        borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                      }}
                    >
                      🎮 Games
                    </button>
                    {isAuthenticated ? (
                      <>
                        <div
                          style={{
                            padding: "8px 16px",
                            borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                            fontSize: "12px",
                            color: "#4fc3f7",
                          }}
                        >
                          Welcome, {user?.username}!
                        </div>
                        <button
                          onMouseDown={(e) => {
                            e.stopPropagation()
                            e.preventDefault()
                            window.history.pushState({}, "", "/dashboard")
                            window.dispatchEvent(new PopStateEvent("popstate"))
                          }}
                          style={{
                            width: "100%",
                            padding: "12px 16px",
                            background: "none",
                            border: "none",
                            color: "#4fc3f7",
                            fontSize: "14px",
                            textAlign: "left",
                            cursor: "pointer",
                            borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                          }}
                        >
                          📊 Dashboard
                        </button>
                        {user?.privilege_level === "godmode" && (
                          <button
                            onMouseDown={(e) => {
                              e.stopPropagation()
                              e.preventDefault()
                              window.history.pushState({}, "", "/analytics")
                              window.dispatchEvent(new PopStateEvent("popstate"))
                            }}
                            style={{
                              width: "100%",
                              padding: "12px 16px",
                              background: "none",
                              border: "none",
                              color: "#ffd700",
                              fontSize: "14px",
                              textAlign: "left",
                              cursor: "pointer",
                              borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                            }}
                          >
                            📊 Analytics
                          </button>
                        )}
                        <button
                          onMouseDown={(e) => {
                            e.stopPropagation()
                            e.preventDefault()
                            handleLogout()
                          }}
                          style={{
                            width: "100%",
                            padding: "12px 16px",
                            background: "none",
                            border: "none",
                            color: "#ff4444",
                            fontSize: "14px",
                            textAlign: "left",
                            cursor: "pointer",
                          }}
                        >
                          Logout
                        </button>
                      </>
                    ) : (
                      <button
                        onMouseDown={(e) => {
                          e.stopPropagation()
                          e.preventDefault()
                          window.history.pushState({}, "", "/login")
                          window.dispatchEvent(new PopStateEvent("popstate"))
                        }}
                        style={{
                          width: "100%",
                          padding: "12px 16px",
                          background: "none",
                          border: "none",
                          color: "#fff",
                          fontSize: "14px",
                          textAlign: "left",
                          cursor: "pointer",
                        }}
                      >
                        Login/Signup
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="results-content">
              <div className="search-type-tabs">
                <button
                  className={`search-tab ${searchType === "web" ? "active" : ""}`}
                  onClick={() => switchSearchType("web")}
                >
                  🌐 All
                </button>
                <button
                  className={`search-tab ${searchType === "images" ? "active" : ""}`}
                  onClick={() => switchSearchType("images")}
                >
                  🖼️ Images
                </button>
              </div>

              <div className="view-mode-options">
                <div className="view-mode-toggle">
                  <input type="checkbox" checked={viewMode === "list"} onChange={() => toggleViewMode("list")} />
                  <label>List</label>
                </div>
                {searchType === "images" ? (
                  <div className="view-mode-toggle">
                    <input type="checkbox" checked={viewMode === "grid"} onChange={() => toggleViewMode("grid")} />
                    <label>Grid</label>
                  </div>
                ) : (
                  <div className="view-mode-toggle disabled">
                    <input type="checkbox" checked={false} disabled />
                    <label>Grid (Coming Soon)</label>
                  </div>
                )}
                <div className="view-mode-toggle">
                  <input type="checkbox" checked={simpleView} onChange={() => setSimpleView(!simpleView)} />
                  <label>Simple</label>
                </div>
                <div className="view-mode-toggle">
                  <input type="checkbox" checked={advancedView} onChange={() => setAdvancedView(!advancedView)} />
                  <label>Advanced</label>
                </div>
                <div className="results-per-page">
                  <select value={perPage} onChange={(e) => handlePerPageChange(Number.parseInt(e.target.value))}>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                </div>
                {searchType === "web" && (
                  <button className="smart-filters-toggle" onClick={() => setShowSmartFilters(!showSmartFilters)}>
                    🔍 Smart Filters
                  </button>
                )}
              </div>

              {showSmartFilters && searchType === "web" && (
                <div className="smart-filters-panel">
                  <div className="filter-section">
                    <h4>File Type</h4>
                    <div className="filter-chips">
                      {fileTypes.map(({ type, label, icon }) => (
                        <button
                          key={type}
                          className={`filter-chip ${selectedFileTypes.includes(type) ? "active" : ""}`}
                          onClick={() => toggleFileType(type)}
                        >
                          <span className="chip-icon">{icon}</span>
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="filter-section">
                    <h4>Date Range</h4>
                    <select
                      value={selectedDateRange}
                      onChange={(e) => setSelectedDateRange(e.target.value)}
                      className="filter-select"
                    >
                      <option value="any">Any time</option>
                      <option value="day">Past 24 hours</option>
                      <option value="week">Past week</option>
                      <option value="month">Past month</option>
                      <option value="year">Past year</option>
                    </select>
                  </div>

                  <div className="filter-section">
                    <h4>Page Length</h4>
                    <select
                      value={selectedPageLength}
                      onChange={(e) => setSelectedPageLength(e.target.value)}
                      className="filter-select"
                    >
                      <option value="any">Any length</option>
                      <option value="short">Short (1-5 pages)</option>
                      <option value="medium">Medium (6-20 pages)</option>
                      <option value="long">Long (20+ pages)</option>
                    </select>
                  </div>

                  <div className="filter-section">
                    <h4>Tech Stack</h4>
                    <div className="filter-chips">
                      {techStacks.map(({ tech, label, color }) => (
                        <button
                          key={tech}
                          className={`filter-chip tech-chip ${selectedTechStack.includes(tech) ? "active" : ""}`}
                          onClick={() => toggleTechStack(tech)}
                          style={{ "--tech-color": color }}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <div id="results-info">
                Showing page {page} ({currentResults.length} {searchType === "images" ? "images" : "results"}) • Fetched
                in {searchTime.toFixed(1)}ms
                {isAuthenticated && <span className="auth-indicator"> • Logged in as {user?.username}</span>}
              </div>

              <div
                id="results-container"
                className={`${searchType === "images" && viewMode === "grid" ? "images-grid-view" : viewMode}-view ${simpleView ? "simple-view" : ""} ${advancedView ? "advanced-view" : ""}`}
              >
                {searchType === "images"
                  ? imageResults.map((row, idx) => (
                      <div key={`image-${idx}`} className="image-result-card">
                        <div className="image-container">
                          <img
                            src={row.images?.[0] || "/placeholder.svg?height=200&width=300&query=image"}
                            alt={row.title}
                            loading="lazy"
                            onError={(e) => {
                              e.target.src = "/placeholder.svg?height=200&width=300"
                            }}
                          />
                          <div className="image-overlay">
                            <a
                              href={row.url.startsWith("http") ? row.url : `http://${row.url}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="image-source-link"
                            >
                              View Source
                            </a>
                          </div>
                        </div>
                        <div className="image-info">
                          <h3 className="image-title">{row.title}</h3>
                          <p className="image-source">
                            {new URL(row.url.startsWith("http") ? row.url : `http://${row.url}`).hostname}
                          </p>
                        </div>
                      </div>
                    ))
                  : results.map((row, idx) => (
                      <div key={`result-${idx}`}>
                        {idx === 5 && results.length > 5 && renderRedditAccordion()}

                        <div className="result-card">
                          <div className="result-main-content">
                            <a
                              href={row.url.startsWith("http") ? row.url : `http://${row.url}`}
                              className="result-title"
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {row.title}
                            </a>
                            <p className="result-summary">{row.summary}</p>
                            <div className="result-meta">
                              <span className="result-time">{row.timestamp}</span>
                            </div>

                            <div className="result-rating-section">
                              <div className="average-rating">
                                <span className="rating-label">Community:</span>
                                <div className="rating-stars average-stars">
                                  {[1, 2, 3, 4, 5].map((star) => (
                                    <span
                                      key={star}
                                      className={`rating-star average-star ${
                                        (getAverageRating(row.url) || 0) >= star ? "active" : ""
                                      }`}
                                    >
                                      ⭐
                                    </span>
                                  ))}
                                  <span className="rating-count">
                                    {getCommunityRatingCount(row.url) > 0
                                      ? `${getAverageRating(row.url)?.toFixed(1)} (${getCommunityRatingCount(row.url)})`
                                      : "No ratings"}
                                  </span>
                                  {resultRatings[row.url] && (
                                    <span className="user-rating-indicator">• You rated {resultRatings[row.url]}★</span>
                                  )}
                                </div>
                              </div>

                              {!resultRatings[row.url] && isAuthenticated && (
                                <div className="user-rating">
                                  <span className="rating-label">Rate this:</span>
                                  <div className="rating-stars user-stars">
                                    {[1, 2, 3, 4, 5].map((rating) => (
                                      <button
                                        key={rating}
                                        className="rating-star user-star"
                                        onClick={() => rateResult(row.url, rating)}
                                        title={`Rate ${rating} stars`}
                                      >
                                        ⭐
                                      </button>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {!isAuthenticated && (
                                <div className="login-prompt">
                                  <span className="rating-label">
                                    <a
                                      href="#"
                                      onClick={(e) => {
                                        e.preventDefault()
                                        window.history.pushState({}, "", "/login")
                                        window.dispatchEvent(new PopStateEvent("popstate"))
                                      }}
                                      style={{ color: "#4fc3f7", textDecoration: "underline" }}
                                    >
                                      Login to rate
                                    </a>
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>

                          <div className="result-actions">
                            <button
                              className="action-btn preview-btn"
                              onClick={() => previewResultContent(row)}
                              title="Quick Preview"
                            >
                              👁️
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                {currentResults.length === perPage && (
                  <div className="pagination-container">
                    <button className="codepen-button" onClick={handleNextPage}>
                      <span>Next Page</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {previewResult && (
          <div className="preview-modal-overlay" onClick={() => setPreviewResult(null)}>
            <div className="preview-modal" onClick={(e) => e.stopPropagation()}>
              <div className="preview-modal-header">
                <h3>{previewResult.title}</h3>
                <button className="close-button" onClick={() => setPreviewResult(null)}>
                  ×
                </button>
              </div>
              <div className="preview-modal-content">
                <p>
                  <strong>URL:</strong> {previewResult.url}
                </p>
                <p>
                  <strong>Summary:</strong> {previewResult.summary}
                </p>
                <p>
                  <strong>Timestamp:</strong> {previewResult.timestamp}
                </p>
                <div className="preview-placeholder">
                  <p>🔍 Content preview would load here...</p>
                  <p>In a real implementation, this would show a preview of the webpage content.</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {showSettingsModal && (
          <div className="settings-modal-overlay" onClick={() => setShowSettingsModal(false)}>
            <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
              <div className="settings-modal-header">
                <h2>Settings</h2>
                <button className="close-button" onClick={() => setShowSettingsModal(false)}>
                  ×
                </button>
              </div>

              <div className="settings-modal-content">
                <div className="settings-section">
                  <h3>Background Wallpaper</h3>
                  <div className="wallpaper-grid">
                    {predefinedWallpapers.map((wallpaper, index) => (
                      <div
                        key={index}
                        className={`wallpaper-option ${currentWallpaper === wallpaper ? "active" : ""}`}
                        style={{ backgroundImage: `url(${wallpaper})` }}
                        onClick={() => handleWallpaperChange(wallpaper)}
                      />
                    ))}
                  </div>

                  <div className="custom-wallpaper">
                    <label htmlFor="wallpaper-upload" className="upload-button">
                      Upload Custom Wallpaper
                    </label>
                    <input
                      id="wallpaper-upload"
                      type="file"
                      accept="image/*"
                      onChange={handleCustomWallpaperUpload}
                      style={{ display: "none" }}
                    />
                  </div>
                </div>

                <div className="settings-section">
                  <h3>Background Blur</h3>
                  <div className="slider-container">
                    <input
                      type="range"
                      min="0"
                      max="20"
                      value={blurIntensity}
                      onChange={(e) => handleBlurChange(Number.parseInt(e.target.value))}
                      className="blur-slider"
                    />
                    <span className="slider-value">{blurIntensity}px</span>
                  </div>
                </div>

                <div className="settings-section">
                  <h3>Accent Color</h3>
                  <div className="color-grid">
                    {accentColors.map((color, index) => (
                      <div
                        key={index}
                        className={`color-option ${accentColor === color ? "active" : ""}`}
                        style={{ backgroundColor: color }}
                        onClick={() => handleAccentColorChange(color)}
                      />
                    ))}
                  </div>
                  <input
                    type="color"
                    value={accentColor}
                    onChange={(e) => handleAccentColorChange(e.target.value)}
                    className="custom-color-picker"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {showCookieConsent && (
          <div className="cookie-overlay">
            <div className="cookieCard">
              <h2 className="cookieHeading">We use cookies</h2>
              <p className="cookieDescription">
                We use cookies to improve your experience on our site and to show you personalized content.
                <a href="/privacy" target="_blank" rel="noreferrer">
                  {" "}
                  Learn more
                </a>
              </p>
              <button className="acceptButton" onClick={handleAcceptCookies}>
                Accept All
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
