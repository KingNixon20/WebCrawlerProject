"use client"

import { useEffect } from "react"

export default function SEO({
  title = "NerdCrawler - Advanced Search Engine",
  description = "NerdCrawler is an advanced search engine for developers and tech enthusiasts",
  keywords = "search engine, web search, developer tools, nerd crawler",
}) {
  useEffect(() => {
    // Set title
    document.title = title

    // Add or update meta tags
    const metaTags = [
      { name: "description", content: description },
      { name: "keywords", content: keywords },
      { name: "google-site-verification", content: "oqXoenPBo3BvlgajZf0p6YvsR6GBt-_QBShmivxvOaU" },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: title },
      { name: "twitter:description", content: description },
    ]

    metaTags.forEach(({ name, property, content }) => {
      const selector = name ? `meta[name="${name}"]` : `meta[property="${property}"]`
      let meta = document.querySelector(selector)

      if (!meta) {
        meta = document.createElement("meta")
        if (name) meta.name = name
        if (property) meta.property = property
        document.head.appendChild(meta)
      }

      meta.content = content
    })
  }, [title, description, keywords])

  return null
}
