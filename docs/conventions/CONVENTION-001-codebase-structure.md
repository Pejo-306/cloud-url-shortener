# CONVENTION-001: Codebase Conventions for `cloudshortener`

## Status

Accepted (Retroactively documented)

## Date

2025-12-21

## Context

I want to write simple and maintainable Python code. That's why I've documented my most important conventions here.

## Flat Codebase Structure

Let's accept the root of this repository is the directory `/`.

Inside the root directory, each folder is a **seperate component of the system**, e.g.:
- `/backend/`: Backend application code, including the codebase for 2 Lambdas
- `/backend/tests/`: Unit and integration tests for the backend
- `/frontend/`: Web application frontend code
- `/.github/`: GitHub Actions workflows
- `/infra/bootstrap/`: Bootstrapping scripts
- ...

Inside each **system component**, we have **modules**, e.g.:
- `/backend/cloudshortener/dao/`: Data Access Objects for our backend code
- `/backend/cloudshortener/lambdas/`: AWS Lambda Functions' code
- `/backend/cloudshortener/utils/`: Backed utility functions
- `/backend/cloudshortener/models/`: Backed data models

We may also have **submodules** inside each **module** which are just specific
implementations of the **module** for a concrete **system component** / **technology**, etc.:
- `/backend/cloudshortener/dao/base/`: Abstract Base Classes (Interfaces) for DAOs
- `/backend/cloudshortener/dao/redis/`: Redis-specific implementation of base DAOs
- `/backend/cloudshortener/dao/cache/`: Elasticache-specific DAOs
- `/backend/cloudshortener/dao/dynamodb/`: DynamoDB-specific implementation of base DAOs
- `/backend/cloudshortener/dao/postgresql/`: PostgreSQL-specific implementation of base DAOs

You may notice that under this logical codebase structure, code spaghettification
is naturally minimized:
- `/backend/cloudshortener/utils/` is always going to be imported by other modules / submodules
- `/backend/cloudshortener/models/` is always going to be imported by other modules / submodules
- `/backend/cloudshortener/dao/` there's no reason to mix up specific-datastore implementations
  and cause circular imports; we already have the base interfaces defined in `backend/cloudshortener/dao/base/`
- `/backend/cloudshortener/lambdas/` is going to import everything. And no other module in
  `/backend/cloudshortener/` is going to import the lambdas (makes no sense)

Inside each Python module / submodule, a few common modules & files are expected:
- `constants.py`: all hardcoded constants
- `exceptions.py`: all module-specific exceptions
- `helpers.py`: all module-specific helper functions (for internal implementation)
- `mixins.py`: all module-specific mixin classes (for internal implementation)
- `base/`: all abstract base classes / protocols go here

And then each seperate file defines a seperate class / data model / collection of
related functions (related to a specific system component).

Make sense? This is simple and easy to navigate.

## Pythonic Code is King

Stop overabusing classes!

Python =/= Java without semicolon

Don't define a class `Config` with a bunch of static methods to handle configuration
files. Instead, define a file `config.py` with a set of regular functions.

Use decorators.

Imo prefer functional-style programming (use `map`, `filter`, `list/dict comprehensions`
`lambda functions`, method chaining) over OOP.

And don't define every single possible function parameter as an `Enum`. It's so ugly!

[Click here for a great video on Pythonic code](https://www.youtube.com/watch?v=bsU7AFjh4m8)

## Functions >>> Classes

I have to repeat this explicitly.

Functions are waaaaaaaaay better than classes for most cases.

And functional programming is so much more beautiful.

Stop abusing OOP for *everything*.
