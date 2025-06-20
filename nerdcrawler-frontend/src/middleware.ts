import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"
import { query } from "./lib/database"

// Helper function to get client IP
function getClientIP(request: NextRequest): string {
  const forwarded = request.headers.get("x-forwarded-for")
  const realIP = request.headers.get("x-real-ip")

  if (forwarded) {
    return forwarded.split(",")[0].trim()
  }

  if (realIP) {
    return realIP
  }

  return "127.0.0.1"
}

// Helper function to parse user agent
function parseUserAgent(userAgent: string) {
  const browser = userAgent.includes("Chrome")
    ? "Chrome"
    : userAgent.includes("Firefox")
      ? "Firefox"
      : userAgent.includes("Safari")
        ? "Safari"
        : userAgent.includes("Edge")
          ? "Edge"
          : userAgent.includes("Opera")
            ? "Opera"
            : "Unknown"

  const deviceType = userAgent.includes("Mobile") ? "Mobile" : userAgent.includes("Tablet") ? "Tablet" : "Desktop"

  return { browser, deviceType }
}

// Helper function to get location from IP (simplified)
function getLocationFromIP(ip: string): string {
  // In a real implementation, you'd use a GeoIP service
  // For now, return a default location
  if (ip.startsWith("192.168.") || ip.startsWith("10.") || ip.startsWith("172.")) {
    return "Local Network"
  }
  return "Unknown"
}

// Track website visits
async function trackVisit(request: NextRequest) {
  try {
    const ip = getClientIP(request)
    const userAgent = request.headers.get("user-agent") || ""
    const { browser, deviceType } = parseUserAgent(userAgent)
    const location = getLocationFromIP(ip)
    const pagePath = request.nextUrl.pathname
    const referrer = request.headers.get("referer")

    // Skip tracking for API routes, static files, and analytics page
    if (
      pagePath.startsWith("/api/") ||
      pagePath.startsWith("/_next/") ||
      pagePath.includes(".") ||
      pagePath === "/analytics"
    ) {
      return
    }

    // Generate a simple session ID
    const sessionId = `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    await query(
      `
      INSERT INTO website_visits (
        ip_address, user_agent, page_path, referrer, username, 
        location, device_type, browser, session_id
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    `,
      [
        ip,
        userAgent,
        pagePath,
        referrer,
        "Anonymous", // You can extract this from auth if available
        location,
        deviceType,
        browser,
        sessionId,
      ],
    )

    console.log(`📊 Tracked visit: ${ip} -> ${pagePath}`)
  } catch (error) {
    // Don't let tracking errors break the app
    console.error("Visit tracking error:", error)
  }
}

export async function middleware(request: NextRequest) {
  // Track the visit in the background
  trackVisit(request).catch(console.error)

  // Continue with the request
  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
}
