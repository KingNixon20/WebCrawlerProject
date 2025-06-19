"use client"

import { useState, useEffect } from "react"

export default function IndexedPagesCount() {
  const [stats, setStats] = useState({
    totalPages: 0,
    isLoading: true,
    error: null,
  })

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch("https://projectkryptos.xyz/api/search?per_page=1")
        if (response.ok) {
          const data = await response.json()
          setStats({
            totalPages: data.total || 0,
            isLoading: false,
            error: null,
          })
        } else {
          setStats({
            totalPages: 0,
            isLoading: false,
            error: "Failed to fetch stats",
          })
        }
      } catch (error) {
        console.error("Error fetching indexed pages count:", error)
        setStats({
          totalPages: 0,
          isLoading: false,
          error: "Failed to fetch stats",
        })
      }
    }

    fetchStats()
  }, [])

  // Format number with commas
  const formatNumber = (num) => {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")
  }

  if (stats.isLoading) {
    return <div className="text-center text-gray-400 text-sm mt-2">Loading stats...</div>
  }

  if (stats.error) {
    return null // Don't show anything if there's an error
  }

  return (
    <div className="text-center text-gray-400 text-sm mt-2">
      {stats.totalPages > 0 ? `${formatNumber(stats.totalPages)} pages indexed` : ""}
    </div>
  )
}
