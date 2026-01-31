# Component: `frontend` - The Frontend

## Responsibility

Provides a stylistic web UI for end users.

This component orchestrates the flow of interaction with the backend `cloudshortener`
app to provide the user with a simple and intuitive user interface. The user can
shorten links, view analytics, and enjoy a buttery-smooth experience.

## Functional Requirements

### FR-1: User Authentication
- User can sign up for an account
- User can log in/out of their account
- User can reset their password if forgotten

### FR-2: Trigger URL Shortening
- User can input a long URL and trigger a URL shortening
- They receive a shortened link back

### FR-3: View Analytics [ OPTIONAL | FUTURE ]
- User can freely view the system analytics

## Non-functional Requirements

### NFR-1: Performance
- Frontend itself must be *blazingly* fast
- Performance bottleneck should always be the backend

### NFR-2: Engagement
- Users should be engaged at all times, even while waiting for a response from the backend

## Constraints

### C-1: Using `Vue.js`
- We have decided in [ADR-015](/docs/decisions/ADR-015-frontend.md) to use `Vue.js`
to implement our frontend application

### C-2: Authentication flow with `Amazon Cognito`
- The backend is using `Amazon Cognito` to authenticate and authorize users to
shorten links via the shortening URL

### C-3: Static Deployment
- Application must be deployable as static HTML / CSS / JS

## Assumptions

### A-1: `cloudshortener` is implemented
- The backend is implemented and working as documented in its [Component document](/docs/components/cloudshortener.md)
and [High level system's design](/docs/architecture.md)

## Routing

- `/`: Home view including URL shortening interface and analytics
- `/login`: modal to log in to your existing account
- `/logout`: log out a user and redirect to `/`
- `/register`: modal to sign up as a new user
- `/confirm-registration`: modal to confirm user registration with code
- `/resend-confirmation-code`: modal to resend registration confirmation code
- `/password-reset`: modal to initiate password reset
- `/confirm-password-reset`: modal to confirm password reset with code

## UX flows

### First-time User

![UX for First-Time User](../assets/png/ux/first-time-user.png)

1. User requests `/`
2. Frontend application intercepts request and redirects to `/login`
3. User has no account and signs up via `/register`
4. Frontend application communicates with `Amazon Cognito` to create a new user
5. On successful sign up, user is redirected back to homepage @ `/`
6. User inputs a short URL and requests shortening
7. Frontend application validates user's input
8. On valid input, frontend application sends a request to shorten user's URL
9. User is engaged with a cool / funny loading screen while awaiting the backend's response
10. Frontend awaits backend's response and displays new short link to user
11. Repeat **6.-11.** indefinitely

### Unauthenticated user

![UX for Unauthenticated User](../assets/png/ux/unauthenticated-user.png)

1. User requests `/`
2. Frontend application intercepts request and redirects to `/login`
3. Frontend application communicates with `Amazon Cognito` to sign in an existing user
4. On successful sign in, user is redirected back to homepage @ `/`
5. User inputs a short URL and requests shortening
6. Frontend application validates user's input
7. On valid input, frontend application sends a request to shorten user's URL
8. User is engaged with a cool / funny loading screen while awaiting the backend's response
9. Frontend awaits backend's response and displays new short link to user
10. Repeat **5.-10.** indefinitely

### Authenticated user

![UX for Authenticated User](../assets/png/ux/authenticated-user.png)

1. User requests `/` and views the homepage
2. User inputs a short URL and requests shortening
3. Frontend application validates user's input
4. On valid input, frontend application sends a request to shorten user's URL
5. User is engaged with a cool / funny loading screen while awaiting the backend's response
6. Frontend awaits backend's response and displays new short link to user
7. Repeat **2.-7.** indefinitely

## High-level Designs

![Frontend Design](../assets/png/frontend-design.png)

Components:
- `views/Home.vue`
- `components/auth/LoginForm.vue`
- `components/auth/RegistrationForm.vue`
- `components/auth/ConfirmRegistrationForm.vue`
- `components/auth/ResendConfirmationCodeForm.vue`
- `components/auth/PasswordResetForm.vue`
- `components/auth/ConfirmPasswordResetForm.vue`
- `components/Modal.vue`
- `components/LoadingScreen.vue`
- `components/Shortener.vue`
- `components/analytics/Dashboard.vue`
- `components/analytics/PieChart.vue`
- `components/analytics/BulletList.vue`

## Deep Dives

### 1. Single-page website vs multi-page? 

Do we create a website with one page and display everything on it or make a multi-page website?

#### 1.1. Single-page website

Have the entire user interface on one page (shortener interface + analytics 
dashboard + user authentication).

**Pros:**
- Simple
- More intuitive for user (just scroll down/up to get everything)

**Cons:**
- n/a

**Accepted** due to simplicity

#### 1.2. Multi-page website

**Pros:**
- Possibly more SEO visibility?? (we don't care about that)

**Cons:**
- Complicates frontend application needlessly

**Rejected** because it adds needless complexity with no benefit.

### 2. How do we integrate `AWS Cognito` with our `Vue` app?

Several options are available depending on how much management we'd like to offload
to AWS.

#### 2.1. Redirect back & forth with `Cognito's` hosted UI

**Pros:**
- Fastest and simplest to integrate

**Cons:**
- Slow (we redirect out of our view app)
- Hard to customize stylistically

**Rejected** because it will hamper our buttery smooth user experience.

#### 2.2. Orchestrate `AWS Cognito's` barebones API ourselves

**Pros:**
- Granular control
- Won't need to rely on Cognito's hosted UI

**Cons:**
- AWS learning curve to bridge
- Leads to cumbersome code

**Rejected** due to being cumbersome.

#### 2.3. Use `AWS Amplify Authenticator` component for `Vue`

**Pros:**
- Handles Cognito API flow for us
- Built to plug into Vue

**Cons:**
- Introduces dependency
- Dependent on AWS release cycle
- Small learning curve

**Rejected** due to adding another big dependency for a small part

#### 2.4. Use `amazon-cognito-identity-js` package

**Pros:**
- Minimal
- Small learning curve (just Amazon Cognito's API)
- Great for minimal & simple auth flows (like ours)

**Cons:**
- Have to manually interact with Amazon Cognito 

**Accepted** as it's easiest to integrate into our flow.

### 3. How do we engage the user while awaiting fetch responses?

Add a loading modal to each fetch request with a message, dancing figure,
success checkmark, close button.

Dancing figure is different every time.

Success checkmark only triggers after fetch succeeds.

Close button only activates after fetch request completes.
