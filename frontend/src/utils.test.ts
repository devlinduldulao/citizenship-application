import { describe, expect, it } from "vitest"
import { getInitials, handleError } from "./utils"

describe("getInitials", () => {
  it("returns two uppercased initials for a two-word name", () => {
    expect(getInitials("Ola Nordmann")).toBe("ON")
  })

  it("returns one initial for a single-word name", () => {
    expect(getInitials("Ola")).toBe("O")
  })

  it("limits to first two words", () => {
    expect(getInitials("Ola Nordmann Jensen")).toBe("ON")
  })

  it("uppercases lowercase input", () => {
    expect(getInitials("ola nordmann")).toBe("ON")
  })

  it("handles mixed casing", () => {
    expect(getInitials("øla NORDMANN")).toBe("ØN")
  })

  it("handles extra whitespace between words", () => {
    const result = getInitials("Alice Bob")
    expect(result).toContain("A")
  })
})

describe("handleError", () => {
  it("calls the bound toast function with error detail string", () => {
    let captured = ""
    const showToast = (msg: string) => {
      captured = msg
    }
    const boundHandler = handleError.bind(showToast)
    boundHandler({ body: { detail: "Not Found" } } as any)
    expect(captured).toBe("Not Found")
  })

  it("extracts first validation error from array detail", () => {
    let captured = ""
    const showToast = (msg: string) => {
      captured = msg
    }
    const boundHandler = handleError.bind(showToast)
    boundHandler({
      body: { detail: [{ msg: "Field required" }] },
    } as any)
    expect(captured).toBe("Field required")
  })

  it("falls back to default message when no detail", () => {
    let captured = ""
    const showToast = (msg: string) => {
      captured = msg
    }
    const boundHandler = handleError.bind(showToast)
    boundHandler({ body: {} } as any)
    expect(captured).toBe("Something went wrong.")
  })
})
