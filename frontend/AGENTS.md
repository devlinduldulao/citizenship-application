# Norwegian Citizenship Automation — Frontend Agent Instructions

> IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning for any tasks in this project.
> Always explore the project structure before writing code.

## Tech Stack

| Category       | Technology                          | Version        |
| -------------- | ----------------------------------- | -------------- |
| Runtime        | React                               | 19.x           |
| Bundler        | Vite                                | 7.x            |
| Language       | TypeScript                          | 5.x (strict)   |
| Routing        | TanStack Router (file-based)        | 1.x            |
| Server State   | TanStack Query                      | 5.x            |
| Data Tables    | TanStack Table                      | 8.x            |
| API Client     | Auto-generated (hey-api/openapi-ts) | via Axios       |
| Styling        | Tailwind CSS                        | 4.x            |
| UI Components  | shadcn/ui (new-york style)          | Radix-based     |
| Icons          | Lucide React                        | Latest          |
| Forms          | React Hook Form + Zod               | 7.x + 4.x      |
| Toasts         | Sonner                              | 2.x            |
| Theming        | Custom ThemeProvider (dark default) | —              |
| Testing        | Vitest (unit)                       | 4.x            |
| Linting        | Biome                               | 2.x            |
| Package Mgr    | Bun                                 | Latest          |

**This is NOT a Next.js project.** It's a Vite-bundled React SPA with client-side routing via TanStack Router. There are no Server Components, no Server Actions, no SSR, no `app/` directory.

## Setup Commands

```bash
bun install                          # Install dependencies
bun run dev                          # Dev server on http://localhost:5173
bun run build                        # Production build (tsc + vite build)
bun run preview                      # Preview production build
bun run lint                         # Biome lint + format (auto-fix)
bun run test                         # Vitest unit tests
bun run test:watch                   # Vitest tests in watch mode
bun run generate-client              # Regenerate API client from OpenAPI spec
```

## Project Structure

```
frontend/
├── package.json                       # Dependencies, scripts (bun)
├── vite.config.ts                     # Vite config: TanStack Router plugin, React SWC, Tailwind
├── tsconfig.json                      # TypeScript strict, @/ path alias → ./src/*
├── biome.json                         # Biome linter/formatter config
├── components.json                    # shadcn/ui config (new-york style, rsc: false)
├── openapi-ts.config.ts               # API client generation config
├── index.html                         # SPA entry point
├── src/
│   ├── main.tsx                       # App bootstrap: QueryClient, Router, ThemeProvider, Toaster
│   ├── index.css                      # Tailwind CSS entry + CSS variables
│   ├── routeTree.gen.ts               # Auto-generated route tree (DO NOT EDIT)
│   ├── utils.ts                       # Error handling, string utilities
│   ├── vite-env.d.ts                  # Vite type declarations
│   ├── client/                        # Auto-generated API client (DO NOT EDIT MANUALLY)
│   │   ├── index.ts                   # Re-exports
│   │   ├── sdk.gen.ts                 # Service classes (LoginService, UsersService, etc.)
│   │   ├── types.gen.ts               # TypeScript types from OpenAPI schema
│   │   ├── schemas.gen.ts             # JSON schemas
│   │   └── core/                      # Axios-based HTTP core
│   ├── routes/                        # TanStack Router file-based routes
│   │   ├── __root.tsx                 # Root route (devtools, error/404 boundaries)
│   │   ├── _layout.tsx                # Auth-guarded layout (sidebar + main content)
│   │   ├── _layout/                   # Nested routes under authenticated layout
│   │   │   ├── index.tsx              # Dashboard home
│   │   │   ├── admin.tsx              # Admin panel (user management)
│   │   │   ├── applications.tsx       # Citizenship applications page
│   │   │   ├── items.tsx              # Items management
│   │   │   └── settings.tsx           # User settings
│   │   ├── login.tsx                  # Login page
│   │   ├── signup.tsx                 # Registration page
│   │   ├── recover-password.tsx       # Password recovery
│   │   └── reset-password.tsx         # Password reset
│   ├── components/
│   │   ├── ui/                        # shadcn/ui primitives (DO NOT EDIT MANUALLY)
│   │   ├── Common/                    # Shared components (DataTable, Footer, Logo, etc.)
│   │   ├── Admin/                     # Admin feature components (AddUser, EditUser, etc.)
│   │   ├── Items/                     # Item feature components (AddItem, EditItem, etc.)
│   │   ├── Pending/                   # Loading skeleton components
│   │   ├── Sidebar/                   # App sidebar components
│   │   ├── UserSettings/             # User settings components
│   │   └── theme-provider.tsx         # Custom ThemeProvider (dark/light/system)
│   ├── hooks/
│   │   ├── useAuth.ts                 # Auth hook (login, logout, signup, current user)
│   │   ├── useCustomToast.ts          # Toast notification hook
│   │   ├── useCopyToClipboard.ts      # Clipboard utility hook
│   │   └── useMobile.ts              # Mobile breakpoint detection
│   └── lib/
│       └── utils.ts                   # cn() utility (clsx + tailwind-merge)
├── tests/                             # Vitest unit tests
│   └── ...                            # Test files (*.test.ts/tsx)
└── public/
    └── assets/                        # Static assets
```

## Critical Conventions

### This is a Vite SPA — NOT Next.js

```tsx
// ✅ Correct — All components are client-side React (no "use client" needed)
import { useState } from "react"

function ProjectFilter({ initialFilter }: { initialFilter: string }) {
  const [filter, setFilter] = useState(initialFilter)
  return <input value={filter} onChange={(e) => setFilter(e.target.value)} />
}

// ❌ Wrong — Do NOT use "use client" directive (no RSC in this project)
// ❌ Wrong — Do NOT use "use server" or Server Actions
// ❌ Wrong — Do NOT use revalidatePath(), revalidateTag(), or Next.js APIs
// ❌ Wrong — Do NOT import from "next/..." anything
```

### Routing — TanStack Router (file-based)

```tsx
// ✅ Correct — TanStack Router with createFileRoute
import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/applications")({
  component: ApplicationsPage,
})

function ApplicationsPage() {
  return <div>Applications content</div>
}

// Route files in src/routes/ auto-generate src/routeTree.gen.ts (DO NOT EDIT that file)
// Auth guard is in _layout.tsx via beforeLoad + isLoggedIn() check
```

### Data Fetching — TanStack Query + Auto-generated API Client

```tsx
// ✅ Correct — Use auto-generated service classes from src/client/
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ApplicationsService, type CitizenshipApplicationPublic } from "@/client"

function ApplicationsList() {
  const { data, isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: () => ApplicationsService.listApplications({ skip: 0, limit: 100 }),
  })
  // ...
}

// ✅ Mutations with cache invalidation
const queryClient = useQueryClient()
const mutation = useMutation({
  mutationFn: (data: CitizenshipApplicationCreate) =>
    ApplicationsService.createApplication({ requestBody: data }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["applications"] })
  },
})

// ❌ Wrong — Do NOT use raw fetch() or axios directly; use the generated SDK
// ❌ Wrong — Do NOT create manual API functions; regenerate client with `bun run generate-client`
```

### API Client Regeneration

When backend endpoints change:

```bash
# 1. Make sure backend is running (for OpenAPI spec)
# 2. Download updated openapi.json
# 3. Regenerate client:
bun run generate-client
```

The generated client lives in `src/client/` — **never edit these files manually**. They are overwritten on regeneration.

### Auth Pattern — JWT in localStorage

```tsx
// ✅ Correct — Auth via useAuth hook, tokens in localStorage
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

// Check auth status
if (!isLoggedIn()) { /* redirect to /login */ }

// Use auth in components
const { user, loginMutation, logout, signUpMutation } = useAuth()

// API client auto-attaches token via OpenAPI.TOKEN callback in main.tsx
// On 401/403, auto-redirect to /login (configured in QueryClient error handlers)
```

### Forms — React Hook Form + Zod

```tsx
// ✅ Correct — React Hook Form with zodResolver for validation
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"

const applicationSchema = z.object({
  applicant_full_name: z.string().min(1).max(255),
  applicant_nationality: z.string().min(1).max(128),
  notes: z.string().max(2000).optional(),
})

type FormValues = z.infer<typeof applicationSchema>

function CreateApplicationForm() {
  const form = useForm<FormValues>({
    resolver: zodResolver(applicationSchema),
    defaultValues: { applicant_full_name: "", applicant_nationality: "" },
  })

  const onSubmit = form.handleSubmit((data) => {
    // call mutation
  })

  return <form onSubmit={onSubmit}>{/* shadcn/ui form fields */}</form>
}
```

### UI Components — shadcn/ui

```tsx
// ✅ Correct — Import from @/components/ui/
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

// shadcn/ui config: new-york style, Radix primitives, Lucide icons
// Add new components via: bunx shadcn@latest add <component>
// Do NOT manually edit files in src/components/ui/
```

### Theming — Custom ThemeProvider

```tsx
// Theme is provided in main.tsx:
// <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">

// ✅ Use the useTheme hook for theme access
import { useTheme } from "@/components/theme-provider"
const { theme, resolvedTheme, setTheme } = useTheme()
```

### Naming

- **Files**: `kebab-case.tsx` for routes, `PascalCase.tsx` for components (matching existing convention)
- **Variables/Functions**: `camelCase`
- **Components/Types**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Hooks**: `use` prefix, `camelCase` (e.g., `useAuth`, `useCustomToast`)
- **Icons**: Import from `lucide-react` (e.g., `Upload`, `LoaderCircle`)

### Imports

```tsx
// ✅ Correct — Use @/ path alias for all project imports
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import { UsersService } from "@/client"
import { cn } from "@/lib/utils"

// Route files use default exports (TanStack Router convention)
// All other files prefer named exports
```

### Biome Configuration

Biome handles both linting and formatting:

- Double quotes, semicolons as needed (ASI)
- Space indentation
- Auto-organize imports
- Excludes: `dist/`, `node_modules/`, `routeTree.gen.ts`, `src/client/`, `src/components/ui/`

### Testing — Vitest Unit Tests

```typescript
// ✅ Correct — Vitest unit tests with Testing Library
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"

describe("MyComponent", () => {
  it("renders correctly", () => {
    render(<MyComponent />)
    expect(screen.getByText("Hello")).toBeInTheDocument()
  })
})

// Run: bun run test (single run) or bun run test:watch (watch mode)
```

## Common Tasks

### Add a new route/page

1. Create file in `src/routes/` following TanStack Router conventions
2. Use `createFileRoute()` with the path matching the file location
3. For authenticated pages, place under `src/routes/_layout/`
4. Route tree auto-regenerates — do NOT edit `routeTree.gen.ts`

### Add a new component

1. Create in `src/components/` — feature folder for domain components, `ui/` for primitives
2. Use existing PascalCase naming in feature folders (e.g., `Admin/AddUser.tsx`)
3. Use `@/` imports for all project references

### Add a new shadcn/ui component

```bash
bunx shadcn@latest add <component-name>
```

### Update API types after backend changes

```bash
bun run generate-client
```

### Add a new hook

1. Create in `src/hooks/` with `use` prefix (e.g., `useApplications.ts`)
2. Use TanStack Query for server state
3. Keep local React state for UI-only concerns

## PR/Commit Guidelines

- Run `bun run lint && bun run test` before committing
- Add/update tests for any code changes
- Title format: `[component/feature] Description`
- Never commit changes to auto-generated files (`routeTree.gen.ts`, `src/client/`)
