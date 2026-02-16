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
import useCustomToast from "@/hooks/useCustomToast"

type ApplicationStatus =
  | "draft"
  | "documents_uploaded"
  | "queued"
  | "processing"
  | "review_ready"

type DocumentStatus = "uploaded" | "processing" | "processed" | "failed"

interface CitizenshipApplication {
  id: string
  applicant_full_name: string
  applicant_nationality: string
  notes?: string | null
  status: ApplicationStatus
  recommendation_summary?: string | null
  confidence_score?: number | null
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
    const body = await response.json().catch(() => ({ detail: "Request failed" }))
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
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [applicantFullName, setApplicantFullName] = useState("")
  const [applicantNationality, setApplicantNationality] = useState("")
  const [applicationNotes, setApplicationNotes] = useState("")
  const [selectedApplicationId, setSelectedApplicationId] = useState("")
  const [documentType, setDocumentType] = useState("")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const applicationsQuery = useQuery({
    queryKey: ["citizenship-applications"],
    queryFn: () =>
      fetchJson<CitizenshipApplicationList>("/api/v1/applications/?skip=0&limit=100"),
  })

  const documentsQuery = useQuery({
    queryKey: ["application-documents", selectedApplicationId],
    queryFn: () =>
      fetchJson<ApplicationDocumentList>(
        `/api/v1/applications/${selectedApplicationId}/documents`,
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
      queryClient.invalidateQueries({
        queryKey: ["application-documents", selectedApplicationId],
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
    },
    onError: (error: Error) => showErrorToast(error.message),
  })

  const sortedApplications = useMemo(() => {
    const rows = applicationsQuery.data?.data || []
    return [...rows].sort((left, right) => {
      const leftDate = left.created_at ? new Date(left.created_at).getTime() : 0
      const rightDate = right.created_at ? new Date(right.created_at).getTime() : 0
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

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Citizenship Applications
        </h1>
        <p className="text-muted-foreground">
          MVP flow: create application, upload documents, then queue automated
          pre-screening.
        </p>
      </div>

      <Card>
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
              value={applicantFullName}
              onChange={(event) => setApplicantFullName(event.target.value)}
              placeholder="e.g. Ola Nordmann"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="applicant_nationality">Nationality</Label>
            <Input
              id="applicant_nationality"
              value={applicantNationality}
              onChange={(event) => setApplicantNationality(event.target.value)}
              placeholder="e.g. Filipino"
            />
          </div>
          <div className="grid gap-2 md:col-span-2">
            <Label htmlFor="application_notes">Notes</Label>
            <Input
              id="application_notes"
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
              "Create application"
            )}
          </Button>
        </CardFooter>
      </Card>

      <Card>
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
                  {application.applicant_full_name} · {application.applicant_nationality}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="document_type">Document type</Label>
            <Input
              id="document_type"
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
              "Queue processing"
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
                Upload document
              </>
            )}
          </Button>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Application Queue</CardTitle>
          <CardDescription>
            Track current application statuses and quick recommendations.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {applicationsQuery.isLoading && (
            <p className="text-sm text-muted-foreground">Loading applications...</p>
          )}

          {!applicationsQuery.isLoading && sortedApplications.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No applications yet. Create your first case above.
            </p>
          )}

          {sortedApplications.map((application) => (
            <div
              key={application.id}
              className="border rounded-md p-4 flex flex-col gap-2"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">{application.applicant_full_name}</p>
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
            </div>
          ))}
        </CardContent>
      </Card>

      {selectedApplicationId && (
        <Card>
          <CardHeader>
            <CardTitle>Uploaded Documents</CardTitle>
            <CardDescription>
              Documents linked to the selected application.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {documentsQuery.isLoading && (
              <p className="text-sm text-muted-foreground">Loading documents...</p>
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
                className="border rounded-md p-3 flex items-center justify-between"
              >
                <div>
                  <p className="font-medium">{document.original_filename}</p>
                  <p className="text-sm text-muted-foreground">
                    {document.document_type}
                  </p>
                </div>
                <Badge variant={document.status === "failed" ? "destructive" : "outline"}>
                  {document.status}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
