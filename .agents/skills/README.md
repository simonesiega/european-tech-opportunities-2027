# Personal skills router

Keep personal skills and their index local. This README defines the shared structure; it contains no developer-specific entries.

1. Create `.agents/skills/ROUTER.md` using the template below.
2. Add one row per skill with its name, matching tasks, and entry-point path relative to `ROUTER.md`. Prefer `<skill-name>/SKILL.md`; external personal skills may use local relative or absolute paths.
3. Update the router when skills move or their scope changes. Never put personal entries in this README.

```markdown
# Skills router

| Skill / keywords | When to use | Entry point |
|---|---|---|
| Example procedure | When performing the related task | example/SKILL.md |
```

Agents check the router when a skill is named or clearly applicable, read the matching entry point before acting, and follow references only as needed. Missing routers are normal in fresh forks; fall back to relevant `<skill-name>/SKILL.md` entries. Missing targets should be reported, not fetched, installed, or guessed. Skills never override `AGENTS.md`, safety boundaries, or explicit user instructions.

Only `README.md` and `.gitkeep` are eligible for tracking here. `ROUTER.md` and all personal skills remain Git-ignored; never force-add them. Ignoring files does not encrypt them or remove previously tracked files from history. Do not store secrets in skills. No shared workflow or validation may require a developer's router or targets.
