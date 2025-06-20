import { type NextRequest, NextResponse } from "next/server"
import { VisitorTracker } from "@/lib/visitor-tracker"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { query, results_count, search_type } = body

    if (!query) {
      return NextResponse.json({ error: "Query is required" }, { status: 400 })
    }

    // Get client IP
    const forwarded = request.headers.get("x-forwarded-for")
    const ip = forwarded ? forwarded.split(",")[0].trim() : "127.0.0.1"

    // Track the search
    const success = await VisitorTracker.trackSearch({
      query,
      ip_address: ip,
      results_count: results_count || 0,
      search_type: search_type || "web",
      username: "Anonymous", // You can get this from auth context
    })

    if (success) {
      return NextResponse.json({ success: true })
    } else {
      return NextResponse.json({ error: "Failed to track search" }, { status: 500 })
    }
  } catch (error) {
    console.error("Search tracking error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
