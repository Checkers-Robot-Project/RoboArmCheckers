import React, { useState, useEffect, useRef } from "react";
import Board from "./Board";
import "./App.css";
import HomeScreen from "./HomeScreen";

export default function App() {
  const emptyBoard = Array.from({ length: 8 }, () => Array(8).fill(0));

  const [mode, setMode] = useState(null);
  const [board, setBoard] = useState(emptyBoard);
  const [status, setStatus] = useState("Waiting...");
  const [aiMove, setAIMove] = useState(null);
  const [cameraPaused, setCameraPaused] = useState(false);

  const wsRef = useRef(null);
  const lastBoardRef = useRef(null);
  const moveLockRef = useRef(false);

  // Self-play state
  const selfPlayerRef = useRef("red");

  // =========================================================
  // WEBSOCKET
  // =========================================================
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:6789");
    wsRef.current = ws;

    ws.onopen = () => setStatus("Connected");

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // CAMERA PAUSED
      if (data?.type === "CAMERA_PAUSED") {
        setCameraPaused(true);
        return;
      }

      // CAMERA RESUMED
      if (data?.type === "CAMERA_RESUMED") {
        setCameraPaused(false);
        return;
      }

      // AI MOVE (robot finished)
      if (data?.type === "AI_MOVE") {
        setAIMove(data.move);
        moveLockRef.current = false;
        return;
      }

      // CAMERA BOARD UPDATE
      if (Array.isArray(data)) {
        if (cameraPaused) return;

        const str = JSON.stringify(data);
        if (lastBoardRef.current !== str) {
          lastBoardRef.current = str;
          setBoard(data);
        }
      }
    };

    ws.onclose = () => setStatus("Disconnected");
    return () => ws.close();
  }, [mode]);

  // =========================================================
  // ONE MOVE PER CLICK
  // =========================================================
  const doOneSelfPlayMove = () => {
    if (!wsRef.current) return;
    if (moveLockRef.current) return;

    moveLockRef.current = true;

    const player = selfPlayerRef.current;

    wsRef.current.send(
      "ROBOT_MOVE_REQUEST|self|" + player + "|" + JSON.stringify(board)
    );

    // Swap for next turn
    selfPlayerRef.current = player === "red" ? "yellow" : "red";
  };

  // =========================================================
  // HUMAN MODE MOVE
  // =========================================================
  const robotMove = () => {
    if (!wsRef.current) return;
    if (moveLockRef.current) return;

    moveLockRef.current = true;

    wsRef.current.send(
      "ROBOT_MOVE_REQUEST|human|" + JSON.stringify(board)
    );
  };

  // =========================================================
  // MODE SELECT
  // =========================================================
  const startMode = (selectedMode) => {
    setMode(selectedMode);
    moveLockRef.current = false;
  };

  // =========================================================
  // HOME SCREEN
  // =========================================================
  if (!mode) {
    return <HomeScreen onSelect={startMode} />;
  }

  // =========================================================
  // UI
  // =========================================================
  return (
    <div className="app-container">
      <div className={`board-wrapper ${cameraPaused ? "camera-paused" : ""}`}>
        {cameraPaused && <div className="overlay">Robot Moving…</div>}
        <Board board={board} />
      </div>

      <div className="sidebar">
        <h2>Robot Checkers</h2>

        <div className="info">
          <p><strong>Mode:</strong> {mode}</p>
          <p><strong>Status:</strong> {status}</p>
          <p><strong>Engine Move:</strong> {aiMove ? aiMove.join(" → ") : "None"}</p>
        </div>

        <div className="controls">
          {mode === "human" && (
            <button onClick={robotMove}>Robot Move</button>
          )}

          {mode === "self" && (
            <button onClick={doOneSelfPlayMove}>
              Make Next Move
            </button>
          )}

          <button onClick={() => setMode(null)}>Back to Menu</button>
        </div>
      </div>
    </div>
  );
}