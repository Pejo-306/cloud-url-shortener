# ADR-015: Frontend application `Cloudshortener Studio (CS)`

## Status

Accepted

## Date

2025-12-27

## Context

We would like to add a frontend application to our `cloudshortener` system and
name it `Cloudshortener Studio (CS)`.

Herein, "the user" refers to an external customer, not an internal user.

`CS` is responsible for providing the user with an intuitive, seamless and simple
interface. The user inputs his long URL and receives a shortened URL in exchange.
They are also aware of their quotas, the links they have created and link analytics.

In order to use `CS` the user enters our website domain (TBD) in their browser and
sign up / log in to their user account. After logging in, they have full access
to the UI.

`CS` is served as static HTML/CSS/JS over the internet. Its primary responsibility
is interacting with the `cloudshortener` system's public and protected endpoints
and handling HTTP responses. It has no direct access to the backend system.

Relevant documents:
- System provides an interface to convert long URL to short URL ([FR-1](/docs/requirements.md#fr-1-url-shortening))
- Only authenticated users can access UI ([FR-3](/docs/requirements.md#fr-3-authentication))
- Display near real-time analytics ([FR-6](/docs/requirements.md#fr-6-analytics-optional--future))
- Seamless UI experience ([NFR-1](/docs/requirements.md#nfr-1-performance) and 
[NFR-2](/docs/requirements.md#nfr-2-scalability))
- One developer with no frontend experience 
([C-2](/docs/requirements.md#c-2-time-constraints) and 
[C-3](/docs/requirements.md#c-3-team-size))

## Responsibilities

**Responsibilities**:
- Provide the user with an intuitive URL shortening interface
- Provide the user with an analytics interface
- Store and attach access tokens for protected endpoints
- Handle HTTP responses from `cloudshortener` backend system
- Be environment-aware (know which AWS endpoints to call)
- Stateless (no caching)
- Static (served as static HTML/CSS/JS via S3 & CloudFront distribution)
- Validate user input

**Non-responsibilities**:
- URL redirection (handled by browser)
- User authentication (handled by Amazon Cognito [ADR-010](/docs/decisions/ADR-010-authentication-model.md))
- Caching responses (it would mess with our analytics)
- Any business logic (URL shortening, quota management, etc.)

## Criteria for Success

Successful resolution of this ADR would be: accessing our web domain (TBD) presents
`Cloudshortener Studio` with the user having the ability to:
- Sign up and log in
- Input a long URL and get a short URL
- View near real-time analytics
- Get descriptive event and error messages

## Constraints and Concerns

**Simplicity**
- Application is servable as plain HTML/CSS/JS
- Avoids need for runtime servers, backend-for-frontend layers, etc.

**Deployment independence**
- Frontend can be deployed and rolled back independent of the backend
- Per-environment application version separation

**Learning-friendly**
- Avoids locking in an unpopular framework with high learning curve

**Configuration**
- Simple runtime configuration in JSON/YAML file
- Per-environment config separation

**Per-environment versioning**

Split the deployed app and configuration per frontend in a central frontend bucket like so:
- local: `s3://<s3-bucket-domain>/cloudshortener/local/`
- dev: `s3://<s3-bucket-domain>/cloudshortener/dev/`
- staging: `s3://<s3-bucket-domain>/cloudshortener/staging/`
- prod: `s3://<s3-bucket-domain>/cloudshortener/prod/`

**Integration with Cognito**

We already have a fully functioning Cognito hosted UI. Instead of reimplementing
authentication flows, we should use and customize Cognito's built-in UI.

## Decision

Use `Vue.js` as the frontend framework due to its simplicity, market leadership position,
static delivery, and easier learning curve (compared to `React.js`).

Full tech stack: `Vue 3 + TypeScript + Vite`

We use `Vite` for 2 purposes:
- As a local dev server for building the application. It handles TypeScript compilation
and hot reloading.
- As a TypeScript compiler so we can ship static HTML/CSS/JS to S3 frontend bucket.

Application configuration is stored per-environment in a JSON/YAML file. It is
separate from backend configuration (AWS AppConfig). The Vue.js app is expected
to load its configuration file at runtime.

AWS S3 + CloudFront are responsible for serving and distributing the UI to end users.

The frontend application is present in [frontend/](/frontend/) directory.

The frontend application is dependent on the following backend APIs at minimum:
- `POST /v1/shorten`: protected shortening endpoint
- `GET /v1/analytics`: (TBD) public/protected analytics endpoint

Amazon Cognito's OAuth flow is used to authenticate the user.

During deployment, the respective environment folder is overwritten in-place with
the new frontend application. No versioning is implemented inside the S3 bucket.

## Alternatives Considered

### 1. Plain HTML/CSS/JS frontend

**Pros**
- No framework lock-in
- 0 learning curve
- Fully static by definition
- Smallest surface area

**Cons**
- Spending my time building HTML/CSS/JS (not learning anything new)
- Not best practice in the software industry
- Hard and painful to maintain
- Tedious to customize
- No built-in guardrails or security
- Scaling UI increases cognitive load over time

**Rejected** due to high cognitive load and no learning experience

### 2. No-code tools

Tools like Wordpress, hosted UI builders, etc.

**Pros**
- Easy to pick up
- Fast to prototype

**Cons**
- Vendor lock-in
- Not versatile or versionable like code
- Hard to integrate cleanly with Cognito + API gateway

**Rejected** due to no versatility

### 3. Next.js, Nuxt.js, Remix

**Pros**
- New technology = new learning
- Based on React.js or Vue.js

**Cons**
- Includes a backend server
- Overkill for a simple static, API-only frontend
- Framework's use case doesn't fit our use case

**Rejected** because it's overkill for the purposes of our frontend app.

### 4. Full React.js ecosystem

The “classic” React stack (React, React Router, Redux/Zustand/etc).

**Pros**
- New technology = new learning
- Based on React.js or Vue.js

**Cons**
- Not fit for a simplistic UI like ours
- High mental overhead
- Easy to overbuild
- Hard to maintain solo

**Rejected** due to being unfit for our simplistic UI app.

### 5. Svelte

**Pros**
- Minimalistic
- Small runtime complexity
- Small bundles and small footprint
- Very fast iteration
- Built for small apps

**Cons**
- Not industry standard

**Rejected** due to not being industry standard like React.js or Vue.js.

### 6. React.js

Vanilla React.js.

**Pros**
- Industry leader

**Cons**
- Steeper learning curve for a new frontend developer
- Application needs are too small to take advantage of React's features

**Rejected** due to learning curve complexity in favor of Vue.js.

## Consequences

### Positive
- I get to learn frontend development
- Frontend is decoupled from backend
- Frontend and backend are separately versioned
- Easy to start and easy to learn

### Negative
- Miss out on learning industry-leading React.js

.
.
.

`Cloudshortener Studio` is documented extensively in [components/frontend.md](/docs/components/frontend.md).
