import { type NextRequest, NextResponse } from "next/server"
import { analyticsQueries } from "@/lib/database"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const days = Number.parseInt(searchParams.get("days") || "7")

    const trends = await analyticsQueries.getVisitorTrends(days)

    // Format data for charts
    const chartData = {
      days: trends.map((t) => t.date),
      visitors: trends.map((t) => Number.parseInt(t.visitors)),
    }

    return NextResponse.json(chartData)
  } catch (error) {
    console.error("Visitor trends error:", error)
    return NextResponse.json({ error: "Failed to fetch visitor trends" }, { status: 500 })
  }
}
