# Architecture Documentation

This directory contains the architecture and design documentation for the `cloudshortener`
system.

The goal of these documents is to explain **why the system is built the way it is**,
not to duplicate code-level details.

**NOTE:** since this project started out as a 3-week MVP sprint with minimal system design,
many of the decisions have been retroactively documented. I.e. it's already implemented 
in code.

**NOTE:** This documentation evolves with the system and may reflect trade-offs that are no longer optimal

## How to read these docs

If you are new to the system, read in this order:

1. **[system-design.md](/docs/system-design.md)**
   Original design narrative: capacity estimates, API shape, Redis key schema, diagram, and deep dives (shortcodes, quotas, retention).

2. **[requirements.md](/docs/requirements.md)**
   Defines functional and non functional requrements and constraints to the system.

3. **[architecture.md](/docs/architecture.md)**
   Describes the high-level system components and their responsibilities.

4. **[decisions/](/docs/decisions/)**
   Contains Architectural Decision Records (ADRs) documenting important design decisions.

## What belongs here (and what does not)

### Included
- High-level system structure
- Design constraints and assumptions
- Major architectural decisions and trade-offs
- Failure considerations and operational intent

### Explicitly excluded
- Code walkthroughs / conventions
- Line-by-line logic explanations
- Configuration values
- Environment-specific instructions

Those belong in the codebase or deployment tooling.

## Architectural Decisions Records (ADR)

All significant architectural decisions are documented as **ADR files** under
[docs/decisions/](docs/decisions/)

Each ADR captures:
- The **context** in which the decision was made
- The **decision** itself
- The **alternatives** that were considered
- The **implications** of the decision

ADRs are (supposed to be...) written at the time the decision is made. Some of the
starting ADRs are documented retroactively.
