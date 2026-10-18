"use strict";
const form = document.querySelector("#shorten-form");
const message = document.querySelector("#message");
const createButton = document.querySelector("#create-button");
const refreshButton = document.querySelector("#refresh-button");
const storageKey = "small-link-codes-v1";
let codes = [];
let currentLink = "";
try {
  const saved = JSON.parse(localStorage.getItem(storageKey) || "[]");
  if (Array.isArray(saved)) codes = [...new Set(saved.filter(c => typeof c === "string" && /^[A-Za-z0-9_-]{8}$/.test(c)))].slice(0, 20);
} catch { /* Browser storage can be unavailable; the application still works. */ }

function announce(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

async function request(path, options = {}) {
  const result = await fetch(path, {...options, signal: AbortSignal.timeout(15000)});
  const data = await result.json();
  if (!result.ok) {
    const error = new Error(data.error || "Something went wrong. Please try again.");
    error.status = result.status;
    throw error;
  }
  return data;
}

function card(data) {
  const row = document.createElement("article");
  row.className = "link-card";
  const detail = document.createElement("div");
  detail.className = "link-detail";
  const link = document.createElement("a");
  link.href = `/r/${data.code}`;
  link.textContent = `${location.host}/r/${data.code}`;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  const destination = document.createElement("p");
  destination.className = "destination";
  destination.textContent = data.url;
  destination.title = data.url;
  const expiry = document.createElement("span");
  expiry.className = "expiry";
  expiry.textContent = `Expires ${new Date(data.expires_at * 1000).toLocaleDateString()}`;
  detail.append(link, destination, expiry);
  const count = document.createElement("div");
  count.className = "visit-count";
  const number = document.createElement("strong");
  number.textContent = data.visits.toLocaleString();
  const label = document.createElement("span");
  label.textContent = data.visits === 1 ? "VISIT" : "VISITS";
  count.append(number, label);
  row.append(detail, count);
  return row;
}

async function refresh() {
  if (!codes.length) return;
  refreshButton.disabled = true;
  const list = document.querySelector("#links-list");
  try {
    const entries = await Promise.all(codes.map(async code => {
      try { return await request(`/api/links/${code}`); }
      catch (error) { if (error.status === 404) return null; throw error; }
    }));
    list.replaceChildren();
    entries.filter(Boolean).forEach(data => list.append(card(data)));
    if (!entries.some(Boolean)) list.textContent = "Your saved links have expired or are unavailable in this environment.";
  } catch {
    announce("Couldn't refresh counts. Check your connection and try again.", true);
  } finally { refreshButton.disabled = false; }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  createButton.disabled = true;
  document.querySelector("#result").hidden = true;
  announce("Creating your short link…");
  try {
    const data = await request("/api/links", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({url: form.elements.url.value.trim()})});
    currentLink = new URL(`/r/${data.code}`, location.origin).href;
    const link = document.querySelector("#short-link");
    link.href = currentLink;
    link.textContent = currentLink;
    document.querySelector("#result").hidden = false;
    document.querySelector("#copy-button").textContent = "Copy link";
    codes = [data.code, ...codes.filter(code => code !== data.code)].slice(0, 20);
    try { localStorage.setItem(storageKey, JSON.stringify(codes)); } catch { /* Optional persistence. */ }
    announce("Ready to share. Open your link, then refresh its visit count.");
    await refresh();
  } catch (error) {
    announce(error.name === "TimeoutError" ? "The request timed out. Please try again." : error.message, true);
  } finally { createButton.disabled = false; }
});

document.querySelector("#copy-button").addEventListener("click", async event => {
  try { await navigator.clipboard.writeText(currentLink); event.target.textContent = "Copied!"; }
  catch { announce("Clipboard unavailable. Select and copy the link above.", true); }
});
refreshButton.addEventListener("click", refresh);
refresh();
