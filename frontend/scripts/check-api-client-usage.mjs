import { readdirSync, readFileSync, statSync } from "node:fs"
import path from "node:path"

const projectRoot = process.cwd()
const srcRoot = path.join(projectRoot, "src")

const excludedDirectories = new Set([
  "client",
  "node_modules",
  "dist",
  ".tanstack",
])

const sourceExtensions = new Set([".ts", ".tsx", ".js", ".jsx"])

const forbiddenPatterns = [
  {
    label: "manual fetch() usage",
    regex: /\bfetch\s*\(/g,
  },
  {
    label: "manual axios() usage",
    regex: /\baxios\s*\(/g,
  },
  {
    label: "hardcoded /api/v1 path",
    regex: /["'`]\/api\/v1\//g,
  },
]

const filesToCheck = []
collectFiles(srcRoot, filesToCheck)

const violations = []
for (const filePath of filesToCheck) {
  const source = readFileSync(filePath, "utf-8")
  for (const pattern of forbiddenPatterns) {
    const matches = [...source.matchAll(pattern.regex)]
    for (const match of matches) {
      const index = match.index ?? 0
      const line = source.slice(0, index).split("\n").length
      violations.push({
        filePath,
        line,
        label: pattern.label,
      })
    }
  }
}

if (violations.length > 0) {
  console.error(
    "\nAPI client usage guard failed. Use generated services from src/client (e.g., ApplicationsService, UsersService, etc.) instead of direct HTTP calls.\n",
  )

  for (const violation of violations) {
    const relativePath = path.relative(projectRoot, violation.filePath)
    console.error(`- ${relativePath}:${violation.line} -> ${violation.label}`)
  }

  process.exit(1)
}

console.log(
  `API client usage guard passed (${filesToCheck.length} source files checked).`,
)

function collectFiles(currentDirectory, output) {
  const entries = readdirSync(currentDirectory)

  for (const entry of entries) {
    const fullPath = path.join(currentDirectory, entry)
    const entryStats = statSync(fullPath)

    if (entryStats.isDirectory()) {
      if (excludedDirectories.has(entry)) {
        continue
      }
      collectFiles(fullPath, output)
      continue
    }

    const extension = path.extname(entry)
    if (sourceExtensions.has(extension)) {
      output.push(fullPath)
    }
  }
}
