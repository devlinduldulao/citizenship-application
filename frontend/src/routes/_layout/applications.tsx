import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { LoaderCircle, Upload } from "lucide-react"
import { useMemo, useState } from "react"

import {
  type ApplicationStatus,
  ApplicationsService,
  type CitizenshipApplicationCreate,
  type ReviewDecisionAction,
} from "@/client"
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

type ReviewAction = ReviewDecisionAction

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
    queryFn: () => ApplicationsService.readReviewQueue({ skip: 0, limit: 5 }),
    enabled: Boolean(currentUser?.is_superuser),
  })

  const reviewQueueMetricsQuery = useQuery({
    queryKey: ["review-queue-metrics"],
    queryFn: () => ApplicationsService.readReviewQueueMetrics({}),
    enabled: Boolean(currentUser?.is_superuser),
  })

  const applicationsQuery = useQuery({
    queryKey: ["citizenship-applications"],
    queryFn: () =>
      ApplicationsService.readApplications({ skip: 0, limit: 100 }),
  })

  const documentsQuery = useQuery({
    queryKey: ["application-documents", selectedApplicationId],
    queryFn: () =>
      ApplicationsService.readApplicationDocuments({
        applicationId: selectedApplicationId,
      }),
    enabled: Boolean(selectedApplicationId),
  })

  const breakdownQuery = useQuery({
    queryKey: ["application-breakdown", selectedApplicationId],
    queryFn: () =>
      ApplicationsService.readApplicationDecisionBreakdown({
        applicationId: selectedApplicationId,
      }),
    enabled: Boolean(selectedApplicationId),
  })

  const auditTrailQuery = useQuery({
    queryKey: ["application-audit-trail", selectedApplicationId],
    queryFn: () =>
      ApplicationsService.readApplicationAuditTrail({
        applicationId: selectedApplicationId,
      }),
    enabled: Boolean(selectedApplicationId),
  })

  const caseExplainerQuery = useQuery({
    queryKey: ["application-case-explainer", selectedApplicationId],
    queryFn: () =>
      ApplicationsService.readApplicationCaseExplainer({
        applicationId: selectedApplicationId,
      }),
    enabled: Boolean(selectedApplicationId),
  })

  const evidenceRecommendationsQuery = useQuery({
    queryKey: ["application-evidence-recommendations", selectedApplicationId],
    queryFn: () =>
      ApplicationsService.readApplicationEvidenceRecommendations({
        applicationId: selectedApplicationId,
      }),
    enabled: Boolean(selectedApplicationId),
  })

  const createMutation = useMutation({
    mutationFn: (requestBody: CitizenshipApplicationCreate) =>
      ApplicationsService.createApplication({ requestBody }),
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
    mutationFn: (payload: {
      applicationId: string
      documentType: string
      file: File
    }) =>
      ApplicationsService.uploadApplicationDocument({
        applicationId: payload.applicationId,
        formData: {
          document_type: payload.documentType,
          file: payload.file,
        },
      }),
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
    mutationFn: (applicationId: string) =>
      ApplicationsService.queueApplicationProcessing({
        applicationId,
        requestBody: { force_reprocess: false },
      }),
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
      ApplicationsService.submitReviewDecision({
        applicationId: payload.applicationId,
        requestBody: {
          action: payload.action,
          reason: payload.reason,
        },
      }),
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
              className={`w-full text-left rounded-md border p-4 flex flex-col gap-2 transition-colors cursor-pointer ${selectedApplicationId === application.id
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
            <CardTitle>AI Evidence Recommendations</CardTitle>
            <CardDescription>
              Targeted document and action suggestions to improve decision
              confidence.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {evidenceRecommendationsQuery.isLoading && (
              <p className="text-sm text-muted-foreground">
                Generating evidence recommendations...
              </p>
            )}

            {!evidenceRecommendationsQuery.isLoading &&
              evidenceRecommendationsQuery.data && (
                <>
                  <div className="bg-muted/20 border-border/60 rounded-md border p-4 space-y-3">
                    <p className="text-sm font-medium">
                      Recommended document types
                    </p>
                    {evidenceRecommendationsQuery.data
                      .recommended_document_types.length === 0 && (
                        <p className="text-sm text-muted-foreground">
                          No additional high-impact document types suggested at
                          this stage.
                        </p>
                      )}
                    <div className="flex flex-wrap gap-2">
                      {evidenceRecommendationsQuery.data.recommended_document_types.map(
                        (documentType) => (
                          <Badge key={documentType} variant="secondary">
                            {documentType}
                          </Badge>
                        ),
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Generated by{" "}
                      {evidenceRecommendationsQuery.data.generated_by}
                    </p>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="bg-muted/20 border-border/60 rounded-md border p-3 space-y-2">
                      <p className="text-sm font-medium">Document rationale</p>
                      {Object.entries(
                        evidenceRecommendationsQuery.data
                          .rationale_by_document_type,
                      ).map(([documentType, rationale]) => (
                        <p
                          key={documentType}
                          className="text-sm text-muted-foreground"
                        >
                          <span className="font-medium text-foreground">
                            {documentType}:
                          </span>
                          {rationale}
                        </p>
                      ))}
                    </div>

                    <div className="bg-muted/20 border-border/60 rounded-md border p-3 space-y-2">
                      <p className="text-sm font-medium">
                        Recommended next actions
                      </p>
                      {evidenceRecommendationsQuery.data.recommended_next_actions.map(
                        (action) => (
                          <p
                            key={action}
                            className="text-sm text-muted-foreground"
                          >
                            • {action}
                          </p>
                        ),
                      )}
                    </div>
                  </div>
                </>
              )}
          </CardContent>
        </Card>
      )}

      {selectedApplicationId && (
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle>AI Case Explainer</CardTitle>
            <CardDescription>
              Decision memo draft generated from rules, documents, and audit
              context.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {caseExplainerQuery.isLoading && (
              <p className="text-sm text-muted-foreground">
                Generating explanation...
              </p>
            )}

            {!caseExplainerQuery.isLoading && caseExplainerQuery.data && (
              <>
                <div className="bg-muted/20 border-border/60 rounded-md border p-4 space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">Recommended action</p>
                    <Badge variant="secondary">
                      {caseExplainerQuery.data.recommended_action.replace(
                        /_/g,
                        " ",
                      )}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {caseExplainerQuery.data.summary}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Generated by {caseExplainerQuery.data.generated_by}
                  </p>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <div className="bg-muted/20 border-border/60 rounded-md border p-3 space-y-2">
                    <p className="text-sm font-medium">Key risks</p>
                    {caseExplainerQuery.data.key_risks.map((risk) => (
                      <p key={risk} className="text-sm text-muted-foreground">
                        • {risk}
                      </p>
                    ))}
                  </div>
                  <div className="bg-muted/20 border-border/60 rounded-md border p-3 space-y-2">
                    <p className="text-sm font-medium">Missing evidence</p>
                    {caseExplainerQuery.data.missing_evidence.map((gap) => (
                      <p key={gap} className="text-sm text-muted-foreground">
                        • {gap}
                      </p>
                    ))}
                  </div>
                  <div className="bg-muted/20 border-border/60 rounded-md border p-3 space-y-2">
                    <p className="text-sm font-medium">Next steps</p>
                    {caseExplainerQuery.data.next_steps.map((step) => (
                      <p key={step} className="text-sm text-muted-foreground">
                        • {step}
                      </p>
                    ))}
                  </div>
                </div>
              </>
            )}
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
