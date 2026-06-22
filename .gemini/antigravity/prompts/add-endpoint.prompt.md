---
mode: plan
description: Add a new API endpoint: route → controller → service → validation → tests
---

# Add API Endpoint Workflow

## Phase 1: Design
1. Define: method, path, request body/params, response shape, error codes
2. Check for existing similar endpoints to follow patterns
3. Consider: authentication, authorization, rate limiting, idempotency

## Phase 2: Validation
1. Define input schema (type, required fields, constraints)
2. Add validation middleware or inline checks
3. Handle: missing fields, wrong types, out-of-range values

## Phase 3: Implementation
1. Add route registration
2. Create controller/handler function
3. Add service/business logic layer
4. Add data access if needed (parameterized queries only)

## Phase 4: Error Handling
1. Define error responses for each failure mode
2. Never leak internal state in error messages
3. Log errors appropriately (no PII, no secrets)

## Phase 5: Tests
1. Happy path: valid request returns expected response
2. Validation errors: invalid input returns 400
3. Auth errors: unauthenticated returns 401
4. Not found: missing resource returns 404
5. Edge cases: empty body, boundary values, concurrent requests
