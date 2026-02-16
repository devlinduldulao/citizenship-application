import { describe, expect, it } from "vitest"
import { cn } from "./utils"

describe("cn (class name merge utility)", () => {
  it("merges multiple class strings", () => {
    expect(cn("px-2", "py-1")).toBe("px-2 py-1")
  })

  it("handles conflicting Tailwind classes by using the last one", () => {
    expect(cn("px-2", "px-4")).toBe("px-4")
  })

  it("handles undefined and null inputs", () => {
    expect(cn("px-2", undefined, null, "py-1")).toBe("px-2 py-1")
  })

  it("handles conditional classes via clsx patterns", () => {
    const isActive = true
    const isDisabled = false
    expect(cn("base", isActive && "active", isDisabled && "disabled")).toBe(
      "base active",
    )
  })

  it("returns empty string for no arguments", () => {
    expect(cn()).toBe("")
  })

  it("handles empty string inputs", () => {
    expect(cn("", "px-2", "")).toBe("px-2")
  })

  it("merges color classes correctly", () => {
    expect(cn("text-red-500", "text-blue-600")).toBe("text-blue-600")
  })

  it("preserves non-conflicting classes from both inputs", () => {
    expect(cn("px-2 py-1", "mt-4")).toBe("px-2 py-1 mt-4")
  })
})
