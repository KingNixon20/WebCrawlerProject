import { type NextRequest, NextResponse } from "next/server"
import { analyticsQueries, initializeDatabase } from "@/lib/database"

export async function GET(request: NextRequest) {
  try {
    // Initialize database if needed
    await initializeDatabase()

    const stats = await analyticsQueries.getCrawlStats()

    const response = {
      success: true,
      stats,
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error("Crawl stats error:", error)
    return NextResponse.json(
      {
        error: "Failed to fetch crawl statistics",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 },
    )
  }
}
