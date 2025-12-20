# Architecture Documentation

This directory contains the architecture and design documentation for the `cloudshortener`
system.

The goal of these documents is to explain **why the system is built the way it is**,
not to duplicate code-level details.

**NOTE:** since this project started out as a 3-week MVP sprint with minimal system design,
many of the decisions have been retroactively documented. I.e. it's already implemented 
in code.

## How to read these docs

If you are new to the system, read in this order:

1. **requirements.md**
   Defines functional and non functional constraints to the system.

2. **architecture.md**
   Describes the high-level system components and their responsibilities.

3. **decisions/**
   Contains Architectural Decision Records (ADRs) documenting important design decisions.

## What belongs here (and what does not)

### Included
- High-level system structure
- Design constraints and assumptions
- Major architectural decisions and trade-offs
- Failure considerations and operational intent (at a high level)
- Codebase maintainability conventions

### Explicitly excluded
- Code walkthroughs
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
- The **consequences** of the decision

ADRs are (supposed to be...) written at the time the decision is made. Some of the
starting ADRs are documented retroactively.

## Conventions

- Documents favor clarity and intent over exhaustiveness
- Diagrams, if present, are illustrative, not authorative
- This documentation evolves with the system and may reflect trade-offs that are no longer optimal

## Audience

These documents are intended for:
- Myself, learning about what software architects document and take into consideration
- People who've taken an interest in this repository and have somehow stumbled here

They assume familiarity with backend systems but not with this specific codebase.
