const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const TOUR_URL = "https://cloud.3dvista.com//hosting/8186875/0/index.htm";
const OUTPUT_FILE = path.join(__dirname, "discovered-assets.json");
const WAIT_MS = Number.parseInt(process.env.DISCOVER_WAIT_MS || "45000", 10);

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

async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/usr/bin/google-chrome",
    args: ["--no-sandbox"],
  });

  const page = await browser.newPage();
  const assets = new Map();

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

  page.on("request", (request) => {
    remember(request.url(), "request");
  });

  page.on("response", (response) => {
    remember(response.url(), "response");
  });

  await page.goto(TOUR_URL, {
    waitUntil: "domcontentloaded",
    timeout: 120000,
  });

  await page.waitForTimeout(WAIT_MS);

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
    waitMs: WAIT_MS,
    counts: Object.fromEntries(Object.entries(grouped).map(([key, list]) => [key, list.length])),
    assets: grouped,
  };

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2));
  console.log(`Saved asset discovery to ${OUTPUT_FILE}`);
  console.log(JSON.stringify(output.counts, null, 2));

  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
