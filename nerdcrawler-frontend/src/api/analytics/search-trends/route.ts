import { type NextRequest, NextResponse } from "next/server"
import { analyticsQueries } from "@/lib/database"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const period = searchParams.get("period") || "7d"

    const trends = await analyticsQueries.getSearchTrends(period)

    // Format data for charts
    const chartData = {
      labels: trends.map((t) => t.period),
      values: trends.map((t) => Number.parseInt(t.searches)),
    }

    return NextResponse.json(chartData)
  } catch (error) {
    console.error("Search trends error:", error)
    return NextResponse.json({ error: "Failed to fetch search trends" }, { status: 500 })
  }
}
