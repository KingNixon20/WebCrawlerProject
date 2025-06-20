import { type NextRequest, NextResponse } from "next/server"
import { analyticsQueries } from "@/lib/database"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const days = Number.parseInt(searchParams.get("days") || "7")

    const visitorTrends = await analyticsQueries.getVisitorTrends(days)
    const searchTrends = await analyticsQueries.getSearchTrends(`${days}d`)

    // Combine and format data
    const chartData = {
      days: visitorTrends.map((t) => t.date),
      visitors: visitorTrends.map((t) => Number.parseInt(t.visitors)),
      searches: searchTrends.map((t) => Number.parseInt(t.searches)),
    }

    return NextResponse.json(chartData)
  } catch (error) {
    console.error("Combined trends error:", error)
    return NextResponse.json({ error: "Failed to fetch combined trends" }, { status: 500 })
  }
}
