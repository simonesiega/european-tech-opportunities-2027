# Personal context router

Keep personal notes and their index local. This README defines the shared structure; it contains no developer-specific entries.

1. Create `.context/ROUTER.md` using the template below.
2. Add one row per note, with recognizable topics and a path relative to `ROUTER.md`. For notes outside this folder, use a local relative or absolute path.
3. Update the router when notes move or their scope changes. Never put personal entries in this README.

```markdown
# Context router

| Topic / keywords | When to read | Local path |
|---|---|---|
| Example decision | When changing the related subsystem | notes/example.md |
```

Agents consult the router only when prior decisions or notes may matter, then read the smallest matching set. Missing routers are normal in fresh forks; fall back to relevant filenames. Missing targets should be reported, not fetched or guessed. Routing does not override `AGENTS.md`, current repository evidence, or security rules.

Only `README.md` and `.gitkeep` are eligible for tracking here. `ROUTER.md` and all personal notes remain Git-ignored; never force-add them. Ignoring files does not encrypt them or remove previously tracked files from history. Do not store secrets in notes. No shared workflow or validation may require a developer's router or targets.
