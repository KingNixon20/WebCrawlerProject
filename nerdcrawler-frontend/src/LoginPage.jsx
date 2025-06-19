"use client"

import { useState } from "react"
import { AuroraText } from "./components/magicui/aurora-text"
import { useAuth } from "./auth/AuthContext"
import "./login.css"

export default function LoginPage() {
  const authContext = useAuth()
  console.log("Auth context received:", authContext)
  const { login, signup, isLoading: authLoading } = authContext
  console.log("Login function:", typeof login, login)
  console.log("Signup function:", typeof signup, signup)
  const [isSignup, setIsSignup] = useState(false)
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  })
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState({})
  const [successMessage, setSuccessMessage] = useState("")

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors((prev) => ({
        ...prev,
        [name]: "",
      }))
    }
    // Clear success message when user starts typing
    if (successMessage) {
      setSuccessMessage("")
    }
  }

  const validateForm = () => {
    const newErrors = {}

    if (!formData.username.trim()) {
      newErrors.username = "Username is required"
    } else if (formData.username.length < 3) {
      newErrors.username = "Username must be at least 3 characters"
    }

    if (isSignup && !formData.email.trim()) {
      newErrors.email = "Email is required"
    } else if (isSignup && !/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = "Email is invalid"
    }

    if (!formData.password) {
      newErrors.password = "Password is required"
    } else if (formData.password.length < 6) {
      newErrors.password = "Password must be at least 6 characters"
    }

    if (isSignup && formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!validateForm()) return

    setIsLoading(true)
    setErrors({})

    try {
      if (isSignup) {
        const result = await signup(formData.username, formData.email, formData.password)

        if (result.success) {
          setSuccessMessage("Account created successfully! Please log in.")
          setIsSignup(false)
          setFormData({ username: formData.username, email: "", password: "", confirmPassword: "" })
        } else {
          setErrors({ general: result.error })
        }
      } else {
        const result = await login(formData.username, formData.password)

        if (result.success) {
          // Show success message briefly before redirecting
          setSuccessMessage("Login successful! Redirecting...")
          setTimeout(() => {
            window.history.pushState({}, "", "/")
            window.dispatchEvent(new PopStateEvent("popstate"))
          }, 1500)
        } else {
          setErrors({ general: result.error })
        }
      }
    } catch (error) {
      console.error("Authentication error:", error)
      setErrors({ general: "An unexpected error occurred. Please try again." })
    } finally {
      setIsLoading(false)
    }
  }

  const toggleMode = () => {
    setIsSignup(!isSignup)
    setFormData({ username: "", email: "", password: "", confirmPassword: "" })
    setErrors({})
    setSuccessMessage("")
  }

  return (
    <div className="login-page">
      <div className="login-background"></div>

      <div className="login-container">
        {/* Header */}
        <div className="login-header">
          <a
            href="#"
            className="login-logo"
            onClick={(e) => {
              e.preventDefault()
              window.history.pushState({}, "", "/")
              window.dispatchEvent(new PopStateEvent("popstate"))
            }}
          >
            <span className="nerd">Nerd</span>
            <AuroraText className="crawler">Crawler</AuroraText>
          </a>
          <p className="login-subtitle">{isSignup ? "Create your account" : "Welcome back"}</p>
        </div>

        {/* Form */}
        <form className="login-form" onSubmit={handleSubmit}>
          {errors.general && <div className="error-message general-error">{errors.general}</div>}
          {successMessage && <div className="success-message">{successMessage}</div>}

          {/* Username Field */}
          <div className="input-group">
            <div className={`input-wrapper ${formData.username ? "has-value" : ""} ${errors.username ? "error" : ""}`}>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                className="form-input"
                required
                disabled={isLoading}
              />
              <label className="form-label">Username</label>
              <div className="input-border"></div>
            </div>
            {errors.username && <span className="error-message">{errors.username}</span>}
          </div>

          {/* Email Field (Signup only) */}
          {isSignup && (
            <div className="input-group">
              <div className={`input-wrapper ${formData.email ? "has-value" : ""} ${errors.email ? "error" : ""}`}>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  className="form-input"
                  required
                  disabled={isLoading}
                />
                <label className="form-label">Email</label>
                <div className="input-border"></div>
              </div>
              {errors.email && <span className="error-message">{errors.email}</span>}
            </div>
          )}

          {/* Password Field */}
          <div className="input-group">
            <div className={`input-wrapper ${formData.password ? "has-value" : ""} ${errors.password ? "error" : ""}`}>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                className="form-input"
                required
                disabled={isLoading}
              />
              <label className="form-label">Password</label>
              <div className="input-border"></div>
            </div>
            {errors.password && <span className="error-message">{errors.password}</span>}
          </div>

          {/* Confirm Password Field (Signup only) */}
          {isSignup && (
            <div className="input-group">
              <div
                className={`input-wrapper ${formData.confirmPassword ? "has-value" : ""} ${errors.confirmPassword ? "error" : ""}`}
              >
                <input
                  type="password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleInputChange}
                  className="form-input"
                  required
                  disabled={isLoading}
                />
                <label className="form-label">Confirm Password</label>
                <div className="input-border"></div>
              </div>
              {errors.confirmPassword && <span className="error-message">{errors.confirmPassword}</span>}
            </div>
          )}

          {/* Submit Button */}
          <button type="submit" className={`submit-button ${isLoading ? "loading" : ""}`} disabled={isLoading}>
            <span className="button-text">
              {isLoading ? (
                <>
                  <div className="loading-spinner"></div>
                  {isSignup ? "Creating Account..." : "Signing In..."}
                </>
              ) : isSignup ? (
                "Create Account"
              ) : (
                "Sign In"
              )}
            </span>
          </button>

          {/* Toggle Mode */}
          <div className="form-footer">
            <p className="toggle-text">
              {isSignup ? "Already have an account?" : "Don't have an account?"}
              <button type="button" className="toggle-button" onClick={toggleMode} disabled={isLoading}>
                {isSignup ? "Sign In" : "Sign Up"}
              </button>
            </p>
          </div>

          {/* Additional Options */}
          {!isSignup && (
            <div className="additional-options">
              <button type="button" className="forgot-password" disabled={isLoading}>
                Forgot Password?
              </button>
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="login-footer">
          <p>&copy; 2024 NerdCrawler. All rights reserved.</p>
        </div>
      </div>
    </div>
  )
}
