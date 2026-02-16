# Next.js + React 19 Demo — Agent Instructions

> IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning for any tasks in this project.

## Tech Stack

| Category       | Technology                   | Version   |
| -------------- | ---------------------------- | --------- |
| Meta-framework | Next.js                      | 15.x      |
| React          | React                        | 19.2      |
| Language       | TypeScript                   | 5.x       |
| Compiler       | React Compiler               | 1.0       |
| Rendering      | React Server Components      | Built-in  |
| Data Mutations | Server Actions               | Built-in  |
| Client State   | Zustand                      | 5.x       |
| Server State   | TanStack Query (client only) | 5.x       |
| Styling        | Tailwind CSS                 | 4.x       |
| UI             | shadcn/ui                    | Latest    |
| Forms          | React Hook Form + Zod        | 7.x + 4.x |
| Auth           | Auth.js (NextAuth)           | 5.x       |
| ORM            | Drizzle ORM                  | Latest    |
| Database       | PostgreSQL                   | 16.x      |
| Testing        | Vitest + Testing Library     | Latest    |
| Build          | Turbopack                    | Built-in  |

## Setup Commands

```bash
npm install              # Install dependencies
npm run dev              # Start dev server with Turbopack (port 3000)
npm run build            # Production build
npm run start            # Start production server
npm run test             # Run all tests
npm run test -- --run    # Run tests once (no watch)
npx tsc --noEmit         # TypeScript check
npm run lint             # Next.js lint (ESLint)
npm run db:generate      # Generate Drizzle migrations
npm run db:migrate       # Run Drizzle migrations
npm run db:studio        # Open Drizzle Studio
```

## Project Structure

```
app/
├── layout.tsx               # Root layout (Server Component)
├── page.tsx                 # Home page (Server Component)
├── loading.tsx              # Root loading UI
├── error.tsx                # Root error boundary
├── not-found.tsx            # 404 page
├── (auth)/                  # Auth route group (no layout nesting)
│   ├── login/page.tsx
│   └── register/page.tsx
├── (dashboard)/             # Dashboard route group
│   ├── layout.tsx           # Dashboard layout with sidebar
│   ├── page.tsx             # Dashboard home
│   └── projects/
│       ├── page.tsx         # Projects list (Server Component)
│       ├── loading.tsx      # Projects loading skeleton
│       ├── [projectId]/
│       │   ├── page.tsx     # Project detail (Server Component)
│       │   └── edit/
│       │       └── page.tsx # Project edit (Client Component form)
│       └── new/
│           └── page.tsx     # New project form
├── api/                     # API routes (Route Handlers)
│   └── [...slug]/route.ts   # Catch-all API route
components/
├── ui/                      # shadcn/ui primitives
├── forms/                   # Form components with validation
├── data-tables/             # Server-rendered data tables
└── layout/                  # Layout components (sidebar, nav)
lib/
├── db/                      # Drizzle schema + queries
│   ├── schema.ts            # Drizzle table definitions
│   ├── queries.ts           # Type-safe query functions
│   └── index.ts             # Database connection
├── actions/                 # Server Actions
│   ├── project-actions.ts   # Project CRUD actions
│   └── auth-actions.ts      # Auth-related actions
├── utils.ts                 # Shared utilities
└── validations/             # Zod schemas (shared client/server)
    └── project.ts           # Project validation schemas
hooks/                       # Client-side custom hooks
state/                       # Zustand stores (client state only)
```

## Critical Conventions

### Server vs. Client Components

```tsx
// ✅ Default — Server Components (no directive needed)
// These run on the server, can access DB directly, and send zero JS to client
async function ProjectsPage() {
  const projects = await db.query.projects.findMany();
  return <ProjectList projects={projects} />;
}

// ✅ Client Component — only when needed for interactivity
("use client");

import { useState } from "react";

function ProjectFilter({ initialFilter }: { initialFilter: string }) {
  const [filter, setFilter] = useState(initialFilter);
  return <input value={filter} onChange={(e) => setFilter(e.target.value)} />;
}

// ❌ Wrong — Don't add "use client" unless you need browser APIs or hooks
// "use client"  ← unnecessary, this component has no interactivity
function ProjectCard({ project }: { project: Project }) {
  return <div>{project.name}</div>;
}
```

**Why?** Server Components are the default in Next.js App Router. They send zero JavaScript to the browser, can access databases directly, and reduce bundle size. Only add `"use client"` when you need `useState`, `useEffect`, event handlers, or browser APIs. The boundary should be as deep in the tree as possible — wrap only the interactive leaf, not the entire page.

### Naming

- **Files**: `kebab-case.tsx` (e.g., `project-card.tsx`, `use-filter.ts`)
- **Variables/Functions**: `camelCase` (NEVER `snake_case`)
- **Components/Types**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Server Actions**: `camelCase` verbs (e.g., `createProject`, `deleteProject`)
- **Zod schemas**: `camelCase` suffixed with `Schema` (e.g., `projectSchema`)
- **Icons**: Import with `Icon` suffix (e.g., `PlusIcon`, `TrashIcon`)

### Imports

```typescript
// ✅ Correct — Path alias for project root
import { Button } from "@/components/ui/button";
import { db } from "@/lib/db";
import { projectSchema } from "@/lib/validations/project";

// ✅ Correct — Server Action import
import { createProject } from "@/lib/actions/project-actions";

// ✅ Correct — shadcn/ui components
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

// ❌ Wrong — Default exports
export default function MyComponent() {}

// ✅ Correct — Named exports only (except page.tsx, layout.tsx, loading.tsx)
// Next.js route files MUST use default export — this is the ONLY exception
export default async function ProjectsPage() {
  // ...
}
```

### Data Fetching Pattern — Server Components

```tsx
// ✅ Correct — Fetch data directly in Server Components
// app/(dashboard)/projects/page.tsx
import { db } from "@/lib/db";
import { projects } from "@/lib/db/schema";
import { ProjectList } from "@/components/data-tables/project-list";

export default async function ProjectsPage() {
  const allProjects = await db.select().from(projects).orderBy(projects.createdAt);
  return <ProjectList projects={allProjects} />;
}

// ❌ Wrong — Don't useEffect + fetch in Server Components
// ❌ Wrong — Don't use TanStack Query in Server Components
// TanStack Query is for CLIENT components that need polling, optimistic updates, or caching
```

### Data Fetching Pattern — Client Components (when needed)

```tsx
// ✅ TanStack Query — Only for client-side data that needs reactivity
"use client";

import { useQuery } from "@tanstack/react-query";

function NotificationBell() {
  const { data: count } = useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: () => fetch("/api/notifications/count").then((r) => r.json()),
    refetchInterval: 30_000, // Poll every 30s — this is why we need Query
  });

  return <span>{count ?? 0}</span>;
}
```

### Server Actions Pattern

```tsx
// lib/actions/project-actions.ts
"use server";

import { revalidatePath } from "next/cache";
import { db } from "@/lib/db";
import { projects } from "@/lib/db/schema";
import { projectSchema } from "@/lib/validations/project";

export async function createProject(formData: FormData) {
  const parsed = projectSchema.safeParse(Object.fromEntries(formData));

  if (!parsed.success) {
    return { error: parsed.error.flatten().fieldErrors };
  }

  await db.insert(projects).values(parsed.data);
  revalidatePath("/dashboard/projects");
  return { success: true };
}

export async function deleteProject(projectId: string) {
  await db.delete(projects).where(eq(projects.id, projectId));
  revalidatePath("/dashboard/projects");
}
```

### Form Pattern — Client Component with Server Action

```tsx
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useTransition } from "react";
import { createProject } from "@/lib/actions/project-actions";
import { projectSchema } from "@/lib/validations/project";

type FormValues = z.infer<typeof projectSchema>;

function CreateProjectForm() {
  const [isPending, startTransition] = useTransition();

  const form = useForm<FormValues>({
    resolver: zodResolver(projectSchema),
    defaultValues: { name: "", description: "" },
  });

  const onSubmit = form.handleSubmit((data) => {
    startTransition(async () => {
      const result = await createProject(new FormData(/* ... */));
      if (result.error) {
        // Handle server validation errors
      }
    });
  });

  return (
    <form onSubmit={onSubmit}>
      {/* shadcn/ui FormField components */}
      <button type="submit" disabled={isPending}>
        {isPending ? "Creating..." : "Create Project"}
      </button>
    </form>
  );
}
```

### State Management Pattern

```typescript
// ✅ Zustand — Client UI state ONLY (sidebar, theme, modals)
import { create } from "zustand";

interface SidebarStore {
  isOpen: boolean;
  toggle: () => void;
  close: () => void;
}

export const useSidebarStore = create<SidebarStore>((set) => ({
  isOpen: true,
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  close: () => set({ isOpen: false }),
}));

// ❌ Wrong — Don't put server data in Zustand
// Server data lives in Server Components (fetched directly) or TanStack Query (client polling)
```

### React Compiler — What Changes

```tsx
// React Compiler 1.0 is enabled — it auto-memoizes components and hooks

// ❌ No longer needed — Compiler handles memoization
const MemoizedComponent = React.memo(MyComponent);
const memoizedValue = useMemo(() => expensiveCalc(a, b), [a, b]);
const memoizedCallback = useCallback(() => doSomething(id), [id]);

// ✅ Just write plain React — Compiler optimizes automatically
function MyComponent({ items }: { items: Item[] }) {
  const filtered = items.filter((item) => item.active);
  const handleClick = () => doSomething();
  return <ItemList items={filtered} onClick={handleClick} />;
}

// ⚠️ Rules still apply — Compiler validates Rules of React
// - Don't mutate props or state directly
// - Don't call hooks conditionally
// - Don't read/write refs during render
```

### Testing Pattern

```typescript
import { describe, it, expect, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@testing-library/react";

// Server Components — test the rendered output
describe("ProjectCard", () => {
  it("should render project name", () => {
    render(<ProjectCard project={{ id: "1", name: "My Project" }} />);
    expect(screen.getByText("My Project")).toBeInTheDocument();
  });
});

// Client Components — test interactivity
describe("ProjectFilter", () => {
  it("should filter on input", async () => {
    const user = userEvent.setup();
    render(<ProjectFilter initialFilter="" />);

    await user.type(screen.getByRole("textbox"), "react");
    expect(screen.getByRole("textbox")).toHaveValue("react");
  });
});

// Server Actions — test like regular async functions
describe("createProject", () => {
  it("should validate input", async () => {
    const formData = new FormData();
    formData.set("name", ""); // Invalid — name required

    const result = await createProject(formData);
    expect(result.error).toBeDefined();
  });
});
```

## Common Tasks

### Add a new page

1. Create file in `app/` following Next.js file conventions
2. Default to Server Component — fetch data directly with `async/await`
3. Add `loading.tsx` sibling for Suspense fallback
4. Add `error.tsx` sibling for error boundary
5. Only add `"use client"` to interactive sub-components

### Add a new Server Action

1. Create in `lib/actions/` with `"use server"` directive
2. Validate input with Zod schema from `lib/validations/`
3. Call `revalidatePath()` or `revalidateTag()` after mutations
4. Return typed result `{ success: true }` or `{ error: ... }`

### Add a new component

1. Create in `components/` with `kebab-case.tsx` naming
2. Server Component by default — no directive needed
3. Add `"use client"` only for interactivity
4. Add `.test.tsx` file alongside

## PR/Commit Guidelines

- Run `npm run lint && npm run test` before committing
- Add/update tests for any code changes
- Use descriptive commit messages
- Title format: `[component/feature] Description`
