import { Pool } from "pg"

// Create a connection pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === "production" ? { rejectUnauthorized: false } : false,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
})

// Helper function to execute queries with better error handling
export async function query(text: string, params?: any[]) {
  const client = await pool.connect()
  try {
    const result = await client.query(text, params)
    return result
  } catch (error) {
    console.error("Database query error:", error)
    throw error
  } finally {
    client.release()
  }
}

// Initialize database tables and indexes
export async function initializeDatabase() {
  console.log("🔧 Initializing analytics database...")

  try {
    // Create tables if they don't exist
    await createTables()
    await createIndexes()
    await seedSampleData()
    console.log("✅ Database initialization completed")
    return true
  } catch (error) {
    console.error("❌ Database initialization failed:", error)
    return false
  }
}

// Create all analytics tables
async function createTables() {
  const tables = [
    {
      name: "website_visits",
      query: `
        CREATE TABLE IF NOT EXISTS website_visits (
          id SERIAL PRIMARY KEY,
          ip_address INET NOT NULL,
          user_agent TEXT,
          page_path VARCHAR(500) NOT NULL,
          referrer VARCHAR(500),
          visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          username VARCHAR(100),
          location VARCHAR(100),
          device_type VARCHAR(50),
          browser VARCHAR(100),
          session_id VARCHAR(100)
        );
      `,
    },
    {
      name: "search_queries",
      query: `
        CREATE TABLE IF NOT EXISTS search_queries (
          id SERIAL PRIMARY KEY,
          query TEXT NOT NULL,
          user_id INTEGER,
          username VARCHAR(100),
          ip_address INET,
          search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          results_count INTEGER DEFAULT 0,
          search_type VARCHAR(50) DEFAULT 'web'
        );
      `,
    },
    {
      name: "crawled_websites",
      query: `
        CREATE TABLE IF NOT EXISTS crawled_websites (
          id SERIAL PRIMARY KEY,
          url TEXT NOT NULL UNIQUE,
          title TEXT,
          description TEXT,
          content TEXT,
          crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          status VARCHAR(20) DEFAULT 'success',
          response_time INTEGER,
          content_length INTEGER,
          domain VARCHAR(255),
          http_status_code INTEGER
        );
      `,
    },
    {
      name: "result_ratings",
      query: `
        CREATE TABLE IF NOT EXISTS result_ratings (
          id SERIAL PRIMARY KEY,
          user_id INTEGER,
          username VARCHAR(100),
          url TEXT NOT NULL,
          rating INTEGER CHECK (rating >= 1 AND rating <= 5),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
      `,
    },
  ]

  for (const table of tables) {
    try {
      await query(table.query)
      console.log(`  ✅ Table ready: ${table.name}`)
    } catch (error) {
      console.error(`  ❌ Failed to create table ${table.name}:`, error)
      throw error
    }
  }
}

// Create database indexes
async function createIndexes() {
  const indexes = [
    "CREATE INDEX IF NOT EXISTS idx_website_visits_time ON website_visits(visit_time);",
    "CREATE INDEX IF NOT EXISTS idx_website_visits_ip ON website_visits(ip_address);",
    "CREATE INDEX IF NOT EXISTS idx_website_visits_page ON website_visits(page_path);",
    "CREATE INDEX IF NOT EXISTS idx_search_queries_time ON search_queries(search_time);",
    "CREATE INDEX IF NOT EXISTS idx_search_queries_user ON search_queries(username);",
    "CREATE INDEX IF NOT EXISTS idx_crawled_websites_domain ON crawled_websites(domain);",
    "CREATE INDEX IF NOT EXISTS idx_crawled_websites_time ON crawled_websites(crawled_at);",
    "CREATE INDEX IF NOT EXISTS idx_result_ratings_url ON result_ratings(url);",
    "CREATE INDEX IF NOT EXISTS idx_result_ratings_user ON result_ratings(username);",
  ]

  for (const indexQuery of indexes) {
    try {
      await query(indexQuery)
    } catch (error) {
      console.error("Index creation error (non-critical):", error.message)
    }
  }
  console.log("  ✅ Database indexes ready")
}

// Seed sample data if tables are empty
async function seedSampleData() {
  try {
    // Check if we already have data
    const visitCount = await query("SELECT COUNT(*) as count FROM website_visits")
    if (visitCount.rows[0].count > 0) {
      console.log("  ℹ️  Sample data already exists, skipping seed")
      return
    }

    console.log("  🌱 Seeding sample data...")

    // Sample website visits
    const sampleVisits = [
      ["192.168.1.100", "/", "john_doe", "United States", "Desktop", "Chrome", "NOW() - INTERVAL '1 hour'"],
      ["10.0.0.50", "/search", "jane_smith", "Canada", "Mobile", "Safari", "NOW() - INTERVAL '2 hours'"],
      ["172.16.0.25", "/", "Anonymous", "United Kingdom", "Desktop", "Firefox", "NOW() - INTERVAL '3 hours'"],
      ["192.168.1.200", "/search", "bob_wilson", "Germany", "Tablet", "Edge", "NOW() - INTERVAL '4 hours'"],
      ["10.0.0.75", "/", "alice_brown", "France", "Desktop", "Chrome", "NOW() - INTERVAL '5 hours'"],
    ]

    for (const visit of sampleVisits) {
      await query(
        `
        INSERT INTO website_visits (ip_address, page_path, username, location, device_type, browser, visit_time)
        VALUES ($1, $2, $3, $4, $5, $6, ${visit[6]})
      `,
        visit.slice(0, 6),
      )
    }

    // Sample search queries
    const sampleSearches = [
      ["artificial intelligence", "john_doe", "192.168.1.100", 1250, "NOW() - INTERVAL '1 hour'"],
      ["machine learning tutorials", "jane_smith", "10.0.0.50", 890, "NOW() - INTERVAL '2 hours'"],
      ["python programming", "Anonymous", "172.16.0.25", 2100, "NOW() - INTERVAL '3 hours'"],
      ["web development", "bob_wilson", "192.168.1.200", 1750, "NOW() - INTERVAL '4 hours'"],
      ["database design", "alice_brown", "10.0.0.75", 650, "NOW() - INTERVAL '5 hours'"],
    ]

    for (const search of sampleSearches) {
      await query(
        `
        INSERT INTO search_queries (query, username, ip_address, results_count, search_time)
        VALUES ($1, $2, $3, $4, ${search[4]})
      `,
        search.slice(0, 4),
      )
    }

    // Sample crawled websites
    const sampleWebsites = [
      [
        "https://example.com",
        "Example Domain",
        "This domain is for use in illustrative examples",
        "example.com",
        "success",
        250,
        1256,
        200,
      ],
      ["https://github.com", "GitHub", "Where the world builds software", "github.com", "success", 180, 45000, 200],
      [
        "https://stackoverflow.com",
        "Stack Overflow",
        "Where developers learn, share, & build careers",
        "stackoverflow.com",
        "success",
        320,
        78000,
        200,
      ],
      ["https://reddit.com", "Reddit", "The front page of the internet", "reddit.com", "success", 290, 120000, 200],
      ["https://wikipedia.org", "Wikipedia", "The free encyclopedia", "wikipedia.org", "success", 150, 95000, 200],
    ]

    for (const website of sampleWebsites) {
      await query(
        `
        INSERT INTO crawled_websites (url, title, description, domain, status, response_time, content_length, http_status_code)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (url) DO NOTHING
      `,
        website,
      )
    }

    // Sample ratings
    const sampleRatings = [
      ["john_doe", "https://example.com", 4],
      ["jane_smith", "https://github.com", 5],
      ["bob_wilson", "https://stackoverflow.com", 5],
      ["alice_brown", "https://reddit.com", 3],
      ["john_doe", "https://wikipedia.org", 4],
    ]

    for (const rating of sampleRatings) {
      await query(
        `
        INSERT INTO result_ratings (username, url, rating)
        VALUES ($1, $2, $3)
      `,
        rating,
      )
    }

    console.log("  ✅ Sample data seeded successfully")
  } catch (error) {
    console.error("  ⚠️  Sample data seeding failed (non-critical):", error.message)
  }
}

// Analytics specific queries with better error handling
export const analyticsQueries = {
  // Get visitor statistics
  getVisitorStats: async (days = 7) => {
    try {
      const result = await query(`
        SELECT 
          COUNT(*) as total_visits,
          COUNT(DISTINCT ip_address) as unique_visitors,
          COUNT(DISTINCT username) FILTER (WHERE username != 'Anonymous') as registered_users
        FROM website_visits 
        WHERE visit_time >= NOW() - INTERVAL '${days} days'
      `)
      return result.rows[0]
    } catch (error) {
      console.error("Error getting visitor stats:", error)
      return { total_visits: 0, unique_visitors: 0, registered_users: 0 }
    }
  },

  // Get daily visitor trends
  getVisitorTrends: async (days = 7) => {
    try {
      const result = await query(`
        SELECT 
          DATE(visit_time) as date,
          COUNT(*) as visitors
        FROM website_visits 
        WHERE visit_time >= NOW() - INTERVAL '${days} days'
        GROUP BY DATE(visit_time)
        ORDER BY date
      `)
      return result.rows
    } catch (error) {
      console.error("Error getting visitor trends:", error)
      return []
    }
  },

  // Get search query trends
  getSearchTrends: async (period = "7d") => {
    try {
      let interval = "7 days"
      let dateFormat = "YYYY-MM-DD"

      switch (period) {
        case "1d":
          interval = "1 day"
          dateFormat = "HH24:00"
          break
        case "30d":
          interval = "30 days"
          break
        case "90d":
          interval = "90 days"
          break
      }

      const result = await query(`
        SELECT 
          TO_CHAR(search_time, '${dateFormat}') as period,
          COUNT(*) as searches
        FROM search_queries 
        WHERE search_time >= NOW() - INTERVAL '${interval}'
        GROUP BY TO_CHAR(search_time, '${dateFormat}')
        ORDER BY period
      `)
      return result.rows
    } catch (error) {
      console.error("Error getting search trends:", error)
      return []
    }
  },

  // Get top pages
  getTopPages: async (days = 7) => {
    try {
      const result = await query(`
        SELECT 
          page_path as page,
          COUNT(*) as visits
        FROM website_visits 
        WHERE visit_time >= NOW() - INTERVAL '${days} days'
        GROUP BY page_path
        ORDER BY visits DESC
        LIMIT 10
      `)
      return result.rows
    } catch (error) {
      console.error("Error getting top pages:", error)
      return []
    }
  },

  // Get top countries
  getTopCountries: async (days = 7) => {
    try {
      const result = await query(`
        SELECT 
          location as country,
          COUNT(*) as visits
        FROM website_visits 
        WHERE visit_time >= NOW() - INTERVAL '${days} days'
          AND location IS NOT NULL
        GROUP BY location
        ORDER BY visits DESC
        LIMIT 10
      `)
      return result.rows
    } catch (error) {
      console.error("Error getting top countries:", error)
      return []
    }
  },

  // Get top browsers
  getTopBrowsers: async (days = 7) => {
    try {
      const result = await query(`
        SELECT 
          browser,
          COUNT(*) as visits
        FROM website_visits 
        WHERE visit_time >= NOW() - INTERVAL '${days} days'
          AND browser IS NOT NULL
        GROUP BY browser
        ORDER BY visits DESC
        LIMIT 10
      `)
      return result.rows
    } catch (error) {
      console.error("Error getting top browsers:", error)
      return []
    }
  },

  // Get recent visits with filters
  getRecentVisits: async (limit = 100, offset = 0) => {
    try {
      const result = await query(
        `
        SELECT 
          id,
          ip_address,
          page_path,
          username,
          location,
          device_type,
          browser,
          visit_time
        FROM website_visits 
        ORDER BY visit_time DESC
        LIMIT $1 OFFSET $2
      `,
        [limit, offset],
      )
      return result.rows
    } catch (error) {
      console.error("Error getting recent visits:", error)
      return []
    }
  },

  // Get crawl analytics
  getCrawlVolume: async (timeframe = "daily") => {
    try {
      let groupBy = "DATE(crawled_at)"
      let selectFormat = "DATE(crawled_at) as date"
      let interval = "30 days"

      switch (timeframe) {
        case "hourly":
          groupBy = "DATE_TRUNC('hour', crawled_at)"
          selectFormat = "DATE_TRUNC('hour', crawled_at) as hour"
          interval = "24 hours"
          break
        case "weekly":
          groupBy = "DATE_TRUNC('week', crawled_at)"
          selectFormat = "DATE_TRUNC('week', crawled_at) as week"
          interval = "12 weeks"
          break
      }

      const result = await query(`
        SELECT 
          ${selectFormat},
          COUNT(*) as count
        FROM crawled_websites 
        WHERE crawled_at >= NOW() - INTERVAL '${interval}'
        GROUP BY ${groupBy}
        ORDER BY ${groupBy}
      `)
      return result.rows
    } catch (error) {
      console.error("Error getting crawl volume:", error)
      return []
    }
  },

  // Get crawled URLs with filters
  getCrawledUrls: async (page = 1, limit = 20, filters: any = {}) => {
    try {
      let whereClause = "WHERE 1=1"
      const params: any[] = []
      let paramIndex = 1

      if (filters.status && filters.status !== "all") {
        whereClause += ` AND status = $${paramIndex}`
        params.push(filters.status)
        paramIndex++
      }

      if (filters.domain) {
        whereClause += ` AND domain ILIKE $${paramIndex}`
        params.push(`%${filters.domain}%`)
        paramIndex++
      }

      if (filters.dateRange) {
        whereClause += ` AND crawled_at >= NOW() - INTERVAL '${filters.dateRange} days'`
      }

      const offset = (page - 1) * limit
      params.push(limit, offset)

      const result = await query(
        `
        SELECT 
          id, url, title, crawled_at, status, response_time, content_length, domain
        FROM crawled_websites 
        ${whereClause}
        ORDER BY crawled_at DESC
        LIMIT $${paramIndex} OFFSET $${paramIndex + 1}
      `,
        params,
      )

      // Get total count for pagination
      const countResult = await query(
        `
        SELECT COUNT(*) as total
        FROM crawled_websites 
        ${whereClause}
      `,
        params.slice(0, -2),
      )

      return {
        urls: result.rows,
        total: Number.parseInt(countResult.rows[0].total),
      }
    } catch (error) {
      console.error("Error getting crawled URLs:", error)
      return { urls: [], total: 0 }
    }
  },

  // Get crawl statistics
  getCrawlStats: async () => {
    try {
      const totalResult = await query("SELECT COUNT(*) as total FROM crawled_websites")
      const todayResult = await query(`
        SELECT COUNT(*) as today 
        FROM crawled_websites 
        WHERE crawled_at >= CURRENT_DATE
      `)
      const avgResponseResult = await query(`
        SELECT AVG(response_time) as avg_response 
        FROM crawled_websites 
        WHERE response_time IS NOT NULL
      `)
      const successRateResult = await query(`
        SELECT 
          COUNT(*) FILTER (WHERE status = 'success') * 100.0 / COUNT(*) as success_rate
        FROM crawled_websites 
        WHERE crawled_at >= NOW() - INTERVAL '24 hours'
      `)
      const domainsResult = await query("SELECT COUNT(DISTINCT domain) as domains FROM crawled_websites")

      return {
        totalUrls: Number.parseInt(totalResult.rows[0].total),
        todayUrls: Number.parseInt(todayResult.rows[0].today),
        avgResponseTime: Math.round(avgResponseResult.rows[0].avg_response || 0),
        successRate: Number.parseFloat(successRateResult.rows[0].success_rate || 0).toFixed(1),
        domainsCount: Number.parseInt(domainsResult.rows[0].domains),
        activeWorkers: 8, // This would come from your crawler system
        queueSize: 2340, // This would come from your crawler queue
        lastCrawlTime: new Date().toISOString(),
      }
    } catch (error) {
      console.error("Error getting crawl stats:", error)
      return {
        totalUrls: 0,
        todayUrls: 0,
        avgResponseTime: 0,
        successRate: "0.0",
        domainsCount: 0,
        activeWorkers: 0,
        queueSize: 0,
        lastCrawlTime: new Date().toISOString(),
      }
    }
  },
}

export default pool
