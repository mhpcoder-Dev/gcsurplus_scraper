# API Features Update

## New Features Added

### 1. Country Field
- **Field**: `country` (String)
- **Values**: `Canada` or `USA`
- **Default**: `Canada` (for GCSurplus.ca)
- **Purpose**: Filter auctions by country of origin

### 2. Category Field
- **Field**: `category` (String)
- **Auto-detected** from auction title using keywords
- **Categories**:
  - Vehicles
  - Motorcycles
  - Electronics
  - Furniture
  - Industrial
  - Real Estate
  - Collectibles
  - Office Equipment
  - Medical
  - Kitchen
  - Other

### 3. Pagination (Already Implemented)
The API already supports pagination to fetch data in batches:
- **skip**: Number of items to skip (default: 0)
- **limit**: Number of items to return (default: 100, max: 500)

## API Endpoints

### GET /api/auctions
Get paginated auction items with filters.

**Query Parameters:**
```
skip       - Number of items to skip (default: 0)
limit      - Number of items to return (default: 100, max: 500)
status     - Filter by status: active, closed, expired
search     - Search in title and description
country    - Filter by country: Canada, USA
category   - Filter by category (partial match supported)
```

**Examples:**
```bash
# Get first 25 items from Canada
GET /api/auctions?limit=25&country=Canada

# Get vehicles only
GET /api/auctions?category=Vehicles

# Get electronics from Canada, skip first 50
GET /api/auctions?category=Electronics&country=Canada&skip=50&limit=25

# Get active auctions only
GET /api/auctions?status=active

# Search for "laptop" in Canadian auctions
GET /api/auctions?search=laptop&country=Canada

# Pagination example - Page 2 with 25 items per page
GET /api/auctions?skip=25&limit=25
```

### GET /api/stats
Get database statistics including country and category breakdowns.

**Response:**
```json
{
  "total_items": 150,
  "active_auctions": 120,
  "closed_auctions": 25,
  "expired_auctions": 5,
  "by_country": {
    "Canada": 145,
    "USA": 5
  },
  "by_category": {
    "Vehicles": 45,
    "Electronics": 30,
    "Furniture": 25,
    "Industrial": 20,
    "Other": 30
  }
}
```

## Database Migration

If you have an existing database, run the migration script to add the new columns:

```bash
python migrate_db.py
```

This will:
1. Add `country` column (default: 'Canada')
2. Add `category` column
3. Create indexes on both columns for faster filtering

## Frontend Implementation Guide

### Pagination Example (React/Next.js)
```javascript
const [page, setPage] = useState(1);
const itemsPerPage = 25;

const fetchAuctions = async () => {
  const skip = (page - 1) * itemsPerPage;
  const response = await fetch(
    `/api/auctions?skip=${skip}&limit=${itemsPerPage}&country=Canada`
  );
  const data = await response.json();
  return data;
};
```

### Filter by Category
```javascript
const [selectedCategory, setSelectedCategory] = useState('');

const fetchByCategory = async (category) => {
  const response = await fetch(
    `/api/auctions?category=${category}&country=Canada&limit=25`
  );
  const data = await response.json();
  return data;
};
```

### Combined Filters
```javascript
const fetchWithFilters = async ({
  country = 'Canada',
  category = '',
  search = '',
  status = 'active',
  page = 1,
  limit = 25
}) => {
  const skip = (page - 1) * limit;
  const params = new URLSearchParams({
    skip,
    limit,
    status,
    ...(country && { country }),
    ...(category && { category }),
    ...(search && { search })
  });
  
  const response = await fetch(`/api/auctions?${params}`);
  return await response.json();
};
```

## How Category Detection Works

The scraper automatically detects categories by analyzing auction titles using keyword matching:

```python
# Example: "2015 Ford F-150 Truck" → Category: "Vehicles"
# Example: "Dell Laptop Computer" → Category: "Electronics"
# Example: "Office Desk and Chair Set" → Category: "Furniture"
```

If no category keywords are found, items are classified as "Other".

## Notes

- **Pagination** prevents loading all data at once, improving performance
- **Country field** allows filtering for Canada-only or USA-only auctions
- **Category field** is auto-detected and indexed for fast filtering
- All filters can be combined for precise queries
- The API returns data in descending order by `updated_at` (newest first)
