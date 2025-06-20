import { type NextRequest, NextResponse } from "next/server"
import { analyticsQueries, initializeDatabase } from "../../../lib/database"

export async function GET(request: NextRequest) {
  try {
    // Initialize database if needed
    await initializeDatabase()

    // Get daily and weekly stats
    const dailyStats = await analyticsQueries.getVisitorStats(1)
    const weeklyStats = await analyticsQueries.getVisitorStats(7)

    // Get top pages and countries
    const topPages = await analyticsQueries.getTopPages(7)
    const topCountries = await analyticsQueries.getTopCountries(7)
    const topBrowsers = await analyticsQueries.getTopBrowsers(7)

    // Get recent visits
    const recentVisits = await analyticsQueries.getRecentVisits(50)

    const response = {
      stats: {
        daily: dailyStats,
        weekly: weeklyStats,
      },
      top_pages: topPages,
      top_countries: topCountries,
      top_browsers: topBrowsers,
      recent_visits: recentVisits,
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error("Analytics dashboard error:", error)
    return NextResponse.json(
      {
        error: "Failed to fetch analytics data",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 },
    )
  }
}
