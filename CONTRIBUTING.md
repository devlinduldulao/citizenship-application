# Contributing

Thanks for contributing to Norwegian Citizenship Automation MVP.

## Before you start

- Read [README.md](README.md) for project context.
- Read [development.md](development.md) for setup.
- For larger changes (new features, architecture changes), open a Discussion or Issue first to align scope.

## Development workflow

1. Fork and clone the repository.
2. Create a branch with a focused name, for example:
	- `feat/reviewer-queue-metrics`
	- `fix/login-token-validation`
	- `docs/oss-readme-cleanup`
3. Implement your changes.
4. Run checks locally.
5. Open a pull request.

## Local checks

### Backend

```bash
cd backend
uv run ruff check .
uv run pytest
```

### Frontend

```bash
cd frontend
bun run check:api-client
bun run lint
bun run test
bun run build
```

## Pull request expectations

- Keep PRs focused and small enough to review.
- Add/update tests for behavior changes.
- Update docs when UX, APIs, or commands change.
- Link related issues and explain the why, not just the what.
- Use clear commit messages and PR descriptions.

## Code style

- Follow project conventions in `AGENTS.md`, `backend/AGENTS.md`, and `frontend/AGENTS.md`.
- Prefer generated frontend API client usage (`src/client/`) over manual HTTP calls.
- Avoid unrelated refactors in the same PR.

## Using AI tools

AI-assisted contributions are welcome, but submissions must include meaningful human review and ownership.

Please ensure:

- You understand every change submitted.
- Generated content is verified against project behavior and tests.
- PR descriptions are written clearly in your own words.

## Reporting issues

- Use GitHub Issues for bugs and actionable tasks.
- Use GitHub Discussions for open-ended questions.
- For vulnerabilities, follow [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the terms of the [MIT License](LICENSE).
