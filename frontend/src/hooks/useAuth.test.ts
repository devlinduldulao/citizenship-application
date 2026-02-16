import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Stub localStorage with a simple in-memory implementation
const store: Record<string, string> = {}
const localStorageMock = {
  getItem: (key: string) => store[key] ?? null,
  setItem: (key: string, value: string) => {
    store[key] = value
  },
  removeItem: (key: string) => {
    delete store[key]
  },
  clear: () => {
    for (const key of Object.keys(store)) delete store[key]
  },
}

vi.stubGlobal("localStorage", localStorageMock)

// Import after mocking
const { isLoggedIn } = await import("@/hooks/useAuth")

describe("isLoggedIn", () => {
  beforeEach(() => {
    localStorageMock.clear()
  })

  afterEach(() => {
    localStorageMock.clear()
  })

  it("returns false when no token in localStorage", () => {
    expect(isLoggedIn()).toBe(false)
  })

  it("returns true when access_token exists", () => {
    localStorageMock.setItem("access_token", "some-jwt-token")
    expect(isLoggedIn()).toBe(true)
  })

  it("returns false after token is removed", () => {
    localStorageMock.setItem("access_token", "token")
    localStorageMock.removeItem("access_token")
    expect(isLoggedIn()).toBe(false)
  })
})
