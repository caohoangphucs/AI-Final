const fs = require("fs");
const path = require("path");
const readline = require("readline");
const { chromium, request } = require("playwright");

const TARGET_URL = "https://360.hcmute.edu.vn/"; // đổi URL
const OUTPUT_DIR = path.join(__dirname, "downloaded_images");

const imageUrls = new Map();

function sanitizePathPart(value) {
  return value.replace(/[<>:"\\|?*\x00-\x1F]/g, "_");
}

function safePathFromUrl(imageUrl, contentType = "") {
  const u = new URL(imageUrl);
  const parts = decodeURIComponent(u.pathname)
    .split("/")
    .filter(Boolean)
    .map(sanitizePathPart);
  const panoramaIndex = parts.findIndex((part) => part.startsWith("panorama_"));

  if (panoramaIndex !== -1) {
    const panoramaFolder = parts[panoramaIndex];
    const relativeParts = parts.slice(panoramaIndex + 1);

    if (relativeParts.length === 0) {
      relativeParts.push(`index${guessExtFromContentType(contentType)}`);
    }

    const lastIndex = relativeParts.length - 1;
    if (!path.extname(relativeParts[lastIndex])) {
      relativeParts[lastIndex] += guessExtFromContentType(contentType);
    }

    return path.join(OUTPUT_DIR, panoramaFolder, ...relativeParts);
  }

  if (parts.length === 0) {
    parts.push(`index${guessExtFromContentType(contentType)}`);
  }

  const lastIndex = parts.length - 1;
  if (!path.extname(parts[lastIndex])) {
    parts[lastIndex] += guessExtFromContentType(contentType);
  }

  return path.join(OUTPUT_DIR, sanitizePathPart(u.hostname), ...parts);
}

function guessExtFromContentType(contentType) {
  if (!contentType) return ".img";

  if (contentType.includes("image/jpeg")) return ".jpg";
  if (contentType.includes("image/png")) return ".png";
  if (contentType.includes("image/webp")) return ".webp";
  if (contentType.includes("image/gif")) return ".gif";
  if (contentType.includes("image/svg")) return ".svg";
  if (contentType.includes("image/avif")) return ".avif";

  return ".img";
}

function getExistingFilePath(imageUrl, contentType = "") {
  const guessedPath = safePathFromUrl(imageUrl, contentType);
  if (fs.existsSync(guessedPath)) {
    return guessedPath;
  }

  if (path.extname(guessedPath) !== ".img") {
    return null;
  }

  const resolvedPath = guessedPath.replace(/\.img$/, guessExtFromContentType(contentType));
  if (fs.existsSync(resolvedPath)) {
    return resolvedPath;
  }

  return null;
}

async function downloadAll(apiContext) {
  const pendingEntries = [...imageUrls.entries()].filter(([, info]) => !info.downloaded);

  console.log(`\nDownloading ${pendingEntries.length} pending image(s)...`);

  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  let ok = 0;
  let fail = 0;
  let skipped = 0;

  for (const [url, info] of pendingEntries) {
    try {
      const existingFilePath = getExistingFilePath(url, info.contentType || "");
      if (existingFilePath) {
        info.downloaded = true;
        info.filePath = existingFilePath;
        console.log("Skip saved:", existingFilePath);
        skipped++;
        continue;
      }

      const res = await apiContext.get(url, {
        headers: {
          referer: info.referer || TARGET_URL,
          "user-agent": info.userAgent || "",
        },
        timeout: 60000,
      });

      if (!res.ok()) {
        console.warn("Failed:", res.status(), url);
        fail++;
        continue;
      }

      const buffer = await res.body();
      const contentType = res.headers()["content-type"] || info.contentType || "";
      const filePath = safePathFromUrl(url, contentType);

      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(filePath, buffer);
      info.downloaded = true;
      info.filePath = filePath;

      console.log("Saved:", filePath);
      ok++;
    } catch (err) {
      console.warn("Skip:", url, err.message);
      fail++;
    }
  }

  console.log(`\nDone. Saved: ${ok}, Skipped existing: ${skipped}, Failed: ${fail}`);
  console.log(`Folder: ${OUTPUT_DIR}\n`);
}

(async () => {
  const browser = await chromium.launch({
    headless: false,
    executablePath: "/usr/bin/google-chrome",
    args: ["--no-sandbox"],
  });

  const context = await browser.newContext();
  const page = await context.newPage();
  const apiContext = await request.newContext();
  let activeDownload = null;
  let isClosing = false;

  page.on("response", async (response) => {
    try {
      const request = response.request();
      const url = response.url();
      const headers = response.headers();
      const contentType = headers["content-type"] || "";

      const isImage =
        request.resourceType() === "image" ||
        contentType.startsWith("image/") ||
        /\.(png|jpe?g|webp|gif|svg|avif)(\?|$)/i.test(url);

      if (!isImage) return;

      if (!imageUrls.has(url)) {
        const existingFilePath = getExistingFilePath(url, contentType);
        imageUrls.set(url, {
          contentType,
          referer: request.headers()["referer"] || TARGET_URL,
          userAgent: request.headers()["user-agent"] || "",
          downloaded: Boolean(existingFilePath),
          filePath: existingFilePath || null,
        });

        if (existingFilePath) {
          console.log(`[${imageUrls.size}] Already saved: ${existingFilePath}`);
        } else {
          console.log(`[${imageUrls.size}] Found image: ${url}`);
        }
      }
    } catch (err) {
      console.warn("Response error:", err.message);
    }
  });

  await page.goto(TARGET_URL, {
    waitUntil: "domcontentloaded",
    timeout: 120000,
  });

  console.log("\nBrowser opened.");
  console.log("Bạn cứ thao tác trong trình duyệt.");
  console.log("Khi muốn tải toàn bộ ảnh đã request, quay lại terminal và bấm Enter.");
  console.log("Gõ q rồi Enter để thoát.\n");

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  rl.on("line", async (line) => {
    const cmd = line.trim().toLowerCase();

    if (cmd === "q" || cmd === "quit" || cmd === "exit") {
      isClosing = true;
      console.log("Closing...");
      if (activeDownload) {
        console.log("Đợi lượt tải hiện tại hoàn tất...");
        await activeDownload;
      }
      await apiContext.dispose();
      rl.close();
      await browser.close();
      process.exit(0);
    }

    if (isClosing) {
      return;
    }

    if (activeDownload) {
      console.log("Đang tải dở, chờ một chút rồi bấm Enter lại.");
      return;
    }

    activeDownload = downloadAll(apiContext);
    try {
      await activeDownload;
    } finally {
      activeDownload = null;
    }
    console.log("Tiếp tục thao tác trong browser, bấm Enter lần nữa để tải thêm.");
  });
})();
