/**
 * api.js
 *
 * Thin client for the StyleScout FastAPI backend. The base URL is
 * configurable via VITE_API_URL (see .env.example) so the same build
 * can point at localhost during development and a deployed backend
 * URL in production, without code changes.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function requestStyling(query) {
  const response = await fetch(`${API_BASE_URL}/api/style`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}
