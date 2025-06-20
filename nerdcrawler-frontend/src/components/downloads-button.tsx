"use client"

interface DownloadsButtonProps {
  onClick?: () => void
}

export default function DownloadsButton({ onClick }: DownloadsButtonProps) {
  const handleClick = () => {
    if (onClick) {
      onClick()
    } else {
      window.history.pushState({}, "", "/downloads")
      window.dispatchEvent(new PopStateEvent("popstate"))
    }
  }

  return (
    <button className="downloads-button" onClick={handleClick}>
      Downloads
    </button>
  )
}
