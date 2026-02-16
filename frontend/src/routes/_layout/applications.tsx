import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { LoaderCircle, Upload } from "lucide-react"
import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"

type ApplicationStatus =
  | "draft"
  | "documents_uploaded"
  | "queued"
  | "processing"
  | "review_ready"
  | "approved"
  | "rejected"
  | "more_info_required"

type DocumentStatus = "uploaded" | "processing" | "processed" | "failed"

interface CitizenshipApplication {
  id: string
  applicant_full_name: string
  applicant_nationality: string
  notes?: string | null
  status: ApplicationStatus
  recommendation_summary?: string | null
  confidence_score?: number | null
  priority_score?: number
  sla_due_at?: string | null
  created_at?: string | null
}

interface CitizenshipApplicationList {
  data: CitizenshipApplication[]
  count: number
}

interface ApplicationDocument {
  id: string
  application_id: string
  document_type: string
  original_filename: string
  status: DocumentStatus
  file_size_bytes: number
}

interface ApplicationDocumentList {
  data: ApplicationDocument[]
  count: number
}

interface EligibilityRuleResult {
  id: string
  rule_code: string
  rule_name: string
  passed: boolean
  score: number
  weight: number
  rationale: string
  evidence: Record<string, unknown>
}

interface DecisionBreakdown {
  application_id: string
  recommendation: string
  confidence_score: number
  risk_level: string
  rules: EligibilityRuleResult[]
}

interface ApplicationAuditEvent {
  id: string
  action: string
  reason?: string | null
  event_metadata: Record<string, unknown>
  actor_user_id?: string | null
  created_at?: string | null
}

interface ApplicationAuditTrail {
  application_id: string
  events: ApplicationAuditEvent[]
}

interface ReviewQueueItem {
  id: string
  applicant_full_name: string
  applicant_nationality: string
  status: ApplicationStatus
  recommendation_summary?: string | null
  confidence_score?: number | null
  risk_level: string
  priority_score: number
  sla_due_at?: string | null
  is_overdue: boolean
}

interface ReviewQueueResponse {
  data: ReviewQueueItem[]
  count: number
}

interface ReviewQueueMetrics {
  pending_manual_count: number
  overdue_count: number
  high_priority_count: number
  avg_waiting_days: number
  daily_manual_capacity: number
  estimated_days_to_clear_backlog: number
}

type ReviewAction = "approve" | "reject" | "request_more_info"

const API_BASE = import.meta.env.VITE_API_URL

const getAuthHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
})

const fetchJson = async <T,>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.headers || {}),
      ...getAuthHeaders(),
    },
  })

  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: "Request failed" }))
    throw new Error(body.detail || "Request failed")
  }

  return response.json() as Promise<T>
}

const createApplication = async (payload: {
  applicant_full_name: string
  applicant_nationality: string
  notes?: string
}) => {
  return fetchJson<CitizenshipApplication>("/api/v1/applications/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })
}

const uploadDocument = async (payload: {
  applicationId: string
  documentType: string
  file: File
}) => {
  const formData = new FormData()
  formData.append("document_type", payload.documentType)
  formData.append("file", payload.file)

  return fetchJson<ApplicationDocument>(
    `/api/v1/applications/${payload.applicationId}/documents`,
    {
      method: "POST",
      body: formData,
    },
  )
}

const queueProcessing = async (applicationId: string) => {
  return fetchJson<CitizenshipApplication>(
    `/api/v1/applications/${applicationId}/process`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ force_reprocess: false }),
    },
  )
}

const getStatusBadgeVariant = (status: ApplicationStatus) => {
  if (status === "approved") return "default"
  if (status === "rejected") return "destructive"
  if (status === "more_info_required") return "secondary"
  if (status === "review_ready") return "default"
  if (status === "processing" || status === "queued") return "secondary"
  return "outline"
}

export const Route = createFileRoute("/_layout/applications")({
  component: ApplicationsPage,
  head: () => ({
    meta: [
      {
        title: "Applications - Citizenship MVP",
      },
    ],
  }),
})

function ApplicationsPage() {
  const queryClient = useQueryClient()
  const { user: currentUser } = useAuth()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [applicantFullName, setApplicantFullName] = useState("")
  const [applicantNationality, setApplicantNationality] = useState("")
  const [applicationNotes, setApplicationNotes] = useState("")
  const [selectedApplicationId, setSelectedApplicationId] = useState("")
  const [documentType, setDocumentType] = useState("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [reviewReason, setReviewReason] = useState("")

  const reviewQueueQuery = useQuery({
    queryKey: ["review-queue"],
    queryFn: () =>
      fetchJson<ReviewQueueResponse>(
        "/api/v1/applications/queue/review?skip=0&limit=5",
      ),
    enabled: Boolean(currentUser?.is_superuser),
  })

  const reviewQueueMetricsQuery = useQuery({
    queryKey: ["review-queue-metrics"],
    queryFn: () =>
      fetchJson<ReviewQueueMetrics>("/api/v1/applications/queue/metrics"),
    enabled: Boolean(currentUser?.is_superuser),
  })

  const applicationsQuery = useQuery({
    queryKey: ["citizenship-applications"],
    queryFn: () =>
      fetchJson<CitizenshipApplicationList>(
        "/api/v1/applications/?skip=0&limit=100",
      ),
  })

  const documentsQuery = useQuery({
    queryKey: ["application-documents", selectedApplicationId],
    queryFn: () =>
      fetchJson<ApplicationDocumentList>(
        `/api/v1/applications/${selectedApplicationId}/documents`,
      ),
    enabled: Boolean(selectedApplicationId),
  })

  const breakdownQuery = useQuery({
    queryKey: ["application-breakdown", selectedApplicationId],
    queryFn: () =>
      fetchJson<DecisionBreakdown>(
        `/api/v1/applications/${selectedApplicationId}/decision-breakdown`,
      ),
    enabled: Boolean(selectedApplicationId),
  })

  const auditTrailQuery = useQuery({
    queryKey: ["application-audit-trail", selectedApplicationId],
    queryFn: () =>
      fetchJson<ApplicationAuditTrail>(
        `/api/v1/applications/${selectedApplicationId}/audit-trail`,
      ),
    enabled: Boolean(selectedApplicationId),
  })

  const createMutation = useMutation({
    mutationFn: createApplication,
    onSuccess: (application) => {
      showSuccessToast("Application created successfully")
      setApplicantFullName("")
      setApplicantNationality("")
      setApplicationNotes("")
      setSelectedApplicationId(application.id)
      queryClient.invalidateQueries({ queryKey: ["citizenship-applications"] })
      queryClient.invalidateQueries({ queryKey: ["review-queue"] })
      queryClient.invalidateQueries({ queryKey: ["review-queue-metrics"] })
    },
    onError: (error: Error) => showErrorToast(error.message),
  })

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      showSuccessToast("Document uploaded")
      setDocumentType("")
      setSelectedFile(null)
      queryClient.invalidateQueries({ queryKey: ["citizenship-applications"] })
      queryClient.invalidateQueries({ queryKey: ["review-queue"] })
      queryClient.invalidateQueries({ queryKey: ["review-queue-metrics"] })
      queryClient.invalidateQueries({
        queryKey: ["application-documents", selectedApplicationId],
      })
      queryClient.invalidateQueries({
        queryKey: ["application-breakdown", selectedApplicationId],
      })
    },
    onError: (error: Error) => showErrorToast(error.message),
  })

  const processMutation = useMutation({
    mutationFn: queueProcessing,
    onSuccess: () => {
      showSuccessToast("Processing queued")
      queryClient.invalidateQueries({ queryKey: ["citizenship-applications"] })
      queryClient.invalidateQueries({
        queryKey: ["application-documents", selectedApplicationId],
      })
      queryClient.invalidateQueries({
        queryKey: ["application-breakdown", selectedApplicationId],
      })
      queryClient.invalidateQueries({
        queryKey: ["application-audit-trail", selectedApplicationId],
      })
    },
    onError: (error: Error) => showErrorToast(error.message),
  })

  const reviewDecisionMutation = useMutation({
    mutationFn: (payload: {
      applicationId: string
      action: ReviewAction
      reason: string
    }) =>
      fetchJson<CitizenshipApplication>(
        `/api/v1/applications/${payload.applicationId}/review-decision`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            action: payload.action,
            reason: payload.reason,
          }),
        },
      ),
    onSuccess: () => {
      showSuccessToast("Caseworker decision saved")
      setReviewReason("")
      queryClient.invalidateQueries({ queryKey: ["citizenship-applications"] })
      queryClient.invalidateQueries({ queryKey: ["review-queue"] })
      queryClient.invalidateQueries({ queryKey: ["review-queue-metrics"] })
      queryClient.invalidateQueries({
        queryKey: ["application-breakdown", selectedApplicationId],
      })
      queryClient.invalidateQueries({
        queryKey: ["application-audit-trail", selectedApplicationId],
      })
    },
    onError: (error: Error) => showErrorToast(error.message),
  })

  const sortedApplications = useMemo(() => {
    const rows = applicationsQuery.data?.data || []
    return [...rows].sort((left, right) => {
      const leftDate = left.created_at ? new Date(left.created_at).getTime() : 0
      const rightDate = right.created_at
        ? new Date(right.created_at).getTime()
        : 0
      return rightDate - leftDate
    })
  }, [applicationsQuery.data?.data])

  const handleCreateApplication = () => {
    if (!applicantFullName.trim() || !applicantNationality.trim()) {
      showErrorToast("Full name and nationality are required")
      return
    }

    createMutation.mutate({
      applicant_full_name: applicantFullName.trim(),
      applicant_nationality: applicantNationality.trim(),
      notes: applicationNotes.trim() || undefined,
    })
  }

  const handleUpload = () => {
    if (!selectedApplicationId) {
      showErrorToast("Select an application first")
      return
    }
    if (!documentType.trim()) {
      showErrorToast("Document type is required")
      return
    }
    if (!selectedFile) {
      showErrorToast("Please choose a file")
      return
    }

    uploadMutation.mutate({
      applicationId: selectedApplicationId,
      documentType: documentType.trim(),
      file: selectedFile,
    })
  }

  const submitReviewDecision = (action: ReviewAction) => {
    if (!selectedApplicationId) {
      showErrorToast("Select an application first")
      return
    }
    if (reviewReason.trim().length < 8) {
      showErrorToast("Please provide a clear reason (at least 8 characters)")
      return
    }

    reviewDecisionMutation.mutate({
      applicationId: selectedApplicationId,
      action,
      reason: reviewReason.trim(),
    })
  }

  return (
    <div className="flex flex-col gap-6">
      {currentUser?.is_superuser && (
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle>Manual Review Workload</CardTitle>
            <CardDescription>
              Backlog pressure and SLA risk indicators for reviewer planning.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {reviewQueueMetricsQuery.isLoading && (
              <p className="text-sm text-muted-foreground">
                Loading queue metrics…
              </p>
            )}
            {!reviewQueueMetricsQuery.isLoading &&
              reviewQueueMetricsQuery.data && (
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="bg-muted/30 border-border/60 rounded-md border p-3">
                    <p className="text-xs text-muted-foreground">
                      Pending Manual
                    </p>
                    <p className="text-xl font-semibold">
                      {reviewQueueMetricsQuery.data.pending_manual_count}
                    </p>
                  </div>
                  <div className="bg-muted/30 border-border/60 rounded-md border p-3">
                    <p className="text-xs text-muted-foreground">Overdue SLA</p>
                    <p className="text-xl font-semibold text-destructive">
                      {reviewQueueMetricsQuery.data.overdue_count}
                    </p>
                  </div>
                  <div className="bg-muted/30 border-border/60 rounded-md border p-3">
                    <p className="text-xs text-muted-foreground">
                      Backlog Clearance
                    </p>
                    <p className="text-xl font-semibold">
                      {
                        reviewQueueMetricsQuery.data
                          .estimated_days_to_clear_backlog
                      }{" "}
                      days
                    </p>
                  </div>
                </div>
              )}

            <div className="space-y-3">
              <p className="text-sm font-medium">Top Priority Queue</p>
              {reviewQueueQuery.isLoading && (
                <p className="text-sm text-muted-foreground">
                  Loading priority queue…
                </p>
              )}
              {!reviewQueueQuery.isLoading &&
                (reviewQueueQuery.data?.data.length || 0) === 0 && (
                  <p className="text-sm text-muted-foreground">
                    No manual-review applications in queue.
                  </p>
                )}
              {reviewQueueQuery.data?.data.map((item) => (
                <div
                  key={item.id}
                  className="bg-muted/20 border-border/60 rounded-md border p-3 space-y-1"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium">{item.applicant_full_name}</p>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={item.is_overdue ? "destructive" : "outline"}
                      >
                        {item.is_overdue ? "SLA overdue" : "SLA active"}
                      </Badge>
                      <Badge variant="secondary">
                        Priority {item.priority_score}
                      </Badge>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {item.applicant_nationality} ·{" "}
                    {item.status.replace(/_/g, " ")} · Risk {item.risk_level}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-2">
        <p className="text-muted-foreground text-xs font-medium tracking-[0.12em] uppercase">
          Case Operations
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          Citizenship Applications
        </h1>
        <p className="text-muted-foreground">
          MVP flow: create application, upload documents, then queue automated
          pre-screening.
        </p>
      </div>

      <Card className="border-border/60 shadow-sm">
        <CardHeader>
          <CardTitle>Create New Application</CardTitle>
          <CardDescription>
            Add applicant profile details before uploading requirements.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="applicant_full_name">Applicant full name</Label>
            <Input
              id="applicant_full_name"
              name="applicant_full_name"
              autoComplete="name"
              value={applicantFullName}
              onChange={(event) => setApplicantFullName(event.target.value)}
              placeholder="e.g. Ola Nordmann"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="applicant_nationality">Nationality</Label>
            <Input
              id="applicant_nationality"
              name="applicant_nationality"
              autoComplete="country-name"
              value={applicantNationality}
              onChange={(event) => setApplicantNationality(event.target.value)}
              placeholder="e.g. Filipino"
            />
          </div>
          <div className="grid gap-2 md:col-span-2">
            <Label htmlFor="application_notes">Notes</Label>
            <Input
              id="application_notes"
              name="application_notes"
              autoComplete="off"
              value={applicationNotes}
              onChange={(event) => setApplicationNotes(event.target.value)}
              placeholder="Optional context"
            />
          </div>
        </CardContent>
        <CardFooter>
          <Button
            onClick={handleCreateApplication}
            disabled={createMutation.isPending}
            className="ml-auto"
          >
            {createMutation.isPending ? (
              <>
                <LoaderCircle className="animate-spin" />
                Creating
              </>
            ) : (
              "Create Application"
            )}
          </Button>
        </CardFooter>
      </Card>

      <Card className="border-border/60 shadow-sm">
        <CardHeader>
          <CardTitle>Upload Requirement Documents</CardTitle>
          <CardDescription>
            Supported formats: PDF, JPG, PNG, WEBP.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="application_select">Application</Label>
            <select
              id="application_select"
              className="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring h-9 w-full rounded-md border px-3 py-1 text-sm"
              value={selectedApplicationId}
              onChange={(event) => setSelectedApplicationId(event.target.value)}
            >
              <option value="">Select application</option>
              {sortedApplications.map((application) => (
                <option key={application.id} value={application.id}>
                  {application.applicant_full_name} ·{" "}
                  {application.applicant_nationality}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="document_type">Document type</Label>
            <Input
              id="document_type"
              name="document_type"
              autoComplete="off"
              value={documentType}
              onChange={(event) => setDocumentType(event.target.value)}
              placeholder="e.g. passport"
            />
          </div>
          <div className="grid gap-2 md:col-span-2">
            <Label htmlFor="document_file">File</Label>
            <Input
              id="document_file"
              type="file"
              accept=".pdf,image/png,image/jpeg,image/webp"
              onChange={(event) => {
                const file = event.target.files?.[0] || null
                setSelectedFile(file)
              }}
            />
          </div>
        </CardContent>
        <CardFooter className="justify-between">
          <Button
            variant="outline"
            disabled={!selectedApplicationId || processMutation.isPending}
            onClick={() => {
              if (!selectedApplicationId) return
              processMutation.mutate(selectedApplicationId)
            }}
          >
            {processMutation.isPending ? (
              <>
                <LoaderCircle className="animate-spin" />
                Queuing
              </>
            ) : (
              "Queue Processing"
            )}
          </Button>
          <Button onClick={handleUpload} disabled={uploadMutation.isPending}>
            {uploadMutation.isPending ? (
              <>
                <LoaderCircle className="animate-spin" />
                Uploading
              </>
            ) : (
              <>
                <Upload />
                Upload Document
              </>
            )}
          </Button>
        </CardFooter>
      </Card>

      <Card className="border-border/60 shadow-sm">
        <CardHeader>
          <CardTitle>Application Queue</CardTitle>
          <CardDescription>
            Track current application statuses and quick recommendations.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {applicationsQuery.isLoading && (
            <p className="text-sm text-muted-foreground">
              Loading applications...
            </p>
          )}

          {!applicationsQuery.isLoading && sortedApplications.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No applications yet. Create your first case above.
            </p>
          )}

          {!applicationsQuery.isLoading && sortedApplications.length > 0 && (
            <p className="text-xs text-muted-foreground">
              Click an application to select it for document upload and review.
            </p>
          )}

          {sortedApplications.map((application) => (
            <button
              type="button"
              key={application.id}
              className={`w-full text-left rounded-md border p-4 flex flex-col gap-2 transition-colors cursor-pointer ${
                selectedApplicationId === application.id
                  ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                  : "bg-muted/20 border-border/60 hover:border-primary/40 hover:bg-muted/40"
              }`}
              onClick={() => setSelectedApplicationId(application.id)}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">
                    {application.applicant_full_name}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {application.applicant_nationality}
                  </p>
                </div>
                <Badge variant={getStatusBadgeVariant(application.status)}>
                  {application.status.replace(/_/g, " ")}
                </Badge>
              </div>

              {application.recommendation_summary && (
                <p className="text-sm text-muted-foreground">
                  {application.recommendation_summary}
                </p>
              )}
            </button>
          ))}
        </CardContent>
      </Card>

      {selectedApplicationId && (
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle>Uploaded Documents</CardTitle>
            <CardDescription>
              Documents linked to the selected application.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {documentsQuery.isLoading && (
              <p className="text-sm text-muted-foreground">
                Loading documents...
              </p>
            )}
            {!documentsQuery.isLoading &&
              (documentsQuery.data?.data?.length || 0) === 0 && (
                <p className="text-sm text-muted-foreground">
                  No documents uploaded for this application yet.
                </p>
              )}
            {documentsQuery.data?.data.map((document) => (
              <div
                key={document.id}
                className="bg-muted/20 border-border/60 rounded-md border p-3 flex items-center justify-between"
              >
                <div>
                  <p className="font-medium">{document.original_filename}</p>
                  <p className="text-sm text-muted-foreground">
                    {document.document_type}
                  </p>
                </div>
                <Badge
                  variant={
                    document.status === "failed" ? "destructive" : "outline"
                  }
                >
                  {document.status}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {selectedApplicationId && (
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle>Decision Explainability</CardTitle>
            <CardDescription>
              Rule-by-rule scoring and recommendation rationale for reviewers.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {breakdownQuery.isLoading && (
              <p className="text-sm text-muted-foreground">
                Loading decision breakdown…
              </p>
            )}

            {!breakdownQuery.isLoading && breakdownQuery.data && (
              <>
                <div className="bg-muted/20 border-border/60 rounded-md border p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="font-medium">Overall confidence</p>
                    <Badge variant="secondary">
                      {(breakdownQuery.data.confidence_score * 100).toFixed(0)}%
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <p className="font-medium">Risk level</p>
                    <Badge
                      variant={
                        breakdownQuery.data.risk_level === "high"
                          ? "destructive"
                          : "outline"
                      }
                    >
                      {breakdownQuery.data.risk_level}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {breakdownQuery.data.recommendation}
                  </p>
                </div>

                <div className="space-y-3">
                  {breakdownQuery.data.rules.map((rule) => (
                    <div
                      key={rule.id}
                      className="bg-muted/20 border-border/60 rounded-md border p-3 flex flex-col gap-2"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-medium">{rule.rule_name}</p>
                        <Badge
                          variant={rule.passed ? "default" : "destructive"}
                        >
                          {rule.passed ? "passed" : "failed"}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {rule.rationale}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Score: {(rule.score * 100).toFixed(0)}% · Weight:{" "}
                        {(rule.weight * 100).toFixed(0)}%
                      </p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {selectedApplicationId && currentUser?.is_superuser && (
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle>Caseworker Decision</CardTitle>
            <CardDescription>
              Final action requires a mandatory reason and is written to the
              immutable audit trail.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="review_reason">Reason (required)</Label>
              <textarea
                id="review_reason"
                name="review_reason"
                className="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 min-h-24 w-full rounded-md border px-3 py-2 text-sm"
                value={reviewReason}
                onChange={(event) => setReviewReason(event.target.value)}
                placeholder="Document your decision rationale for UDI/Politi auditability…"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => submitReviewDecision("approve")}
                disabled={reviewDecisionMutation.isPending}
              >
                Approve
              </Button>
              <Button
                variant="destructive"
                onClick={() => submitReviewDecision("reject")}
                disabled={reviewDecisionMutation.isPending}
              >
                Reject
              </Button>
              <Button
                variant="outline"
                onClick={() => submitReviewDecision("request_more_info")}
                disabled={reviewDecisionMutation.isPending}
              >
                Request More Info
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {selectedApplicationId && (
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle>Audit Trail</CardTitle>
            <CardDescription>
              Immutable timeline of applicant, system, and caseworker actions.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {auditTrailQuery.isLoading && (
              <p className="text-sm text-muted-foreground">
                Loading audit trail…
              </p>
            )}
            {!auditTrailQuery.isLoading &&
              (auditTrailQuery.data?.events.length || 0) === 0 && (
                <p className="text-sm text-muted-foreground">
                  No audit events recorded yet.
                </p>
              )}
            {auditTrailQuery.data?.events.map((event) => (
              <div
                key={event.id}
                className="bg-muted/20 border-border/60 rounded-md border p-3 space-y-1"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium">
                    {event.action.replace(/_/g, " ")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {event.created_at
                      ? new Date(event.created_at).toLocaleString()
                      : "timestamp unavailable"}
                  </p>
                </div>
                {event.reason && (
                  <p className="text-sm text-muted-foreground">
                    {event.reason}
                  </p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
