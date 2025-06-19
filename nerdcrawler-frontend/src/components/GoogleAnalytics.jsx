"use client"

import { useEffect } from "react"

const GA_TRACKING_ID = "G-FLCSWSD2SX"

export default function GoogleAnalytics() {
  useEffect(() => {
    // Check if gtag is already loaded
    if (window.gtag) return

    // Add the gtag script
    const gtagScript = document.createElement("script")
    gtagScript.async = true
    gtagScript.src = `https://www.googletagmanager.com/gtag/js?id=${GA_TRACKING_ID}`
    document.head.appendChild(gtagScript)

    // Add the gtag configuration script
    const gtagConfigScript = document.createElement("script")
    gtagConfigScript.innerHTML = `
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', '${GA_TRACKING_ID}');
    `
    document.head.appendChild(gtagConfigScript)
  }, [])

  return null
}

// Helper function to track page views
export const trackPageView = (path) => {
  if (window.gtag) {
    window.gtag("config", GA_TRACKING_ID, {
      page_path: path,
    })
  }
}

// Helper function to track events
export const trackEvent = (action, category, label, value) => {
  if (window.gtag) {
    window.gtag("event", action, {
      event_category: category,
      event_label: label,
      value: value,
    })
  }
}
