import React, { useEffect, useState } from "react";

const LIMIT = 15 * 60 * 1000;
const WARN = 60 * 1000;
const KEY = "alpimo_last_activity";
const EVENTS = ["mousemove", "mousedown", "keydown", "scroll", "touchstart", "wheel"];

const last = () => Number(localStorage.getItem(KEY) || Date.now());
const touch = () => localStorage.setItem(KEY, String(Date.now()));

export function IdleLogout({ onLogout }) {
  const [left, setLeft] = useState(null);
  useEffect(() => {
    if (Date.now() - last() > LIMIT && localStorage.getItem(KEY)) onLogout(true);
    else touch();
  }, []); // eslint-disable-line
  useEffect(() => {
    let t = 0;
    const act = () => { const n = Date.now(); if (n - t > 5000 && left === null) { t = n; touch(); } };
    EVENTS.forEach((e) => window.addEventListener(e, act, { passive: true }));
    const iv = setInterval(() => {
      const rem = LIMIT - (Date.now() - last());
      if (rem <= 0) { onLogout(true); return; }
      setLeft(rem <= WARN ? Math.ceil(rem / 1000) : null);
    }, 1000);
    return () => { EVENTS.forEach((e) => window.removeEventListener(e, act)); clearInterval(iv); };
  }, [onLogout, left === null]); // eslint-disable-line
  if (left === null) return null;
  return (
    <div className="ov" style={{ zIndex: 200 }} data-testid="idle-warning">
      <div className="modal">
        <h3>Sei ancora lì?</h3>
        <p className="muted" style={{ margin: "8px 0 16px" }}>Per sicurezza verrai disconnesso tra <b data-testid="idle-countdown">{left}</b> secondi per inattività.</p>
        <div className="act">
          <button className="btn" onClick={() => onLogout(true)} data-testid="idle-logout-now">Esci ora</button>
          <button className="btn primary" onClick={() => { touch(); setLeft(null); }} data-testid="idle-stay">Resta collegato</button>
        </div>
      </div>
    </div>
  );
}

export const clearIdle = () => localStorage.removeItem(KEY);
export const startIdle = touch;
