# Documentation & Agent Output Requirements

## 1. Agent Document Outputs

The agent shall produce the following document types. Each document type shall follow a
consistent template (sections, headings, tables) to ensure uniform outputs across projects.

### 1.1 Architecture Overview

- **Purpose:** Describe the system's purpose, context, key components, and main data/control
  flows.
- **Style:** C4-style context diagrams as the default notation.

### 1.2 Design Specification

- **Scope:** Module responsibilities, interfaces, data models, error-handling strategies, and
  non-functional constraints.

### 1.3 Deployment & Operational Runbook

- **Scope:** Environments, infrastructure topology, CI/CD steps, configuration, scaling
  strategy, observability, and SLOs.

### 1.4 Product / Requirements Document (PRD/SRS Hybrid)

- **Scope:** User goals, functional requirements, quality attributes, acceptance criteria, and
  dependencies.

---

## 2. Input Requirements for the Agent

The agent shall only produce high-quality documentation when supplied with the following
structured inputs.

### 2.1 Problem Statement & Constraints

- 2.1.1 Business goals and target users.
- 2.1.2 Success metrics.
- 2.1.3 Regulatory or infrastructure limits.

### 2.2 Architectural Drivers

- 2.2.1 Prioritized functional requirements.
- 2.2.2 Quality-attribute scenarios.
- 2.2.3 Concerns and constraints in structured form (e.g., separate markdown or tables).

### 2.3 Existing System Context

- 2.3.1 Repository snapshot and high-level description.
- 2.3.2 Any "blessed" patterns or reference architectures the agent shall reuse.

### 2.4 Guardrails & Style

- 2.4.1 Naming conventions.
- 2.4.2 Diagram notation (C4 / UML).
- 2.4.3 Document voice and tone.
- 2.4.4 Decision rules categorized as **Always / Ask First / Never** (e.g., "never store PII",
  "ask before choosing a DB").

### 2.5 Codebase Grounding

- 2.5.1 For large systems, the agent shall work against an indexed codebase / document store
  rather than raw, ad-hoc pastes, so descriptions and diagrams are grounded in reality.

---

## 3. Generation & Review Practices

The documentation workflow shall be explicitly multi-step, not "one-shot big spec."

### 3.1 Plan-First Mode

- 3.1.1 The agent shall outline sections, open questions, and assumptions before writing full
  prose.

### 3.2 Iterative Refinement

- 3.2.1 Start with coarse documents (context + containers).
- 3.2.2 Iterate into components, interfaces, and deployment details.
- 3.2.3 Update earlier diagrams as the design evolves.

### 3.3 Human Checkpoints

- 3.3.1 After each phase (drivers, architecture, detailed design, deployment), a human must
  approve or comment.
- 3.3.2 Feed diffs and comments back so the agent revises rather than rewriting from scratch.

### 3.4 Self-Checks

- 3.4.1 The agent shall include a **Validation / Open Issues** section listing assumptions,
  risks, and items to confirm.
- 3.4.2 The agent shall perform a consistency check against the original requirements.

### 3.5 Separation of Concerns

- 3.5.1 Use separate runs/agents for code vs. documentation (e.g., one agent generates the
  spec, another implements against it) to keep the design stable and auditable.

---

## 4. Content Standards

Each document shall meet the following content standards to ensure quality and downstream
usability.

### 4.1 Traceability

- 4.1.1 Map requirements to architectural drivers to design decisions.
- 4.1.2 Maintain traceability in small tables the agent keeps up to date.

### 4.2 Explicit Decisions

- 4.2.1 Capture key trade-offs ("chose X over Y because...") instead of only describing the
  final design.

### 4.3 Non-Functional Details

- 4.3.1 Performance budgets.
- 4.3.2 Reliability targets.
- 4.3.3 Security boundaries.
- 4.3.4 Observability requirements.
- 4.3.5 How the design meets each of the above.

### 4.4 LLM / Agent Specifics

- 4.4.1 Model names and versions.
- 4.4.2 Prompting strategy.
- 4.4.3 Tools used.
- 4.4.4 Safety policies.
- 4.4.5 Configuration parameters.
- 4.4.6 Follow LLM system-engineering guidelines.

### 4.5 Diagrams

- 4.5.1 For C4, sequence, and deployment diagrams, the agent shall generate text-based specs
  (PlantUML, Mermaid) under a **Diagrams** section.
- 4.5.2 Diagrams must be versionable and reviewable.

---

## 5. Deployment & Lifecycle Practices

Documentation shall be treated as living artifacts maintained by agents, not one-off exports.

### 5.1 Repo-Stored Documentation

- 5.1.1 Store generated documents in the repository.
- 5.1.2 Wire an agent into CI to flag drift between code and documentation (e.g., changed
  endpoints, config keys, queues).

### 5.2 Orchestrated Updates

- 5.2.1 Use orchestration (e.g., LangGraph or equivalent) so one agent updates architecture
  documents when another introduces significant structural changes.

### 5.3 Cache & Reuse

- 5.3.1 The system shall retrieve relevant sections of past documents as context when
  generating new ones.
- 5.3.2 Maintain consistent terminology and patterns across documents.

### 5.4 Governance

- 5.4.1 Define who signs off on architecture and deployment documents.
- 5.4.2 Require sign-off before certain CI stages (e.g., infrastructure changes) can proceed.
