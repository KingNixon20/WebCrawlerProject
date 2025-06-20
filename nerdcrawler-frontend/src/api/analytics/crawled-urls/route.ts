import { type NextRequest, NextResponse } from "next/server"
import { analyticsQueries } from "@/lib/database"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const page = Number.parseInt(searchParams.get("page") || "1")
    const limit = Number.parseInt(searchParams.get("limit") || "20")

    const filters = {
      status: searchParams.get("status") || "all",
      domain: searchParams.get("domain") || "",
      dateRange: Number.parseInt(searchParams.get("dateRange") || "7"),
    }

    const result = await analyticsQueries.getCrawledUrls(page, limit, filters)

    const response = {
      success: true,
      urls: result.urls,
      pagination: {
        currentPage: page,
        totalPages: Math.ceil(result.total / limit),
        totalItems: result.total,
        itemsPerPage: limit,
      },
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error("Crawled URLs error:", error)
    return NextResponse.json({ error: "Failed to fetch crawled URLs" }, { status: 500 })
  }
}
