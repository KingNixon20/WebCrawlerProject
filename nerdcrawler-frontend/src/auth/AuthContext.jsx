"use client"

import { createContext, useContext, useState, useEffect } from "react"

const AuthContext = createContext(null)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // API Base URL - adjust this to match your backend
  const API_BASE_URL = "https://projectkryptos.xyz"

  // Check if user is logged in on app start
  useEffect(() => {
    checkAuthStatus()
  }, [])

  const checkAuthStatus = async () => {
    try {
      const token = localStorage.getItem("authToken")
      if (!token) {
        setIsLoading(false)
        return
      }

      console.log("Verifying token with backend...")
      const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      })

      if (response.ok) {
        const userData = await response.json()
        console.log("Token verified successfully:", userData)
        setUser({
          ...userData.user,
          privilege_level: userData.user.privilege_level,
        })
        setIsAuthenticated(true)
      } else {
        console.log("Token verification failed:", response.status, response.statusText)
        // Token is invalid, remove it
        localStorage.removeItem("authToken")
        setUser(null)
        setIsAuthenticated(false)
      }
    } catch (error) {
      console.error("Auth check failed:", error)
      localStorage.removeItem("authToken")
      setUser(null)
      setIsAuthenticated(false)
    } finally {
      setIsLoading(false)
    }
  }

  const login = async (username, password) => {
    try {
      console.log("Attempting login for:", username)
      console.log("API URL:", `${API_BASE_URL}/api/auth/login`)

      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      })

      console.log("Login response status:", response.status)
      console.log("Login response headers:", Object.fromEntries(response.headers.entries()))

      if (!response.ok) {
        // Handle HTTP errors
        let errorMessage = `Login failed with status ${response.status}`

        try {
          const errorData = await response.json()
          errorMessage = errorData.message || errorMessage
        } catch (jsonError) {
          // If response is not JSON, use the status text
          errorMessage = response.statusText || errorMessage
        }

        console.error("Login failed:", errorMessage)
        return { success: false, error: errorMessage }
      }

      // Parse successful response
      const data = await response.json()
      console.log("Login successful:", data)

      // Store token and user data
      localStorage.setItem("authToken", data.token)
      setUser({
        ...data.user,
        privilege_level: data.user.privilege_level,
      })
      setIsAuthenticated(true)

      return { success: true, user: data.user }
    } catch (error) {
      console.error("Login network error:", error)

      // Provide specific error messages based on error type
      let errorMessage = "Network error. Please try again."

      if (error.name === "TypeError" && error.message.includes("fetch")) {
        errorMessage = "Unable to connect to server. Please check your internet connection."
      } else if (error.name === "SyntaxError" && error.message.includes("JSON")) {
        errorMessage = "Server returned invalid response. Please try again."
      }

      return { success: false, error: errorMessage }
    }
  }

  const signup = async (username, email, password) => {
    try {
      console.log("Attempting signup for:", username, email)
      console.log("API URL:", `${API_BASE_URL}/api/auth/signup`)

      const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, email, password }),
      })

      console.log("Signup response status:", response.status)

      if (!response.ok) {
        // Handle HTTP errors
        let errorMessage = `Signup failed with status ${response.status}`

        try {
          const errorData = await response.json()
          errorMessage = errorData.message || errorMessage
        } catch (jsonError) {
          errorMessage = response.statusText || errorMessage
        }

        console.error("Signup failed:", errorMessage)
        return { success: false, error: errorMessage }
      }

      // Parse successful response
      const data = await response.json()
      console.log("Signup successful:", data)

      return { success: true, message: data.message || "Account created successfully! Please log in." }
    } catch (error) {
      console.error("Signup network error:", error)

      let errorMessage = "Network error. Please try again."

      if (error.name === "TypeError" && error.message.includes("fetch")) {
        errorMessage = "Unable to connect to server. Please check your internet connection."
      } else if (error.name === "SyntaxError" && error.message.includes("JSON")) {
        errorMessage = "Server returned invalid response. Please try again."
      }

      return { success: false, error: errorMessage }
    }
  }

  const logout = async () => {
    try {
      const token = localStorage.getItem("authToken")
      if (token) {
        console.log("Attempting logout...")

        try {
          const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          })

          if (response.ok) {
            console.log("Server logout successful")
          } else {
            console.log("Server logout failed, but continuing with local logout")
          }
        } catch (error) {
          console.log("Server logout request failed, continuing with local logout:", error)
        }
      }
    } catch (error) {
      console.error("Logout error:", error)
    } finally {
      // Always clear local state regardless of server response
      localStorage.removeItem("authToken")
      setUser(null)
      setIsAuthenticated(false)
      console.log("Local logout completed")
    }
  }

  const value = {
    user,
    isAuthenticated,
    isLoading,
    login,
    signup,
    logout,
    checkAuthStatus,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
