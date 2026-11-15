#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const dir = path.join(__dirname, "..", ".lock-parts");
const out = path.join(__dirname, "..", "package-lock.json");
if (fs.existsSync(out) && fs.statSync(out).size > 1000) process.exit(0);
if (!fs.existsSync(dir)) process.exit(0);
const parts = fs.readdirSync(dir).filter((f) => f.endsWith(".txt")).sort();
if (!parts.length) process.exit(0);
const content = parts.map((f) => fs.readFileSync(path.join(dir, f), "utf8")).join("");
fs.writeFileSync(out, content);
console.log("assembled package-lock.json from", parts.length, "parts");
