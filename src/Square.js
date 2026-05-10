import React from "react";

export default function Square({ value, isDark, label }) {
  return (
    <div className={`cell ${isDark ? "dark" : "light"}`}>
      {/* Square coordinate label */}
      {isDark && <div className="label">{label}</div>}

      {/* Pieces */}
      {value === 1 && <div className="piece red" />}
      {value === 2 && <div className="piece yellow" />}
      {value === 3 && <div className="piece red king">👑</div>}
      {value === 4 && <div className="piece yellow king">👑</div>}
    </div>
  );
}
