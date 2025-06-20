import { query } from "./database"

export interface VisitData {
  ip_address: string
  user_agent?: string
  page_path: string
  referrer?: string
  username?: string
  location?: string
  device_type?: string
  browser?: string
  session_id?: string
}

export interface SearchData {
  query: string
  username?: string
  ip_address?: string
  results_count?: number
  search_type?: string
}

export class VisitorTracker {
  // Track a website visit
  static async trackVisit(visitData: VisitData): Promise<boolean> {
    try {
      await query(
        `
        INSERT INTO website_visits (
          ip_address, user_agent, page_path, referrer, username,
          location, device_type, browser, session_id
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      `,
        [
          visitData.ip_address,
          visitData.user_agent,
          visitData.page_path,
          visitData.referrer,
          visitData.username || "Anonymous",
          visitData.location || "Unknown",
          visitData.device_type || "Unknown",
          visitData.browser || "Unknown",
          visitData.session_id || `sess_${Date.now()}`,
        ],
      )

      return true
    } catch (error) {
      console.error("Failed to track visit:", error)
      return false
    }
  }

  // Track a search query
  static async trackSearch(searchData: SearchData): Promise<boolean> {
    try {
      await query(
        `
        INSERT INTO search_queries (
          query, username, ip_address, results_count, search_type
        ) VALUES ($1, $2, $3, $4, $5)
      `,
        [
          searchData.query,
          searchData.username || "Anonymous",
          searchData.ip_address,
          searchData.results_count || 0,
          searchData.search_type || "web",
        ],
      )

      return true
    } catch (error) {
      console.error("Failed to track search:", error)
      return false
    }
  }

  // Track a crawled website
  static async trackCrawledWebsite(websiteData: {
    url: string
    title?: string
    description?: string
    content?: string
    status?: string
    response_time?: number
    content_length?: number
    domain?: string
    http_status_code?: number
  }): Promise<boolean> {
    try {
      await query(
        `
        INSERT INTO crawled_websites (
          url, title, description, content, status, response_time,
          content_length, domain, http_status_code
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (url) DO UPDATE SET
          title = EXCLUDED.title,
          description = EXCLUDED.description,
          content = EXCLUDED.content,
          status = EXCLUDED.status,
          response_time = EXCLUDED.response_time,
          content_length = EXCLUDED.content_length,
          http_status_code = EXCLUDED.http_status_code,
          last_updated = CURRENT_TIMESTAMP
      `,
        [
          websiteData.url,
          websiteData.title,
          websiteData.description,
          websiteData.content,
          websiteData.status || "success",
          websiteData.response_time,
          websiteData.content_length,
          websiteData.domain,
          websiteData.http_status_code || 200,
        ],
      )

      return true
    } catch (error) {
      console.error("Failed to track crawled website:", error)
      return false
    }
  }

  // Track a user rating
  static async trackRating(ratingData: {
    username: string
    url: string
    rating: number
  }): Promise<boolean> {
    try {
      await query(
        `
        INSERT INTO result_ratings (username, url, rating)
        VALUES ($1, $2, $3)
        ON CONFLICT (username, url) DO UPDATE SET
          rating = EXCLUDED.rating,
          updated_at = CURRENT_TIMESTAMP
      `,
        [ratingData.username, ratingData.url, ratingData.rating],
      )

      return true
    } catch (error) {
      console.error("Failed to track rating:", error)
      return false
    }
  }
}
