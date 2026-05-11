import React from "react";
import Square from "./Square";

export default function Board({ board }) {
  const squareLabel = (r, c) => {
    const file = "ABCDEFGH"[c];
    const rank = 8 - r;
    return file + rank;
  };

  return (
    <div className="board">
      {board.map((row, r) => (
        <div key={r} className="row">
          {row.map((cell, c) => (
            <Square
              key={c}
              value={cell}
              isDark={(r + c) % 2 === 1}
              label={squareLabel(r, c)}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
