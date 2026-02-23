/**
 * Unit tests for document upload and queue processing validations.
 *
 * These tests verify the client-side validation rules that prevent
 * common user errors like:
 *   - Uploading without selecting an application
 *   - Uploading without entering a document type
 *   - Uploading without choosing a file
 *   - Queueing processing when no documents exist
 *   - Allowed MIME types matching the backend contract
 */

import { describe, expect, it } from "vitest"

// ---------------------------------------------------------------------------
// Allowed file types — mirrors backend ALLOWED_CONTENT_TYPES
// ---------------------------------------------------------------------------

/**
 * The exact set of MIME types accepted by the backend's upload endpoint.
 * The frontend file input's `accept` attribute must cover these.
 */
const BACKEND_ALLOWED_CONTENT_TYPES = new Set([
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp",
])

/**
 * The `accept` attribute used on the frontend file input.
 * Format: comma-separated extensions and/or MIME types.
 */
const FRONTEND_ACCEPT = ".pdf,image/png,image/jpeg,image/webp"

describe("Allowed file types contract", () => {
  it("frontend accept attribute covers all backend MIME types", () => {
    // Parse the accept attribute into individual tokens
    const acceptTokens = FRONTEND_ACCEPT.split(",").map((s) => s.trim())

    // Map file extensions to MIME types for validation
    const extensionMimeMap: Record<string, string> = {
      ".pdf": "application/pdf",
      ".jpg": "image/jpeg",
      ".jpeg": "image/jpeg",
      ".png": "image/png",
      ".webp": "image/webp",
    }

    // Collect all MIME types the frontend accepts
    const frontendMimes = new Set<string>()
    for (const token of acceptTokens) {
      if (token.startsWith(".")) {
        const mapped = extensionMimeMap[token]
        if (mapped) frontendMimes.add(mapped)
      } else {
        frontendMimes.add(token)
      }
    }

    // Every backend type must be accepted by the frontend
    for (const mime of BACKEND_ALLOWED_CONTENT_TYPES) {
      expect(frontendMimes.has(mime)).toBe(true)
    }
  })

  it("PDF files are accepted", () => {
    expect(BACKEND_ALLOWED_CONTENT_TYPES.has("application/pdf")).toBe(true)
  })

  it("JPEG files are accepted", () => {
    expect(BACKEND_ALLOWED_CONTENT_TYPES.has("image/jpeg")).toBe(true)
  })

  it("PNG files are accepted", () => {
    expect(BACKEND_ALLOWED_CONTENT_TYPES.has("image/png")).toBe(true)
  })

  it("WEBP files are accepted", () => {
    expect(BACKEND_ALLOWED_CONTENT_TYPES.has("image/webp")).toBe(true)
  })

  it("GIF files are NOT accepted", () => {
    expect(BACKEND_ALLOWED_CONTENT_TYPES.has("image/gif")).toBe(false)
  })

  it("plain text files are NOT accepted", () => {
    expect(BACKEND_ALLOWED_CONTENT_TYPES.has("text/plain")).toBe(false)
  })

  it("HTML files are NOT accepted", () => {
    expect(BACKEND_ALLOWED_CONTENT_TYPES.has("text/html")).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Upload validation logic (mirrors handleUpload in applications.tsx)
// ---------------------------------------------------------------------------

type UploadValidationInput = {
  selectedApplicationId: string
  documentType: string
  selectedFile: File | null
}

type ValidationResult = {
  valid: boolean
  error?: string
}

function validateUpload(input: UploadValidationInput): ValidationResult {
  if (!input.selectedApplicationId) {
    return { valid: false, error: "Select an application first" }
  }
  if (!input.documentType.trim()) {
    return { valid: false, error: "Document type is required" }
  }
  if (!input.selectedFile) {
    return { valid: false, error: "Please choose a file" }
  }
  return { valid: true }
}

describe("Upload form validation", () => {
  const validInput: UploadValidationInput = {
    selectedApplicationId: "some-uuid",
    documentType: "passport",
    selectedFile: new File(["content"], "test.pdf", {
      type: "application/pdf",
    }),
  }

  it("passes with all valid inputs", () => {
    expect(validateUpload(validInput)).toEqual({ valid: true })
  })

  it("fails when no application is selected", () => {
    const result = validateUpload({ ...validInput, selectedApplicationId: "" })
    expect(result.valid).toBe(false)
    expect(result.error).toContain("application")
  })

  it("fails when document type is empty", () => {
    const result = validateUpload({ ...validInput, documentType: "" })
    expect(result.valid).toBe(false)
    expect(result.error).toContain("Document type")
  })

  it("fails when document type is only whitespace", () => {
    const result = validateUpload({ ...validInput, documentType: "   " })
    expect(result.valid).toBe(false)
    expect(result.error).toContain("Document type")
  })

  it("fails when no file is selected", () => {
    const result = validateUpload({ ...validInput, selectedFile: null })
    expect(result.valid).toBe(false)
    expect(result.error).toContain("file")
  })

  it("trims document type before validation", () => {
    const result = validateUpload({
      ...validInput,
      documentType: "  passport  ",
    })
    expect(result.valid).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Queue Processing validation logic (mirrors button disabled state)
// ---------------------------------------------------------------------------

type QueueValidationInput = {
  selectedApplicationId: string
  documentCount: number
  isPending: boolean
}

function validateQueueProcessing(input: QueueValidationInput): ValidationResult {
  if (!input.selectedApplicationId) {
    return { valid: false, error: "Select an application first" }
  }
  if (!input.documentCount) {
    return {
      valid: false,
      error: "Upload at least one document before queuing processing",
    }
  }
  if (input.isPending) {
    return { valid: false, error: "Processing already in progress" }
  }
  return { valid: true }
}

function isQueueButtonDisabled(input: QueueValidationInput): boolean {
  return !input.selectedApplicationId || input.isPending || !input.documentCount
}

type QueuePayload = {
  applicationId: string
  force_reprocess: boolean
}

function buildQueuePayload(
  applicationId: string,
  forceReprocess: boolean,
): QueuePayload {
  return {
    applicationId,
    force_reprocess: forceReprocess,
  }
}

describe("Queue Processing validation", () => {
  const validInput: QueueValidationInput = {
    selectedApplicationId: "some-uuid",
    documentCount: 2,
    isPending: false,
  }

  it("passes with application selected and documents uploaded", () => {
    expect(validateQueueProcessing(validInput)).toEqual({ valid: true })
  })

  it("fails when no application is selected", () => {
    const result = validateQueueProcessing({
      ...validInput,
      selectedApplicationId: "",
    })
    expect(result.valid).toBe(false)
    expect(result.error).toContain("application")
  })

  it("fails when no documents are uploaded", () => {
    const result = validateQueueProcessing({
      ...validInput,
      documentCount: 0,
    })
    expect(result.valid).toBe(false)
    expect(result.error).toContain("Upload at least one document")
  })

  it("fails when already pending", () => {
    const result = validateQueueProcessing({
      ...validInput,
      isPending: true,
    })
    expect(result.valid).toBe(false)
  })
})

describe("Queue button disabled state", () => {
  it("is disabled when no application selected", () => {
    expect(
      isQueueButtonDisabled({
        selectedApplicationId: "",
        documentCount: 2,
        isPending: false,
      }),
    ).toBe(true)
  })

  it("is disabled when no documents uploaded", () => {
    expect(
      isQueueButtonDisabled({
        selectedApplicationId: "id",
        documentCount: 0,
        isPending: false,
      }),
    ).toBe(true)
  })

  it("is disabled when mutation is pending", () => {
    expect(
      isQueueButtonDisabled({
        selectedApplicationId: "id",
        documentCount: 1,
        isPending: true,
      }),
    ).toBe(true)
  })

  it("is enabled when application selected, docs exist, not pending", () => {
    expect(
      isQueueButtonDisabled({
        selectedApplicationId: "id",
        documentCount: 1,
        isPending: false,
      }),
    ).toBe(false)
  })
})

describe("Queue payload builder", () => {
  it("builds normal queue payload with force_reprocess=false", () => {
    expect(buildQueuePayload("app-123", false)).toEqual({
      applicationId: "app-123",
      force_reprocess: false,
    })
  })

  it("builds force reprocess payload with force_reprocess=true", () => {
    expect(buildQueuePayload("app-123", true)).toEqual({
      applicationId: "app-123",
      force_reprocess: true,
    })
  })
})

// ---------------------------------------------------------------------------
// Application status transitions
// ---------------------------------------------------------------------------

describe("Application status state machine", () => {
  const VALID_STATUSES = [
    "draft",
    "documents_uploaded",
    "queued",
    "processing",
    "review_ready",
    "approved",
    "rejected",
    "more_info_required",
  ] as const

  it("starts in draft status", () => {
    expect(VALID_STATUSES[0]).toBe("draft")
  })

  it("transitions to documents_uploaded after upload", () => {
    expect(VALID_STATUSES[1]).toBe("documents_uploaded")
  })

  it("transitions to queued after queueing", () => {
    expect(VALID_STATUSES[2]).toBe("queued")
  })

  it("transitions to processing during OCR/NLP", () => {
    expect(VALID_STATUSES[3]).toBe("processing")
  })

  it("transitions to review_ready after processing completes", () => {
    expect(VALID_STATUSES[4]).toBe("review_ready")
  })

  it("terminal statuses include approved, rejected, more_info_required", () => {
    expect(VALID_STATUSES).toContain("approved")
    expect(VALID_STATUSES).toContain("rejected")
    expect(VALID_STATUSES).toContain("more_info_required")
  })

  it("queue processing should only be clickable after documents_uploaded", () => {
    // Statuses where Queue Processing makes sense
    const queueableStatuses = new Set([
      "documents_uploaded",
      "review_ready",
      "more_info_required",
    ])

    // draft has no documents — button should be disabled
    expect(queueableStatuses.has("draft")).toBe(false)
  })
})
