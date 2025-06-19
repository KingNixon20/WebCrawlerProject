"use client"

import { useState } from "react"
import { AuroraText } from "./components/magicui/aurora-text"
import "./index.css"

export default function GamesPage() {
  const [selectedGame, setSelectedGame] = useState(null)

  const games = [
    {
      id: 1,
      title: "Snake Game",
      description: "Classic snake game with modern styling",
      emoji: "🐍",
      color: "#4caf50",
      comingSoon: false,
    },
    {
      id: 2,
      title: "Tetris",
      description: "The classic block-stacking puzzle game",
      emoji: "🧩",
      color: "#9c27b0",
      comingSoon: true,
    },
    {
      id: 3,
      title: "2048",
      description: "Combine tiles to reach 2048",
      emoji: "🔢",
      color: "#ff9800",
      comingSoon: true,
    },
    {
      id: 4,
      title: "Pong",
      description: "The original arcade tennis game",
      emoji: "🏓",
      color: "#2196f3",
      comingSoon: true,
    },
    {
      id: 5,
      title: "Memory Game",
      description: "Test your memory with card matching",
      emoji: "🧠",
      color: "#e91e63",
      comingSoon: true,
    },
    {
      id: 6,
      title: "Breakout",
      description: "Break bricks with a bouncing ball",
      emoji: "🧱",
      color: "#ff5722",
      comingSoon: true,
    },
  ]

  const handleGoHome = () => {
    window.history.pushState({}, "", "/")
    window.dispatchEvent(new PopStateEvent("popstate"))
  }

  const handleGameSelect = (game) => {
    if (game.comingSoon) {
      alert("This game is coming soon! 🎮")
      return
    }
    setSelectedGame(game)
  }

  return (
    <div
      className="games-page"
      style={{
        minHeight: "100vh",
        background: "#0f0f0f",
        color: "#fff",
        padding: "2rem",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "3rem",
          borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
          paddingBottom: "1rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "2rem" }}>
          <button
            onClick={handleGoHome}
            style={{
              background: "none",
              border: "none",
              color: "#4fc3f7",
              fontSize: "1.5rem",
              cursor: "pointer",
              textDecoration: "none",
            }}
          >
            <span style={{ color: "#4285f4", fontWeight: "600" }}>Nerd</span>
            <AuroraText style={{ color: "#4fc3f7", fontWeight: "500" }}>Crawler</AuroraText>
          </button>
          <h1 style={{ margin: 0, fontSize: "2rem", fontWeight: "600" }}>🎮 Games</h1>
        </div>
        <button
          onClick={handleGoHome}
          style={{
            background: "rgba(79, 195, 247, 0.1)",
            border: "1px solid #4fc3f7",
            color: "#4fc3f7",
            padding: "0.5rem 1rem",
            borderRadius: "8px",
            cursor: "pointer",
            fontSize: "0.9rem",
          }}
        >
          ← Back to Search
        </button>
      </div>

      <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
        {!selectedGame ? (
          <>
            {/* Games Grid */}
            <div style={{ textAlign: "center", marginBottom: "3rem" }}>
              <h2 style={{ color: "#4fc3f7", marginBottom: "1rem" }}>Choose Your Game</h2>
              <p style={{ color: "#ccc", fontSize: "1.1rem" }}>
                Take a break from searching and enjoy some classic games!
              </p>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
                gap: "2rem",
                marginBottom: "3rem",
              }}
            >
              {games.map((game) => (
                <div
                  key={game.id}
                  onClick={() => handleGameSelect(game)}
                  style={{
                    background: `rgba(${
                      game.color === "#4caf50"
                        ? "76, 175, 80"
                        : game.color === "#9c27b0"
                          ? "156, 39, 176"
                          : game.color === "#ff9800"
                            ? "255, 152, 0"
                            : game.color === "#2196f3"
                              ? "33, 150, 243"
                              : game.color === "#e91e63"
                                ? "233, 30, 99"
                                : "255, 87, 34"
                    }, 0.1)`,
                    border: `1px solid ${game.color}`,
                    borderRadius: "16px",
                    padding: "2rem",
                    textAlign: "center",
                    cursor: game.comingSoon ? "not-allowed" : "pointer",
                    transition: "all 0.3s ease",
                    opacity: game.comingSoon ? 0.6 : 1,
                    position: "relative",
                    overflow: "hidden",
                  }}
                  onMouseEnter={(e) => {
                    if (!game.comingSoon) {
                      e.target.style.transform = "translateY(-5px)"
                      e.target.style.boxShadow = `0 10px 30px rgba(${game.color.slice(1)}, 0.3)`
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!game.comingSoon) {
                      e.target.style.transform = "translateY(0)"
                      e.target.style.boxShadow = "none"
                    }
                  }}
                >
                  {game.comingSoon && (
                    <div
                      style={{
                        position: "absolute",
                        top: "1rem",
                        right: "1rem",
                        background: "rgba(255, 255, 255, 0.1)",
                        padding: "0.25rem 0.5rem",
                        borderRadius: "12px",
                        fontSize: "0.7rem",
                        color: "#ccc",
                      }}
                    >
                      Coming Soon
                    </div>
                  )}
                  <div style={{ fontSize: "4rem", marginBottom: "1rem" }}>{game.emoji}</div>
                  <h3 style={{ margin: "0 0 1rem", color: game.color, fontSize: "1.5rem" }}>{game.title}</h3>
                  <p style={{ color: "#ccc", margin: 0, lineHeight: "1.5" }}>{game.description}</p>
                </div>
              ))}
            </div>

            {/* Coming Soon Notice */}
            <div
              style={{
                background: "rgba(79, 195, 247, 0.1)",
                border: "1px solid rgba(79, 195, 247, 0.3)",
                borderRadius: "12px",
                padding: "2rem",
                textAlign: "center",
              }}
            >
              <h3 style={{ color: "#4fc3f7", marginBottom: "1rem" }}>🚀 More Games Coming Soon!</h3>
              <p style={{ color: "#ccc", margin: 0 }}>
                We're working on adding more exciting games to help you take breaks during your search sessions. Stay
                tuned for updates!
              </p>
            </div>
          </>
        ) : (
          /* Game View - Placeholder for now */
          <div style={{ textAlign: "center", padding: "4rem" }}>
            <div style={{ fontSize: "6rem", marginBottom: "2rem" }}>{selectedGame.emoji}</div>
            <h2 style={{ color: selectedGame.color, marginBottom: "1rem" }}>{selectedGame.title}</h2>
            <p style={{ color: "#ccc", marginBottom: "2rem", fontSize: "1.1rem" }}>{selectedGame.description}</p>
            <div
              style={{
                background: "rgba(20, 20, 20, 0.8)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                borderRadius: "12px",
                padding: "3rem",
                marginBottom: "2rem",
              }}
            >
              <p style={{ color: "#888", fontSize: "1.2rem" }}>🎮 Game implementation coming soon!</p>
              <p style={{ color: "#666", marginTop: "1rem" }}>
                This will be a fully playable {selectedGame.title} game.
              </p>
            </div>
            <button
              onClick={() => setSelectedGame(null)}
              style={{
                background: selectedGame.color,
                border: "none",
                color: "#fff",
                padding: "1rem 2rem",
                borderRadius: "8px",
                cursor: "pointer",
                fontSize: "1rem",
                fontWeight: "600",
              }}
            >
              ← Back to Games
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
