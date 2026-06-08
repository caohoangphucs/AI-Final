const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const TOUR_URL = "https://cloud.3dvista.com//hosting/8186875/0/index.htm";
const OUTPUT_FILE = path.join(__dirname, "discovered-map-assets.json");
const CLICK_WAIT_MS = Number.parseInt(process.env.DISCOVER_CLICK_WAIT_MS || "5000", 10);
const INITIAL_WAIT_MS = Number.parseInt(process.env.DISCOVER_INITIAL_WAIT_MS || "7000", 10);
const MAX_ITEMS = Number.parseInt(process.env.DISCOVER_MAX_ITEMS || "999", 10);
const HEADLESS = process.env.DISCOVER_HEADLESS === "true";

function normalizeUrl(rawUrl) {
  try {
    const url = new URL(rawUrl);
    url.hash = "";
    return url.toString();
  } catch {
    return rawUrl;
  }
}

function categorize(url) {
  if (/\/media\/panorama_/i.test(url)) return "panorama_tile";
  if (/\/media\/res_/i.test(url)) return "media_res";
  if (/\/media\/map_/i.test(url)) return "media_map";
  if (/\/loading\//i.test(url)) return "loading";
  if (/\/skin\//i.test(url)) return "skin";
  if (/\/locale\//i.test(url)) return "locale";
  if (/\/misc\//i.test(url)) return "misc";
  if (/\/lib\//i.test(url)) return "lib";
  if (/script\.js/i.test(url)) return "script";
  if (/\.(webp|png|jpg|jpeg|gif|svg|cur)(\?|$)/i.test(url)) return "image_other";
  return "other";
}

async function dismissOverlays(page) {
  await page.getByText("NO").click({ timeout: 3000 }).catch(() => {});
  await page.locator('text="BẢNG HƯỚNG DẪN"').click({ force: true, timeout: 2000 }).catch(() => {});
  await page.mouse.click(700, 220).catch(() => {});
  await page.keyboard.press("Escape").catch(() => {});
}

async function ensureMenuOpen(page) {
  const clickLeftMenuToggle = async () => {
    await page.mouse.click(330, 85).catch(() => {});
    await page.waitForTimeout(1200);
  };

  let items = await discoverMenuItems(page);
  if (items.length > 0) {
    return items;
  }

  await clickLeftMenuToggle();
  items = await discoverMenuItems(page);
  if (items.length > 0) {
    return items;
  }

  await page.mouse.click(800, 870).catch(() => {});
  await page.waitForTimeout(1200);
  return discoverMenuItems(page);
}

async function discoverMenuItems(page) {
  return page.evaluate(() => {
    const els = [...document.querySelectorAll("*")];
    const seen = new Set();
    const items = [];

    for (const el of els) {
      const s = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      const text = (el.innerText || "").trim().replace(/\s+/g, " ");
      const id = el.id || "";

      if (!text || text.length > 80 || s.pointerEvents === "none") continue;
      if (s.display === "none" || s.visibility === "hidden" || s.opacity === "0") continue;
      if (r.width < 150 || r.height < 24 || r.height > 60) continue;
      if (r.x < -10 || r.x > 380) continue;

      const key = `${text}|${Math.round(r.y)}`;
      if (seen.has(key)) continue;
      seen.add(key);

      items.push({
        id,
        text,
        x: Math.round(r.x),
        y: Math.round(r.y),
        width: Math.round(r.width),
        height: Math.round(r.height),
      });
    }

    return items.sort((a, b) => a.y - b.y || a.x - b.x);
  });
}

async function clickMenuItem(page, item) {
  const clicked = await page.evaluate((target) => {
    const candidates = [...document.querySelectorAll("*")].filter((el) => {
      const s = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      const text = (el.innerText || "").trim().replace(/\s+/g, " ");
      return (
        text === target.text &&
        s.display !== "none" &&
        s.visibility !== "hidden" &&
        s.opacity !== "0" &&
        r.width >= 150 &&
        r.height >= 24 &&
        r.height <= 60 &&
        r.x >= -10 &&
        r.x <= 380
      );
    });

    let el = candidates[0];
    if (!el) return false;

    while (el && getComputedStyle(el).pointerEvents === "none") {
      el = el.parentElement;
    }

    if (!el) return false;

    const eventInit = { bubbles: true, cancelable: true, view: window };
    el.dispatchEvent(new MouseEvent("mouseover", eventInit));
    el.dispatchEvent(new MouseEvent("mousedown", eventInit));
    el.dispatchEvent(new MouseEvent("mouseup", eventInit));
    el.dispatchEvent(new MouseEvent("click", eventInit));
    if (typeof el.click === "function") el.click();
    return true;
  }, item);

  return clicked;
}

async function main() {
  const browser = await chromium.launch({
    headless: HEADLESS,
    executablePath: "/usr/bin/google-chrome",
    args: ["--no-sandbox"],
  });

  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const assets = new Map();
  const clickedItems = [];

  const remember = (rawUrl, source) => {
    const url = normalizeUrl(rawUrl);
    if (!assets.has(url)) {
      assets.set(url, {
        url,
        category: categorize(url),
        source,
      });
    }
  };

  page.on("request", (request) => remember(request.url(), "request"));
  page.on("response", (response) => remember(response.url(), "response"));

  await page.goto(TOUR_URL, {
    waitUntil: "domcontentloaded",
    timeout: 120000,
  });

  await dismissOverlays(page);
  await page.waitForTimeout(INITIAL_WAIT_MS);
  await page.screenshot({ path: path.join(__dirname, "discover-map-initial.png") }).catch(() => {});

  const items = await ensureMenuOpen(page);
  const limitedItems = items.slice(0, MAX_ITEMS);
  console.log(`Discovered ${items.length} clickable menu item(s). Visiting ${limitedItems.length}.`);

  for (const item of limitedItems) {
    const ok = await clickMenuItem(page, item);
    if (!ok) {
      continue;
    }

    clickedItems.push(item.text);
    console.log(`Clicked: ${item.text}`);
    await page.waitForTimeout(CLICK_WAIT_MS);
    await dismissOverlays(page);
  }

  await page.screenshot({ path: path.join(__dirname, "discover-map-final.png") }).catch(() => {});

  const grouped = {};
  for (const asset of assets.values()) {
    grouped[asset.category] ||= [];
    grouped[asset.category].push(asset.url);
  }

  for (const key of Object.keys(grouped)) {
    grouped[key].sort();
  }

  const output = {
    discoveredAt: new Date().toISOString(),
    initialWaitMs: INITIAL_WAIT_MS,
    clickWaitMs: CLICK_WAIT_MS,
    clickedItems,
    menuItems: items,
    counts: Object.fromEntries(Object.entries(grouped).map(([key, list]) => [key, list.length])),
    assets: grouped,
  };

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2));
  console.log(`Saved map discovery to ${OUTPUT_FILE}`);
  console.log(JSON.stringify(output.counts, null, 2));

  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
