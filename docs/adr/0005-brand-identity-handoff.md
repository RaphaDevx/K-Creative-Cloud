# ADR 0005 — Portable brand identity and social-media handoff

## Status
Accepted

## Context
Natural-language style briefs need usable colors, typography, guidelines and handoff files, rather than an untracked chat response. Existing brand/tokens and the social-media skill already have contracts.

## Decision
Store a versioned identity under native project.brand, retain name/accent compatibility, and validate semantic color roles, CSS-safe type stacks, layout, voice and assumptions at the shared API boundary. The assistant emits brand.update; local Y2K/colorful/minimal presets provide draft foundations without a model.

Export to workspace/brand-projects/<project-id>/revision-<revision>-<digest> with brand/identity.json, tokens.json (primitive/semantic/component), styles.css, BRAND.md, palette.svg, preview.html, social-media/brand.json and project.json. Exports never replace existing files. Other tools can edit exported identity.json and import it with revision protection/undo. Social briefs follow the social-media skill template and remain drafts-only; account/publication authority is never inferred from file contents.

## Consequences
Font stacks contain system fallbacks; no external fonts silently installed. Preset style is a draft direction, not a finished identity or legal clearance. Existing Piggy brand source is unaffected. No target app or account is changed by export.
