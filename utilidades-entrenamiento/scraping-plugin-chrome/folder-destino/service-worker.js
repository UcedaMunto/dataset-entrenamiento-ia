const DOWNLOAD_DIRECTORY = "folder-destino";

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id) {
    await showStatus("ERR", "No se encontró una pestaña activa.");
    return;
  }

  await showStatus("...", "Buscando imagen de producto...");

  try {
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: findProductImage
    });
    const candidate = result?.result;

    if (!candidate?.url) {
      throw new Error("No encontré una imagen de producto adecuada en esta página.");
    }

    const filename = `${DOWNLOAD_DIRECTORY}/${makeFilename(
      candidate.title,
      candidate.url
    )}`;
    const downloadId = await chrome.downloads.download({
      url: candidate.url,
      filename,
      conflictAction: "uniquify",
      saveAs: false
    });

    await chrome.action.setBadgeBackgroundColor({ color: "#188038" });
    await chrome.action.setBadgeText({ text: "OK" });
    await chrome.action.setTitle({
      title: `Descarga iniciada: ${candidate.title || "imagen de producto"} (#${downloadId})`
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    await showStatus("ERR", message);
  }
});

async function showStatus(text, title) {
  await chrome.action.setBadgeBackgroundColor({
    color: text === "ERR" ? "#b3261e" : "#5f6368"
  });
  await chrome.action.setBadgeText({ text });
  await chrome.action.setTitle({ title });
}

function makeFilename(title, imageUrl) {
  const safeTitle = (title || "producto")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "producto";

  let extension = "jpg";
  try {
    const path = new URL(imageUrl).pathname;
    const match = path.match(/\.([a-zA-Z0-9]{2,5})$/);
    const candidateExtension = match?.[1]?.toLowerCase();
    if (candidateExtension && ["avif", "gif", "jpeg", "jpg", "png", "webp"].includes(candidateExtension)) {
      extension = candidateExtension === "jpeg" ? "jpg" : candidateExtension;
    }
  } catch {
    // URLs are validated while choosing the image.
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `${safeTitle}-${timestamp}.${extension}`;
}

function findProductImage() {
  const positiveWords =
    /\b(product|producto|item|articulo|artículo|buy|comprar|gallery|galeria|galería|main-image|primary-image|product-image|product-photo|product-media|pdp)\b/i;
  const negativeWords =
    /\b(logo|icon|sprite|avatar|banner|header|footer|badge|payment|shipping|thumbnail|thumb|swatch|pixel|tracking|placeholder)\b/i;
  const candidates = new Map();

  function addCandidate(rawUrl, details = {}) {
    if (!rawUrl || typeof rawUrl !== "string") return;

    let url;
    try {
      url = new URL(rawUrl, document.baseURI);
    } catch {
      return;
    }
    if (!["http:", "https:"].includes(url.protocol)) return;
    if (url.username || url.password) return;

    const key = url.href;
    const previous = candidates.get(key);
    if (previous) {
      previous.width = Math.max(previous.width, details.width || 0);
      previous.height = Math.max(previous.height, details.height || 0);
      previous.hints.push(details.hint || "");
      previous.priority = Math.max(previous.priority, details.priority || 0);
      return;
    }

    candidates.set(key, {
      url: key,
      width: details.width || 0,
      height: details.height || 0,
      hints: [details.hint || ""],
      priority: details.priority || 0
    });
  }

  for (const image of document.images) {
    const sources = new Set([
      image.currentSrc,
      image.src,
      image.dataset.src,
      image.dataset.lazySrc,
      image.dataset.original,
      image.dataset.originalSrc
    ]);
    const hint = [
      image.alt,
      image.title,
      image.id,
      image.className,
      image.getAttribute("itemprop"),
      image.closest(
        '[itemtype*="Product"], [itemprop="image"], [class*="product"], [id*="product"], [class*="gallery"]'
      )?.className,
      image.closest(
        '[itemtype*="Product"], [itemprop="image"], [class*="product"], [id*="product"], [class*="gallery"]'
      )?.id
    ].filter(Boolean).join(" ");

    for (const source of sources) {
      addCandidate(source, {
        width: Math.max(image.naturalWidth, image.width),
        height: Math.max(image.naturalHeight, image.height),
        hint
      });
    }
  }

  for (const meta of document.querySelectorAll(
    'meta[property="og:image"], meta[name="twitter:image"], meta[property="og:image:secure_url"]'
  )) {
    addCandidate(meta.content, {
      width: 1200,
      height: 1200,
      priority: 3,
      hint: "product social image"
    });
  }

  for (const element of document.querySelectorAll(
    '[itemprop="image"], [class*="product-image"], [class*="product__image"], [id*="product-image"]'
  )) {
    const rawUrl =
      element.getAttribute("content") ||
      element.getAttribute("data-src") ||
      element.getAttribute("src");
    addCandidate(rawUrl, {
      width: element.naturalWidth || element.clientWidth,
      height: element.naturalHeight || element.clientHeight,
      priority: 2,
      hint: `${element.className || ""} ${element.id || ""} ${element.getAttribute("itemprop") || ""}`
    });
  }

  const ranked = [...candidates.values()]
    .map((candidate) => {
      const hint = candidate.hints.join(" ");
      const area = candidate.width * candidate.height;
      const aspect = candidate.width && candidate.height
        ? candidate.width / candidate.height
        : 1;
      let score = Math.log2(Math.max(area, 1));

      if (candidate.width < 180 || candidate.height < 180) score -= 20;
      if (aspect < 0.35 || aspect > 3.2) score -= 18;
      if (positiveWords.test(hint)) score += 18;
      if (negativeWords.test(`${hint} ${candidate.url}`)) score -= 45;
      if (/^https?:\/\/[^/]+\/(?:logo|icons?|assets\/icons?)(?:\/|$)/i.test(candidate.url)) {
        score -= 25;
      }
      score += candidate.priority * 5;

      return { ...candidate, score };
    })
    .filter((candidate) => candidate.width >= 180 && candidate.height >= 180)
    .sort((left, right) => right.score - left.score);

  const best = ranked[0];
  if (!best) return null;

  const pageTitle =
    document.querySelector('meta[property="og:title"]')?.content ||
    document.querySelector('meta[name="twitter:title"]')?.content ||
    document.title ||
    "producto";

  return {
    url: best.url,
    title: pageTitle.trim().slice(0, 160)
  };
}
