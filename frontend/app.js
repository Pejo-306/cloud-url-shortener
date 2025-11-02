(function () {
  const { API_BASE_URL, COGNITO_DOMAIN, COGNITO_CLIENT_ID, REDIRECT_URI } = window.ENV || {};
  const longUrl = document.getElementById("longUrl");
  const shortenBtn = document.getElementById("shortenBtn");
  const result = document.getElementById("result");
  const shortUrlEl = document.getElementById("shortUrl");
  const openBtn = document.getElementById("openBtn");

  const ID_TOKEN_KEY = "id_token";
  const VERIFIER_KEY = "pkce_verifier";

  // --- PKCE helpers ---
  async function sha256(buf) { return crypto.subtle.digest("SHA-256", buf); }
  function b64url(bytes) {
    return btoa(String.fromCharCode(...new Uint8Array(bytes)))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  }
  function randomB64url(n = 64) {
    const a = new Uint8Array(n); crypto.getRandomValues(a); return b64url(a);
  }
  function formUrl(obj) {
    return Object.entries(obj).map(([k,v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join("&");
  }

  async function startLogin() {
    const verifier = randomB64url(64);
    sessionStorage.setItem(VERIFIER_KEY, verifier);
    const challenge = b64url(await sha256(new TextEncoder().encode(verifier)));

    const params = {
      client_id: COGNITO_CLIENT_ID,
      response_type: "code",
      scope: "openid email profile",
      redirect_uri: REDIRECT_URI,
      code_challenge: challenge,
      code_challenge_method: "S256"
    };
    const url = `https://${COGNITO_DOMAIN}/oauth2/authorize?${formUrl(params)}`;
    window.location.assign(url);
  }

  async function exchangeCodeForTokens(code) {
    const verifier = sessionStorage.getItem(VERIFIER_KEY) || "";
    const body = formUrl({
      grant_type: "authorization_code",
      client_id: COGNITO_CLIENT_ID,
      code,
      redirect_uri: REDIRECT_URI,
      code_verifier: verifier
    });
    const resp = await fetch(`https://${COGNITO_DOMAIN}/oauth2/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body
    });
    if (!resp.ok) {
      const t = await resp.text().catch(()=>"");
      throw new Error(`token exchange failed: ${resp.status} ${t}`);
    }
    return resp.json();
  }

  function getQuery(name) { return new URLSearchParams(window.location.search).get(name) || ""; }
  function clearQuery() {
    if (history.replaceState) {
      const u = new URL(location.href); u.search = ""; history.replaceState({}, document.title, u.toString());
    }
  }
  function getIdToken() { return sessionStorage.getItem(ID_TOKEN_KEY); }

  async function ensureAuth() {
    const token = getIdToken();
    if (token) return token;

    const code = getQuery("code");
    if (code) {
      const tokens = await exchangeCodeForTokens(code);
      if (!tokens.id_token) throw new Error("no id_token in response");
      sessionStorage.setItem(ID_TOKEN_KEY, tokens.id_token);
      clearQuery();
      return tokens.id_token;
    }
    await startLogin();
    return null;
  }

  async function callShorten(url, idToken) {
    const r = await fetch(`${API_BASE_URL.replace(/\/$/, "")}/v1/shorten`, {
      method: "POST",
      headers: { "Content-Type":"application/json", "Authorization": `Bearer ${idToken}` },
      body: JSON.stringify({ target_url: url }) // use { target_url: url } if your Lambda expects that field
    });
    if (!r.ok) { throw new Error(`${r.status} ${await r.text().catch(()=>"")}`); }
    return r.json();
  }

  // Bootstrap auth on load (non-blocking)
  ensureAuth().catch(e => alert("Auth error: " + e.message));

  shortenBtn.addEventListener("click", async () => {
    const url = longUrl.value.trim();
    if (!url) { alert("Please enter a URL."); return; }
    try {
      const idToken = getIdToken() || await ensureAuth();
      const data = await callShorten(url, idToken);
      const shortUrl = data.short_url || data.shortUrl || "";
      if (!shortUrl) throw new Error("No short_url in response");
      shortUrlEl.textContent = shortUrl;
      shortUrlEl.href = shortUrl;
      result.style.display = "block";
      openBtn.onclick = () => window.open(shortUrl, "_blank", "noopener");
    } catch (e) {
      alert("Error: " + e.message);
    }
  });
})();
