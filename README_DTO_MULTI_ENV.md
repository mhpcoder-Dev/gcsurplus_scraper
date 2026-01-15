# DTO and Multi-Environment Configuration Guide

## Overview
This document explains the major backend refactoring that implements:
1. **DTOs (Data Transfer Objects)** using Pydantic schemas
2. **Multi-environment configuration** (.env.common, .env.development, .env.production)

## Changes Made

### 1. DTO Implementation

#### Created New Directory: `schemas/`
- `schemas/__init__.py` - Exports all DTO models
- `schemas/auction.py` - Auction DTOs
- `schemas/comment.py` - Comment DTOs

#### Auction DTOs

**AuctionBase** (for list views):
- Minimal fields for performance
- Includes nested `location` and `bidding` objects
- Only sends first image URL instead of all images
- Used by endpoints that return multiple auctions

**AuctionDetailResponse** (for single item view):
- Complete auction details
- Full image array
- All contact information
- Extra data parsed from JSON
- Used by `/api/auctions/{lot_number}` endpoint

**AuctionLocation**:
```python
{
    "country": "USA",
    "city": "Washington",
    "region": "DC",
    "postal_code": "20001",
    "address_raw": "123 Main St"
}
```

**AuctionBidding**:
```python
{
    "current_bid": 1000.00,
    "minimum_bid": 500.00,
    "bid_increment": 50.00,
    "next_minimum_bid": 1050.00,
    "currency": "USD"
}
```

**AuctionListResponse**:
```python
{
    "items": [AuctionBase, ...],
    "pagination": {
        "total": 100,
        "skip": 0,
        "limit": 20,
        "page": 1,
        "total_pages": 5
    },
    "filters": {
        "status": "active",
        "source": "gsa",
        "asset_type": "vehicles"
    }
}
```

#### Comment DTOs

**CommentCreate** (request):
- Validates text (1-1000 chars)
- Validates auctionId (required)
- Sanitizes author (max 100 chars)

**CommentResponse**:
- Uses Field aliases for camelCase conversion
- `auction_id` → `auctionId`
- `created_at` → `createdAt`

### 2. Multi-Environment Configuration

#### Environment Files Structure

**.env.common**
- Shared settings across all environments
- Scraping URLs
- Connection pool settings
- API endpoints
- Non-sensitive defaults

**.env.development**
- `ENVIRONMENT=development`
- `DEBUG=true`
- SQLite database for local development
- `LOG_LEVEL=DEBUG`
- localhost frontend URL
- Development API keys

**.env.production**
- `ENVIRONMENT=production`
- `DEBUG=false`
- PostgreSQL (Neon) database
- `LOG_LEVEL=INFO`
- Production frontend URL
- Secure API keys (set in hosting environment)

#### How It Works

**Loading Priority** (highest to lowest):
1. Environment variables (set in hosting platform)
2. `.env.{environment}` (e.g., `.env.production`)
3. `.env.common`
4. Default values in `config.py`

**Setting Environment**:
```bash
# Development (default)
export ENVIRONMENT=development
python main.py

# Production
export ENVIRONMENT=production
python main.py
```

**Hosting Platforms**:
- Railway/Render: Set `ENVIRONMENT=production` in environment variables
- The app will automatically load `.env.common` + `.env.production`

### 3. Service Layer Updates

**auction_service.py** now has:
- `_model_to_base_dto()` - Converts DB model to AuctionBase
- `_model_to_detail_dto()` - Converts DB model to AuctionDetailResponse
- `get_auctions()` returns `AuctionListResponse` (DTO)
- `get_auction_by_lot_number()` returns `AuctionDetailResponse` (DTO)
- Legacy `_transform_to_api_format()` kept for backward compatibility

### 4. API Endpoint Updates

All auction endpoints now return structured DTOs:

```python
@app.get("/api/auctions", response_model=AuctionListResponse)
async def get_all_auctions(...)

@app.get("/api/auctions/{lot_number}", response_model=AuctionDetailResponse)
async def get_auction(...)
```

## Benefits

### DTOs
✅ **Type Safety**: Pydantic validates response structure
✅ **Performance**: Only send required fields (smaller payload)
✅ **Documentation**: FastAPI auto-generates correct OpenAPI schema
✅ **Maintainability**: Clear contract between backend and frontend
✅ **Flexibility**: Easy to add/remove fields without breaking changes

### Multi-Environment
✅ **Clean Separation**: Development vs Production settings
✅ **Security**: Secrets in environment-specific files
✅ **Flexibility**: Common settings shared, environment-specific overrides
✅ **Easy Deployment**: Set `ENVIRONMENT` variable in hosting platform
✅ **Local Development**: SQLite for dev, PostgreSQL for production

## Migration Guide

### For Development

1. **Use `.env.development`**:
```bash
# Already created, just run:
python main.py
# or
ENVIRONMENT=development python main.py
```

2. **Database**: Uses SQLite (`auction_data_dev.db`)
3. **Debug**: Enabled by default
4. **Logs**: DEBUG level

### For Production

1. **Set environment variable**:
```bash
# In Railway/Render dashboard:
ENVIRONMENT=production
```

2. **Override sensitive values**:
```bash
DATABASE_URL=postgresql://...
GSA_API_KEY=your_production_key
API_KEY=your_secure_api_key
SECRET_KEY=your_jwt_secret_min_32_chars
FRONTEND_URL=https://your-app.vercel.app
```

3. **The app automatically**:
   - Loads `.env.common`
   - Loads `.env.production`
   - Overrides with environment variables

## Frontend Compatibility

### Response Structure Changes

**Before** (dict):
```json
{
    "items": [...],
    "total": 100,
    "skip": 0,
    "limit": 20,
    "filters": {...}
}
```

**After** (DTO):
```json
{
    "items": [
        {
            "id": 1,
            "lot_number": "LOT123",
            "title": "...",
            "location": {
                "country": "USA",
                "city": "NYC"
            },
            "bidding": {
                "current_bid": 1000.00,
                "currency": "USD"
            }
        }
    ],
    "pagination": {
        "total": 100,
        "skip": 0,
        "limit": 20,
        "page": 1,
        "total_pages": 5
    },
    "filters": {...}
}
```

### Frontend Updates Needed

1. **Update response parsing**:
```javascript
// Before
const { items, total } = await response.json();

// After
const { items, pagination } = await response.json();
const total = pagination.total;
```

2. **Access nested fields**:
```javascript
// Before
const city = item.city;
const currentBid = item.current_bid;

// After
const city = item.location.city;
const currentBid = item.bidding.current_bid;
```

3. **Image URLs**:
```javascript
// List view - single image
const firstImage = item.image_urls; // string

// Detail view - array of images
const allImages = item.image_urls; // array
```

## Testing

### Test Environment Loading
```bash
# Test development
ENVIRONMENT=development python -c "from config import settings; print(f'Env: {settings.environment}, Debug: {settings.debug}, DB: {settings.database_url}')"

# Test production
ENVIRONMENT=production python -c "from config import settings; print(f'Env: {settings.environment}, Debug: {settings.debug}')"
```

### Test API Response
```bash
# Start server
python main.py

# Test auction list (DTO response)
curl http://localhost:8000/api/auctions?limit=5

# Test auction detail (DTO response)
curl http://localhost:8000/api/auctions/LOT123
```

## Security Notes

⚠️ **Never commit**:
- `.env.production` with real secrets
- Real API keys
- Real database credentials

✅ **Do commit**:
- `.env.common` (non-sensitive)
- `.env.development` (dev/test keys only)
- `.env.production` (template with placeholders)

✅ **In production**:
- Set sensitive values as environment variables in hosting platform
- Use Railway/Render/Vercel's secret management
- Rotate keys regularly

## Troubleshooting

### Environment not loading
```python
# Check which env file is being used
from config import settings
print(f"Environment: {settings.environment}")
print(f"Debug: {settings.debug}")
```

### DTO validation errors
- Check Pydantic error messages in logs
- Ensure database fields match DTO fields
- Verify data types (Decimal → float conversion)

### Frontend getting wrong structure
- Check API docs: http://localhost:8000/docs
- Verify response_model in endpoint decorator
- Test with curl/Postman first
