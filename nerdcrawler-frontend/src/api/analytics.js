// Mock API functions - replace with actual database calls
const mockCrawledData = {
  hourly: Array.from({ length: 24 }, (_, i) => ({
    hour: i,
    count: Math.floor(Math.random() * 100) + 20,
    timestamp: new Date(Date.now() - (23 - i) * 60 * 60 * 1000).toISOString(),
  })),
  daily: Array.from({ length: 30 }, (_, i) => ({
    day: i + 1,
    count: Math.floor(Math.random() * 2000) + 500,
    date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString(),
  })),
  weekly: Array.from({ length: 12 }, (_, i) => ({
    week: i + 1,
    count: Math.floor(Math.random() * 10000) + 2000,
    startDate: new Date(Date.now() - (11 - i) * 7 * 24 * 60 * 60 * 1000).toISOString(),
  })),
}

const mockLatestUrls = Array.from({ length: 100 }, (_, i) => ({
  id: i + 1,
  url: `https://example${i % 10}.com/page-${i}`,
  title: `Example Page ${i + 1} - Lorem ipsum dolor sit amet`,
  crawledAt: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
  status: ["success", "error", "pending"][Math.floor(Math.random() * 3)],
  responseTime: Math.floor(Math.random() * 2000) + 100,
  contentLength: Math.floor(Math.random() * 50000) + 1000,
  domain: `example${i % 10}.com`,
}))

export const fetchCrawlAnalytics = async (timeframe = "daily") => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 500))

  return {
    success: true,
    data: mockCrawledData[timeframe] || mockCrawledData.daily,
    summary: {
      total: mockCrawledData[timeframe]?.reduce((sum, item) => sum + item.count, 0) || 0,
      average:
        Math.floor(
          mockCrawledData[timeframe]?.reduce((sum, item) => sum + item.count, 0) / mockCrawledData[timeframe]?.length,
        ) || 0,
      peak: Math.max(...(mockCrawledData[timeframe]?.map((item) => item.count) || [0])),
    },
  }
}

export const fetchLatestCrawledUrls = async (page = 1, limit = 20, filters = {}) => {
  await new Promise((resolve) => setTimeout(resolve, 300))

  let filteredUrls = [...mockLatestUrls]

  // Apply filters
  if (filters.status && filters.status !== "all") {
    filteredUrls = filteredUrls.filter((url) => url.status === filters.status)
  }

  if (filters.domain) {
    filteredUrls = filteredUrls.filter((url) => url.domain.includes(filters.domain))
  }

  if (filters.dateRange) {
    const now = new Date()
    const cutoff = new Date(now.getTime() - filters.dateRange * 24 * 60 * 60 * 1000)
    filteredUrls = filteredUrls.filter((url) => new Date(url.crawledAt) >= cutoff)
  }

  // Sort by crawled date (newest first)
  filteredUrls.sort((a, b) => new Date(b.crawledAt) - new Date(a.crawledAt))

  const startIndex = (page - 1) * limit
  const endIndex = startIndex + limit
  const paginatedUrls = filteredUrls.slice(startIndex, endIndex)

  return {
    success: true,
    data: paginatedUrls,
    pagination: {
      currentPage: page,
      totalPages: Math.ceil(filteredUrls.length / limit),
      totalItems: filteredUrls.length,
      itemsPerPage: limit,
    },
  }
}

export const fetchCrawlStats = async () => {
  await new Promise((resolve) => setTimeout(resolve, 200))

  return {
    success: true,
    stats: {
      totalUrls: 1250000,
      todayUrls: 15420,
      activeWorkers: 8,
      queueSize: 2340,
      avgResponseTime: 850,
      successRate: 94.2,
      errorRate: 5.8,
      domainsCount: 45000,
      lastCrawlTime: new Date().toISOString(),
    },
  }
}
