# Norwegian Citizenship Automation MVP - Frontend

The frontend is the reviewer operations dashboard for the citizenship manual-review triage system. It gives UDI/Politi review teams a structured interface to process the backlog of flagged applications that can't be auto-decided by existing systems.

Built with [Vite](https://vitejs.dev/), [React](https://reactjs.org/), [TypeScript](https://www.typescriptlang.org/), [TanStack Query](https://tanstack.com/query), [TanStack Router](https://tanstack.com/router) and [Tailwind CSS](https://tailwindcss.com/).

## Frontend responsibilities

- Applicant case creation and requirement upload workflow
- Processing queue visibility with status tracking
- Explainable AI/rule insights (confidence, risk, per-rule rationale)
- Caseworker final decision actions with mandatory reason
- Audit trail timeline for accountability and traceability
- Reviewer workload dashboard with queue and SLA metrics

## AI-assisted reviewer workflow

The Applications route includes AI-assisted support components:

- **AI Case Explainer** — concise case memo from rules/documents/audit context.
- **AI Evidence Recommendations** — targeted missing-document suggestions and next actions.

These AI outputs are advisory and are always paired with human decision controls.

## Reviewer Ops Playbook

On the `Applications` page, use this sequence for daily review operations:

1. Check queue metric cards and prioritize overdue workload first.
2. Open top-priority pending-manual applications from the review queue.
3. Verify decision breakdown and uploaded evidence.
4. Complete `approve`, `reject`, or `request_more_info` with mandatory reason.
5. Confirm timeline/audit entries for handoff and supervision.

## Requirements

- [Bun](https://bun.sh/) (recommended) or [Node.js](https://nodejs.org/)

## Quick Start

```bash
bun install
bun run dev
```

* Then open your browser at http://localhost:5173/.

For demo usage, the login form is prefilled by default with:

- Email: `admin@example.com`
- Password: `changethis`

After login, the main MVP workflow is on the `Applications` page.

Notice that this live server is not running inside Docker, it's for local development, and that is the recommended workflow. Once you are happy with your frontend, you can build the frontend Docker image and start it, to test it in a production-like environment. But building the image at every change will not be as productive as running the local development server with live reload.

Check the file `package.json` to see other available options.

## Generate Client

### Automatically

* Activate the backend virtual environment.
* From the top level project directory, run the script:

```bash
bash ./scripts/generate-client.sh
```

* Commit the changes.

### Manually

* Start the Docker Compose stack.

* Download the OpenAPI JSON file from `http://localhost/api/v1/openapi.json` and copy it to a new file `openapi.json` at the root of the `frontend` directory.

* To generate the frontend client, run:

```bash
bun run generate-client
```

* Commit the changes.

Notice that everytime the backend changes (changing the OpenAPI schema), you should follow these steps again to update the frontend client.

## API Call Guard (Generated Client Only)

To prevent drift from the OpenAPI contract, frontend source code under `src/` is guarded against:

* direct `fetch(...)` calls
* direct `axios(...)` calls
* hardcoded `"/api/v1/..."` paths

The guard runs automatically as part of `bun run lint` via:

```bash
bun run check:api-client
```

Only generated client files in `src/client/` are allowed to contain direct HTTP implementation details.

## Quality gates

Run these checks before committing frontend changes:

```bash
bun run check:api-client
bun run lint
bun run test
bun run build
```

From monorepo root, you can run:

```bash
bun run verify:api-contract
```

## Code Structure

The frontend code is structured as follows:

* `frontend/src` - The main frontend code.
* `frontend/src/assets` - Static assets.
* `frontend/src/client` - The generated OpenAPI client.
* `frontend/src/components` -  The different components of the frontend.
* `frontend/src/hooks` - Custom hooks.
* `frontend/src/routes` - The different routes of the frontend which include the pages.

For the citizenship MVP flow, the main screen is:

* `frontend/src/routes/_layout/applications.tsx` - application intake, decision breakdown, caseworker actions, and audit timeline.

## End-to-End Testing with Playwright

The frontend includes initial end-to-end tests using Playwright. To run the tests, you need to have the Docker Compose stack running. Start the stack with the following command:

```bash
docker compose up -d --wait backend
```

Then, you can run the tests with the following command:

```bash
bunx playwright test
```

You can also run your tests in UI mode to see the browser and interact with it running:

```bash
bunx playwright test --ui
```

To stop and remove the Docker Compose stack and clean the data created in tests, use the following command:

```bash
docker compose down -v
```

To update the tests, navigate to the tests directory and modify the existing test files or add new ones as needed.

For more information on writing and running Playwright tests, refer to the official [Playwright documentation](https://playwright.dev/docs/intro).

## Related Documentation

- [Root README](../README.md)
- [Backend README](../backend/README.md)
- [Roadmap](../ROADMAP.md)
- [Immigrant User Guide](../IMMIGRANT_USER_GUIDE.md)
- [Reviewer Admin Guide](../REVIEWER_ADMIN_GUIDE.md)
