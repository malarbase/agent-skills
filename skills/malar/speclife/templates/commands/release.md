---
name: /speclife-release
id: speclife-release
category: SpecLife
description: Create a release with version bump (typically for major versions).
---
**Guardrails**
- Execute immediately—must be on main with clean working directory
- Use for major releases or when auto-release was skipped
- For patch/minor, prefer `/speclife land` which handles auto-release

**Steps**
1. Check branch: must be on `main`; error otherwise.
2. Analyze commits since last tag: `feat:` → minor, `fix:` → patch, `BREAKING CHANGE` or `!` → major; use explicit flag (--major/--minor/--patch) if provided.
3. Calculate new version from current `package.json`.
4. Update version: `npm version <bump> --no-git-tag-version` (and workspaces if monorepo).
5. Update CHANGELOG.md with grouped commits.
6. Commit: `git commit -am "chore(release): v<version>"`.
7. Push: `git push origin main`.
8. Report: version bumped, pushed, GitHub Actions will create tag and release.

**Reference**
- Commit message format `chore(release): vX.X.X` triggers release workflow
- Major releases should use this command; patch/minor typically via `/speclife land`
