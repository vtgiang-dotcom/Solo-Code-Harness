---
mode: ask
description: Add a new REST API endpoint with Pydantic models, service layer, router, and frontend integration following layered architecture
triggers: add endpoint, create API, new route, REST endpoint
---

# Add API Endpoint

Create a new REST API endpoint following clean architecture patterns.

## Variables

- `RESOURCE_NAME`: The resource name (singular, e.g., `annotation`)
- `RESOURCE_PLURAL`: Plural form (e.g., `annotations`)
- `RESOURCE_DESCRIPTION`: Brief description of the resource
- `RESOURCE_FIELDS`: Key fields for the resource

## Steps

### 1. Define Pydantic Models

Create `src/backend/app/models/{RESOURCE_NAME}.py`:

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class {{RESOURCE_NAME|title}}Base(BaseModel):
    """Base model with common fields."""
    # Add {RESOURCE_FIELDS}

    class Config:
        populate_by_name = True

class {{RESOURCE_NAME|title}}Create({{RESOURCE_NAME|title}}Base):
    """Request model for creation."""
    # Add required creation fields
    pass

class {{RESOURCE_NAME|title}}Update(BaseModel):
    """Request model for partial updates (all fields optional)."""
    # Add optional update fields
    pass

class {{RESOURCE_NAME|title}}({{RESOURCE_NAME|title}}Base):
    """Response model."""
    id: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    class Config:
        from_attributes = True
        populate_by_name = True

class {{RESOURCE_NAME|title}}InDB({{RESOURCE_NAME|title}}):
    """Database document model."""
    doc_type: str = "{RESOURCE_NAME}"
```

### 2. Create Service Layer

Create `src/backend/app/services/{RESOURCE_NAME}_service.py`:

```python
from typing import Optional
from app.models.{RESOURCE_NAME} import {{RESOURCE_NAME|title}}, {{RESOURCE_NAME|title}}Create, {{RESOURCE_NAME|title}}Update

class {{RESOURCE_NAME|title}}Service:
    async def get_by_id(self, id: str) -> Optional[{{RESOURCE_NAME|title}}]:
        """Get {RESOURCE_NAME} by ID."""
        # Implement

    async def create(self, data: {{RESOURCE_NAME|title}}Create, user_id: str) -> {{RESOURCE_NAME|title}}:
        """Create new {RESOURCE_NAME}."""
        # Implement

    async def update(self, id: str, data: {{RESOURCE_NAME|title}}Update) -> {{RESOURCE_NAME|title}}:
        """Update {RESOURCE_NAME}."""
        # Implement

    async def delete(self, id: str) -> None:
        """Delete {RESOURCE_NAME}."""
        # Implement
```

### 3. Create Router

Create `src/backend/app/routers/{RESOURCE_PLURAL}.py`:

```python
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import get_current_user, get_current_user_required
from app.models.user import User
from app.models.{RESOURCE_NAME} import {{RESOURCE_NAME|title}}, {{RESOURCE_NAME|title}}Create, {{RESOURCE_NAME|title}}Update
from app.services.{RESOURCE_NAME}_service import {{RESOURCE_NAME|title}}Service

router = APIRouter(prefix="/api", tags=["{RESOURCE_PLURAL}"])

@router.get("/{RESOURCE_PLURAL}/{{id}}", response_model={{RESOURCE_NAME|title}})
async def get_{RESOURCE_NAME}(id: str, current_user: Optional[User] = Depends(get_current_user)):
    service = {{RESOURCE_NAME|title}}Service()
    result = await service.get_by_id(id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result

@router.post("/{RESOURCE_PLURAL}", status_code=status.HTTP_201_CREATED)
async def create_{RESOURCE_NAME}(data: {{RESOURCE_NAME|title}}Create, current_user: User = Depends(get_current_user_required)):
    return await {{RESOURCE_NAME|title}}Service().create(data, current_user.id)

@router.patch("/{RESOURCE_PLURAL}/{{id}}")
async def update_{RESOURCE_NAME}(id: str, data: {{RESOURCE_NAME|title}}Update, current_user: User = Depends(get_current_user_required)):
    return await {{RESOURCE_NAME|title}}Service().update(id, data)

@router.delete("/{RESOURCE_PLURAL}/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{RESOURCE_NAME}(id: str, current_user: User = Depends(get_current_user_required)):
    await {{RESOURCE_NAME|title}}Service().delete(id)
```

### 4. Mount Router

In `src/backend/app/main.py`:

```python
from app.routers.{RESOURCE_PLURAL} import router as {RESOURCE_PLURAL}_router
app.include_router({RESOURCE_PLURAL}_router)
```

### 5. Add Frontend Types

In `src/frontend/src/types/index.ts`:

```typescript
export interface {{RESOURCE_NAME|title}} {
  id: string;
  createdAt: string;
  updatedAt?: string;
}

export interface {{RESOURCE_NAME|title}}Create {
  // Add creation fields
}

export interface {{RESOURCE_NAME|title}}Update {
  // Add optional update fields
}
```

### 6. Add API Client Functions

In `src/frontend/src/services/api.ts`:

```typescript
export async function get{{RESOURCE_NAME|title}}(id: string): Promise<{{RESOURCE_NAME|title}}> {
  return authFetch(`/api/{RESOURCE_PLURAL}/${id}`);
}

export async function create{{RESOURCE_NAME|title}}(data: {{RESOURCE_NAME|title}}Create): Promise<{{RESOURCE_NAME|title}}> {
  return authFetch('/api/{RESOURCE_PLURAL}', { method: 'POST', body: JSON.stringify(data) });
}

export async function update{{RESOURCE_NAME|title}}(id: string, data: {{RESOURCE_NAME|title}}Update): Promise<{{RESOURCE_NAME|title}}> {
  return authFetch(`/api/{RESOURCE_PLURAL}/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
}

export async function delete{{RESOURCE_NAME|title}}(id: string): Promise<void> {
  return authFetch(`/api/{RESOURCE_PLURAL}/${id}`, { method: 'DELETE' });
}
```

## Checklist

- [ ] Pydantic models (Base, Create, Update, Response, InDB)
- [ ] Service with proper async/await
- [ ] Router with auth dependencies
- [ ] Router mounted in main.py
- [ ] Frontend types
- [ ] API client functions
- [ ] Tests added for all endpoints
