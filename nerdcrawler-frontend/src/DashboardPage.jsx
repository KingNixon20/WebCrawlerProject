"use client"

import { useState, useEffect } from "react"
import { AuroraText } from "./components/magicui/aurora-text"
import { useAuth } from "./auth/AuthContext"
import "./index.css"

export default function DashboardPage() {
  const { user, isAuthenticated, logout } = useAuth()
  const [userRatings, setUserRatings] = useState([])
  const [savedResults, setSavedResults] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [stats, setStats] = useState({
    totalRatings: 0,
    averageRating: 0,
    savedResults: 0,
    accountAge: 0,
  })

  // Admin panel states
  const [allUsers, setAllUsers] = useState([])
  const [showUserManagement, setShowUserManagement] = useState(false)
  const [isLoadingUsers, setIsLoadingUsers] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [newPrivilegeLevel, setNewPrivilegeLevel] = useState("")

  useEffect(() => {
    if (!isAuthenticated) {
      // Redirect to login if not authenticated
      window.history.pushState({}, "", "/login")
      window.dispatchEvent(new PopStateEvent("popstate"))
      return
    }

    fetchUserData()
  }, [isAuthenticated])

  const fetchUserData = async () => {
    try {
      setIsLoading(true)

      // Fetch user ratings
      const token = localStorage.getItem("authToken")
      if (token) {
        try {
          const response = await fetch("https://projectkryptos.xyz/api/user/ratings", {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          })

          if (response.ok) {
            const contentType = response.headers.get("content-type")
            if (contentType && contentType.includes("application/json")) {
              const data = await response.json()
              setUserRatings(data.ratings || [])

              // Calculate stats
              const totalRatings = (data.ratings || []).length
              const averageRating =
                totalRatings > 0 ? data.ratings.reduce((sum, rating) => sum + rating.rating, 0) / totalRatings : 0

              setStats((prev) => ({
                ...prev,
                totalRatings,
                averageRating: averageRating.toFixed(1),
              }))
            } else {
              console.log("Ratings API returned non-JSON response, using mock data")
              // Use mock data for now
              setUserRatings([])
              setStats((prev) => ({ ...prev, totalRatings: 0, averageRating: 0 }))
            }
          } else {
            console.log(`Ratings API returned ${response.status}, using mock data`)
            setUserRatings([])
            setStats((prev) => ({ ...prev, totalRatings: 0, averageRating: 0 }))
          }
        } catch (ratingsError) {
          console.log("Ratings API error, using mock data:", ratingsError.message)
          setUserRatings([])
          setStats((prev) => ({ ...prev, totalRatings: 0, averageRating: 0 }))
        }
      }

      // Load saved results from localStorage
      const saved = localStorage.getItem("savedResults")
      if (saved) {
        try {
          const parsedSaved = JSON.parse(saved)
          setSavedResults(parsedSaved)
          setStats((prev) => ({
            ...prev,
            savedResults: parsedSaved.length,
          }))
        } catch (parseError) {
          console.log("Error parsing saved results:", parseError)
          setSavedResults([])
          setStats((prev) => ({ ...prev, savedResults: 0 }))
        }
      }

      // Calculate account age (mock for now)
      setStats((prev) => ({
        ...prev,
        accountAge: Math.floor(Math.random() * 30) + 1, // Random days for demo
      }))
    } catch (error) {
      console.error("Error fetching user data:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchAllUsers = async () => {
    try {
      setIsLoadingUsers(true)
      const token = localStorage.getItem("authToken")

      const response = await fetch("https://projectkryptos.xyz/api/admin/users", {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      })

      if (response.ok) {
        const contentType = response.headers.get("content-type")
        if (contentType && contentType.includes("application/json")) {
          const data = await response.json()
          setAllUsers(data.users || [])
        } else {
          console.log("Admin users API returned non-JSON response")
          showNotification("⚠️ Admin API not yet implemented - using mock data", "info")
          // Use mock data for demonstration
          setAllUsers([
            {
              id: 1,
              username: "john_doe",
              email: "john@example.com",
              privilege_level: "user",
              created_at: "2024-01-15",
            },
            {
              id: 2,
              username: "jane_admin",
              email: "jane@example.com",
              privilege_level: "admin",
              created_at: "2024-01-10",
            },
            {
              id: 3,
              username: "bob_moderator",
              email: "bob@example.com",
              privilege_level: "moderator",
              created_at: "2024-01-20",
            },
          ])
        }
      } else if (response.status === 404) {
        console.log("Admin users API endpoint not found")
        showNotification("⚠️ Admin API not yet implemented - using mock data", "info")
        // Use mock data for demonstration
        setAllUsers([
          {
            id: 1,
            username: "john_doe",
            email: "john@example.com",
            privilege_level: "user",
            created_at: "2024-01-15",
          },
          {
            id: 2,
            username: "jane_admin",
            email: "jane@example.com",
            privilege_level: "admin",
            created_at: "2024-01-10",
          },
          {
            id: 3,
            username: "bob_moderator",
            email: "bob@example.com",
            privilege_level: "moderator",
            created_at: "2024-01-20",
          },
        ])
      } else {
        console.error("Failed to fetch users:", response.status, response.statusText)
        showNotification("❌ Failed to fetch users", "error")
      }
    } catch (error) {
      console.error("Error fetching users:", error)
      if (error.name === "TypeError" && error.message.includes("fetch")) {
        showNotification("⚠️ Admin API not available - using mock data", "info")
        // Use mock data when API is not available
        setAllUsers([
          {
            id: 1,
            username: "john_doe",
            email: "john@example.com",
            privilege_level: "user",
            created_at: "2024-01-15",
          },
          {
            id: 2,
            username: "jane_admin",
            email: "jane@example.com",
            privilege_level: "admin",
            created_at: "2024-01-10",
          },
          {
            id: 3,
            username: "bob_moderator",
            email: "bob@example.com",
            privilege_level: "moderator",
            created_at: "2024-01-20",
          },
        ])
      } else {
        showNotification("❌ Error fetching users", "error")
      }
    } finally {
      setIsLoadingUsers(false)
    }
  }

  const updateUserPrivileges = async (userId, newPrivilege) => {
    try {
      const token = localStorage.getItem("authToken")

      const response = await fetch(`https://projectkryptos.xyz/api/admin/users/${userId}/privileges`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ privilege_level: newPrivilege }),
      })

      if (response.ok) {
        const contentType = response.headers.get("content-type")
        if (contentType && contentType.includes("application/json")) {
          // Update local state
          setAllUsers((users) => users.map((u) => (u.id === userId ? { ...u, privilege_level: newPrivilege } : u)))
          setEditingUser(null)
          showNotification("✅ User privileges updated successfully", "success")
        } else {
          // API not implemented yet, just update local state for demo
          setAllUsers((users) => users.map((u) => (u.id === userId ? { ...u, privilege_level: newPrivilege } : u)))
          setEditingUser(null)
          showNotification("✅ User privileges updated (demo mode)", "success")
        }
      } else if (response.status === 404) {
        // API not implemented yet, just update local state for demo
        setAllUsers((users) => users.map((u) => (u.id === userId ? { ...u, privilege_level: newPrivilege } : u)))
        setEditingUser(null)
        showNotification("✅ User privileges updated (demo mode)", "success")
      } else {
        console.error("Failed to update user privileges:", response.status, response.statusText)
        showNotification("❌ Failed to update user privileges", "error")
      }
    } catch (error) {
      console.error("Error updating user privileges:", error)
      if (error.name === "TypeError" && error.message.includes("fetch")) {
        // API not available, just update local state for demo
        setAllUsers((users) => users.map((u) => (u.id === userId ? { ...u, privilege_level: newPrivilege } : u)))
        setEditingUser(null)
        showNotification("✅ User privileges updated (demo mode)", "success")
      } else {
        showNotification("❌ Error updating user privileges", "error")
      }
    }
  }

  const showNotification = (message, type = "info") => {
    const notification = document.createElement("div")
    notification.textContent = message
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: ${type === "error" ? "rgba(244, 67, 54, 0.9)" : "rgba(76, 175, 80, 0.9)"};
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      z-index: 10000;
      font-size: 14px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      animation: slideInRight 0.3s ease-out;
    `
    document.body.appendChild(notification)
    setTimeout(() => notification.remove(), 4000)
  }

  const handleGoHome = () => {
    window.history.pushState({}, "", "/")
    window.dispatchEvent(new PopStateEvent("popstate"))
  }

  const handleLogout = async () => {
    await logout()
    window.history.pushState({}, "", "/")
    window.dispatchEvent(new PopStateEvent("popstate"))
  }

  const handleShowUserManagement = () => {
    setShowUserManagement(true)
    fetchAllUsers()
  }

  const handleEditUser = (user) => {
    setEditingUser(user)
    setNewPrivilegeLevel(user.privilege_level)
  }

  const handleSaveUserEdit = () => {
    if (editingUser && newPrivilegeLevel) {
      updateUserPrivileges(editingUser.id, newPrivilegeLevel)
    }
  }

  const privilegeLevels = [
    { value: "user", label: "User", color: "#4fc3f7" },
    { value: "premium", label: "Premium", color: "#ff9800" },
    { value: "moderator", label: "Moderator", color: "#9c27b0" },
    { value: "admin", label: "Admin", color: "#f44336" },
    { value: "godmode", label: "God Mode", color: "#ffd700" },
  ]

  const getPrivilegeColor = (level) => {
    const privilege = privilegeLevels.find((p) => p.value === level)
    return privilege ? privilege.color : "#ccc"
  }

  const getPrivilegeLabel = (level) => {
    const privilege = privilegeLevels.find((p) => p.value === level)
    return privilege ? privilege.label : level
  }

  if (!isAuthenticated) {
    return null // Will redirect in useEffect
  }

  return (
    <div
      className="dashboard-page"
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
          <h1 style={{ margin: 0, fontSize: "2rem", fontWeight: "600" }}>Dashboard</h1>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <span style={{ color: "#ccc" }}>Welcome, {user?.username}!</span>
          {user?.privilege_level === "godmode" && (
            <span
              style={{
                color: "#ffd700",
                fontSize: "0.8rem",
                background: "rgba(255, 215, 0, 0.1)",
                padding: "0.25rem 0.5rem",
                borderRadius: "4px",
                border: "1px solid rgba(255, 215, 0, 0.3)",
              }}
            >
              👑 GOD MODE
            </span>
          )}
          <button
            onClick={handleLogout}
            style={{
              background: "rgba(255, 68, 68, 0.1)",
              border: "1px solid #ff4444",
              color: "#ff4444",
              padding: "0.5rem 1rem",
              borderRadius: "8px",
              cursor: "pointer",
              fontSize: "0.9rem",
            }}
          >
            Logout
          </button>
        </div>
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
          <p>Loading your dashboard...</p>
        </div>
      ) : (
        <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
          {/* God Mode Admin Panel */}
          {user?.privilege_level === "godmode" && (
            <div
              style={{
                background: "rgba(255, 215, 0, 0.1)",
                border: "1px solid rgba(255, 215, 0, 0.3)",
                borderRadius: "12px",
                padding: "1.5rem",
                marginBottom: "3rem",
              }}
            >
              <h2
                style={{
                  margin: "0 0 1rem",
                  color: "#ffd700",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                👑 Admin Panel
              </h2>
              <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                <button
                  onClick={handleShowUserManagement}
                  style={{
                    background: "rgba(255, 215, 0, 0.2)",
                    border: "1px solid #ffd700",
                    color: "#ffd700",
                    padding: "0.75rem 1.5rem",
                    borderRadius: "8px",
                    cursor: "pointer",
                    fontSize: "0.9rem",
                    fontWeight: "500",
                    transition: "all 0.2s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.background = "rgba(255, 215, 0, 0.3)"
                    e.target.style.transform = "translateY(-2px)"
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.background = "rgba(255, 215, 0, 0.2)"
                    e.target.style.transform = "translateY(0)"
                  }}
                >
                  👥 Manage Users
                </button>
                <button
                  onClick={() => {
                    window.history.pushState({}, "", "/analytics")
                    window.dispatchEvent(new PopStateEvent("popstate"))
                  }}
                  style={{
                    background: "rgba(255, 215, 0, 0.2)",
                    border: "1px solid #ffd700",
                    color: "#ffd700",
                    padding: "0.75rem 1.5rem",
                    borderRadius: "8px",
                    cursor: "pointer",
                    fontSize: "0.9rem",
                    fontWeight: "500",
                    transition: "all 0.2s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.background = "rgba(255, 215, 0, 0.3)"
                    e.target.style.transform = "translateY(-2px)"
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.background = "rgba(255, 215, 0, 0.2)"
                    e.target.style.transform = "translateY(0)"
                  }}
                >
                  📊 System Analytics
                </button>
              </div>
            </div>
          )}

          {/* User Management Modal */}
          {showUserManagement && (
            <div
              style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0, 0, 0, 0.8)",
                backdropFilter: "blur(8px)",
                zIndex: 2000,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              onClick={() => setShowUserManagement(false)}
            >
              <div
                style={{
                  background: "rgba(25, 25, 25, 0.95)",
                  backdropFilter: "blur(20px)",
                  borderRadius: "16px",
                  width: "min(90vw, 800px)",
                  maxHeight: "80vh",
                  overflow: "hidden",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  boxShadow: "0 20px 60px rgba(0, 0, 0, 0.5)",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "24px",
                    borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
                  }}
                >
                  <h2 style={{ margin: 0, color: "#fff", fontSize: "24px", fontWeight: "600" }}>👥 User Management</h2>
                  <button
                    onClick={() => setShowUserManagement(false)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#fff",
                      fontSize: "28px",
                      cursor: "pointer",
                      width: "32px",
                      height: "32px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      borderRadius: "8px",
                      transition: "background-color 0.2s ease",
                    }}
                    onMouseEnter={(e) => (e.target.style.background = "rgba(255, 255, 255, 0.1)")}
                    onMouseLeave={(e) => (e.target.style.background = "none")}
                  >
                    ×
                  </button>
                </div>

                <div style={{ padding: "24px", maxHeight: "calc(80vh - 100px)", overflowY: "auto" }}>
                  {isLoadingUsers ? (
                    <div style={{ textAlign: "center", padding: "2rem" }}>
                      <div
                        style={{
                          width: "30px",
                          height: "30px",
                          border: "3px solid rgba(255, 215, 0, 0.3)",
                          borderTop: "3px solid #ffd700",
                          borderRadius: "50%",
                          animation: "spin 1s linear infinite",
                          margin: "0 auto 1rem",
                        }}
                      ></div>
                      <p style={{ color: "#ccc" }}>Loading users...</p>
                    </div>
                  ) : (
                    <div style={{ display: "grid", gap: "1rem" }}>
                      {allUsers.map((userItem) => (
                        <div
                          key={userItem.id}
                          style={{
                            background: "rgba(255, 255, 255, 0.05)",
                            border: "1px solid rgba(255, 255, 255, 0.1)",
                            borderRadius: "8px",
                            padding: "1rem",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                          }}
                        >
                          <div>
                            <h4 style={{ margin: "0 0 0.5rem", color: "#fff" }}>{userItem.username}</h4>
                            <p style={{ margin: "0 0 0.5rem", color: "#ccc", fontSize: "0.9rem" }}>{userItem.email}</p>
                            <span
                              style={{
                                color: getPrivilegeColor(userItem.privilege_level),
                                fontSize: "0.8rem",
                                background: `${getPrivilegeColor(userItem.privilege_level)}20`,
                                padding: "0.25rem 0.5rem",
                                borderRadius: "4px",
                                border: `1px solid ${getPrivilegeColor(userItem.privilege_level)}40`,
                              }}
                            >
                              {getPrivilegeLabel(userItem.privilege_level)}
                            </span>
                          </div>
                          <button
                            onClick={() => handleEditUser(userItem)}
                            style={{
                              background: "rgba(79, 195, 247, 0.2)",
                              border: "1px solid #4fc3f7",
                              color: "#4fc3f7",
                              padding: "0.5rem 1rem",
                              borderRadius: "6px",
                              cursor: "pointer",
                              fontSize: "0.8rem",
                              transition: "all 0.2s ease",
                            }}
                            onMouseEnter={(e) => {
                              e.target.style.background = "rgba(79, 195, 247, 0.3)"
                            }}
                            onMouseLeave={(e) => {
                              e.target.style.background = "rgba(79, 195, 247, 0.2)"
                            }}
                          >
                            Edit Privileges
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Edit User Modal */}
          {editingUser && (
            <div
              style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0, 0, 0, 0.8)",
                backdropFilter: "blur(8px)",
                zIndex: 2001,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              onClick={() => setEditingUser(null)}
            >
              <div
                style={{
                  background: "rgba(25, 25, 25, 0.95)",
                  backdropFilter: "blur(20px)",
                  borderRadius: "16px",
                  width: "min(90vw, 400px)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  boxShadow: "0 20px 60px rgba(0, 0, 0, 0.5)",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "20px",
                    borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
                  }}
                >
                  <h3 style={{ margin: 0, color: "#fff" }}>Edit User Privileges</h3>
                  <button
                    onClick={() => setEditingUser(null)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#fff",
                      fontSize: "24px",
                      cursor: "pointer",
                    }}
                  >
                    ×
                  </button>
                </div>

                <div style={{ padding: "20px" }}>
                  <p style={{ color: "#ccc", marginBottom: "1rem" }}>
                    User: <strong style={{ color: "#fff" }}>{editingUser.username}</strong>
                  </p>

                  <label style={{ color: "#fff", display: "block", marginBottom: "0.5rem" }}>Privilege Level:</label>
                  <select
                    value={newPrivilegeLevel}
                    onChange={(e) => setNewPrivilegeLevel(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "0.75rem",
                      background: "rgba(255, 255, 255, 0.1)",
                      border: "1px solid rgba(255, 255, 255, 0.2)",
                      borderRadius: "6px",
                      color: "#fff",
                      fontSize: "1rem",
                      marginBottom: "1.5rem",
                    }}
                  >
                    {privilegeLevels.map((level) => (
                      <option key={level.value} value={level.value} style={{ background: "#333" }}>
                        {level.label}
                      </option>
                    ))}
                  </select>

                  <div style={{ display: "flex", gap: "1rem", justifyContent: "flex-end" }}>
                    <button
                      onClick={() => setEditingUser(null)}
                      style={{
                        background: "rgba(255, 255, 255, 0.1)",
                        border: "1px solid rgba(255, 255, 255, 0.2)",
                        color: "#fff",
                        padding: "0.75rem 1.5rem",
                        borderRadius: "6px",
                        cursor: "pointer",
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveUserEdit}
                      style={{
                        background: "#4fc3f7",
                        border: "none",
                        color: "#fff",
                        padding: "0.75rem 1.5rem",
                        borderRadius: "6px",
                        cursor: "pointer",
                        fontWeight: "500",
                      }}
                    >
                      Save Changes
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Stats Cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
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
              <h3 style={{ margin: "0 0 0.5rem", color: "#4fc3f7" }}>Total Ratings</h3>
              <p style={{ fontSize: "2rem", fontWeight: "bold", margin: 0 }}>{stats.totalRatings}</p>
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
              <h3 style={{ margin: "0 0 0.5rem", color: "#4caf50" }}>Average Rating</h3>
              <p style={{ fontSize: "2rem", fontWeight: "bold", margin: 0 }}>{stats.averageRating}⭐</p>
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
              <h3 style={{ margin: "0 0 0.5rem", color: "#ff9800" }}>Saved Results</h3>
              <p style={{ fontSize: "2rem", fontWeight: "bold", margin: 0 }}>{stats.savedResults}</p>
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
              <h3 style={{ margin: "0 0 0.5rem", color: "#9c27b0" }}>Account Age</h3>
              <p style={{ fontSize: "2rem", fontWeight: "bold", margin: 0 }}>{stats.accountAge} days</p>
            </div>
          </div>

          {/* Recent Activity */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "2rem",
              "@media (max-width: 768px)": {
                gridTemplateColumns: "1fr",
              },
            }}
          >
            {/* Recent Ratings */}
            <div
              style={{
                background: "rgba(20, 20, 20, 0.8)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                borderRadius: "12px",
                padding: "1.5rem",
              }}
            >
              <h3 style={{ margin: "0 0 1rem", color: "#4fc3f7" }}>Recent Ratings</h3>
              {userRatings.length > 0 ? (
                <div style={{ maxHeight: "300px", overflowY: "auto" }}>
                  {userRatings.slice(0, 5).map((rating, index) => (
                    <div
                      key={index}
                      style={{
                        padding: "0.75rem",
                        borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                        marginBottom: "0.5rem",
                      }}
                    >
                      <div style={{ fontSize: "0.9rem", color: "#ccc", marginBottom: "0.25rem" }}>
                        {new URL(rating.url).hostname}
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "1.2rem" }}>{"⭐".repeat(rating.rating)}</span>
                        <span style={{ fontSize: "0.8rem", color: "#888" }}>
                          {new Date(rating.updated_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: "#888", textAlign: "center", padding: "2rem" }}>
                  No ratings yet. Start rating search results!
                </p>
              )}
            </div>

            {/* Saved Results */}
            <div
              style={{
                background: "rgba(20, 20, 20, 0.8)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                borderRadius: "12px",
                padding: "1.5rem",
              }}
            >
              <h3 style={{ margin: "0 0 1rem", color: "#ff9800" }}>Saved Results</h3>
              {savedResults.length > 0 ? (
                <div style={{ maxHeight: "300px", overflowY: "auto" }}>
                  {savedResults.slice(0, 5).map((result, index) => (
                    <div
                      key={index}
                      style={{
                        padding: "0.75rem",
                        borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                        marginBottom: "0.5rem",
                      }}
                    >
                      <div style={{ fontSize: "0.9rem", color: "#ff9800", marginBottom: "0.25rem" }}>
                        {result.title}
                      </div>
                      <div style={{ fontSize: "0.8rem", color: "#888" }}>
                        Saved {new Date(result.savedAt).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: "#888", textAlign: "center", padding: "2rem" }}>
                  No saved results yet. Save interesting results while searching!
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
