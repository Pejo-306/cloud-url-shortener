(function () {
  const apiBase = (window.ENV && window.ENV.API_BASE_URL) || "";
  const longUrl = document.getElementById("longUrl");
  const shortenBtn = document.getElementById("shortenBtn");
  const result = document.getElementById("result");
  const shortUrlEl = document.getElementById("shortUrl");
  const openBtn = document.getElementById("openBtn");

  shortenBtn.addEventListener("click", async () => {
    const url = longUrl.value.trim();
    if (!url) { alert("Please enter a URL."); return; }
    try {
      const r = await fetch(`${apiBase}/v1/shorten`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ target_url: url })
      });
      if (!r.ok) {
        const t = await r.text().catch(()=>"");
        throw new Error(`${r.status} ${r.statusText} ${t}`);
      }
      const data = await r.json();
      const shortUrl = data.short_url;
      shortUrlEl.textContent = shortUrl;
      shortUrlEl.href = shortUrl;
      result.style.display = "block";
      openBtn.onclick = () => window.open(shortUrl, "_blank", "noopener");
    } catch (e) {
      alert("Error: " + e.message);
    }
  });
})();
