import { type NextRequest, NextResponse } from "next/server"
import { analyticsQueries } from "@/lib/database"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const timeframe = searchParams.get("timeframe") || "daily"

    const data = await analyticsQueries.getCrawlVolume(timeframe)

    // Calculate summary statistics
    const counts = data.map((d) => Number.parseInt(d.count))
    const total = counts.reduce((sum, count) => sum + count, 0)
    const average = Math.floor(total / counts.length) || 0
    const peak = Math.max(...counts) || 0

    const response = {
      success: true,
      data: data.map((item, index) => ({
        ...item,
        count: Number.parseInt(item.count),
        // Add index-based identifiers for chart display
        hour: timeframe === "hourly" ? new Date(item.hour).getHours() : undefined,
        day: timeframe === "daily" ? index + 1 : undefined,
        week: timeframe === "weekly" ? index + 1 : undefined,
      })),
      summary: {
        total,
        average,
        peak,
      },
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error("Crawl volume error:", error)
    return NextResponse.json({ error: "Failed to fetch crawl volume data" }, { status: 500 })
  }
}
