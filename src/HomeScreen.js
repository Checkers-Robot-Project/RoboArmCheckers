import React from "react";
import "./HomeScreen.css";

export default function HomeScreen({ onSelect }) {
  return (
    <div className="home-container">
      <div className="home-card">
        <h1>
          Checkers
          <br />
          Robot
        </h1>

        <p>
          Dara Rattigan 2150849
        </p>

        <div className="button-grid">
          <button onClick={() => onSelect("human")}>
            Play vs Robot
          </button>

          <button onClick={() => onSelect("self")}>
            Robot Self Play
          </button>
        </div>
      </div>
    </div>
  );
}