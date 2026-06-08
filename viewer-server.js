const fs = require("fs");
const http = require("http");
const path = require("path");

const ROOT = __dirname;
const START_PORT = Number.parseInt(process.env.PORT || "4173", 10);
const MAX_PORT_ATTEMPTS = 20;

const CONTENT_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
};

function resolveFile(requestUrl) {
  const cleanPath = decodeURIComponent((requestUrl || "/").split("?")[0]);
  const relativePath = cleanPath === "/" ? "viewer/index.html" : cleanPath.replace(/^\/+/, "");
  const absolutePath = path.normalize(path.join(ROOT, relativePath));

  if (!absolutePath.startsWith(ROOT)) {
    return null;
  }

  return absolutePath;
}

function createServer() {
  return http.createServer((req, res) => {
    const filePath = resolveFile(req.url);

    if (!filePath) {
      res.writeHead(403);
      res.end("Forbidden");
      return;
    }

    fs.readFile(filePath, (error, data) => {
      if (error) {
        res.writeHead(error.code === "ENOENT" ? 404 : 500);
        res.end(error.code === "ENOENT" ? "Not found" : "Server error");
        return;
      }

      res.writeHead(200, {
        "Content-Type": CONTENT_TYPES[path.extname(filePath).toLowerCase()] || "application/octet-stream",
        "Cache-Control": "no-cache",
      });
      res.end(data);
    });
  });
}

function listenOnPort(port, remainingAttempts) {
  const server = createServer();

  server
    .once("error", (error) => {
      if (error.code === "EADDRINUSE" && remainingAttempts > 0) {
        console.warn(`Port ${port} is busy, trying ${port + 1}...`);
        listenOnPort(port + 1, remainingAttempts - 1);
        return;
      }

      throw error;
    })
    .listen(port, () => {
      console.log(`Panorama viewer: http://localhost:${port}/`);
      console.log("Build first with: npm run build:panoramas");
    });
}

listenOnPort(START_PORT, MAX_PORT_ATTEMPTS);
