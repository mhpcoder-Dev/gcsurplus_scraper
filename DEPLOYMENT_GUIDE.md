# Deployment Steps for Vercel + Neon PostgreSQL

## 🚀 How to Deploy Changes

### 1. Push to Git & Deploy
```bash
git add .
git commit -m "Add country and category fields with API filters"
git push
```

Vercel will automatically deploy your changes.

---

## 🔧 Run Database Migration

After deployment, run the migration via API endpoint:

### Using Postman:
```
Method: POST
URL: https://gcsurplus-scraper.vercel.app/api/migrate
Headers: (none needed)
Body: (none needed)
```

### Using cURL:
```bash
curl -X POST https://gcsurplus-scraper.vercel.app/api/migrate
```

### Expected Response:
```json
{
  "status": "success",
  "message": "Migration completed successfully",
  "steps": [
    "✓ Added 'country' column",
    "✓ Created index on 'country'",
    "✓ Added 'category' column",
    "✓ Created index on 'category'",
    "✓ Updated 25 rows with default country",
    "✓ Auto-detected categories for 25 existing items"
  ]
}
```

---

## ✅ What the Migration Does

### For Existing Data (Your 25 Items):
1. ✅ Adds `country` column → Sets to 'Canada' for all existing records
2. ✅ Adds `category` column → Auto-detects from titles (e.g., "Truck" → "Vehicles")
3. ✅ Creates indexes → Fast filtering performance
4. ✅ **100% Safe** → Won't delete or modify existing data

### Example:
```
Before Migration:
- Lot #123: "Ford F-150 Truck"
  
After Migration:
- Lot #123: "Ford F-150 Truck"
  ├── country: "Canada"
  └── category: "Vehicles"
```

---

## 🧪 Testing After Migration

### 1. Check Stats
```bash
GET https://gcsurplus-scraper.vercel.app/api/stats
```

**Expected Response:**
```json
{
  "total_items": 25,
  "active_auctions": 25,
  "by_country": {
    "Canada": 25,
    "USA": 0
  },
  "by_category": {
    "Vehicles": 12,
    "Electronics": 5,
    "Furniture": 3,
    "Other": 5
  }
}
```

### 2. Filter by Country
```bash
GET https://gcsurplus-scraper.vercel.app/api/auctions?country=Canada&limit=10
```

### 3. Filter by Category
```bash
GET https://gcsurplus-scraper.vercel.app/api/auctions?category=Vehicles&limit=10
```

### 4. Test Pagination
```bash
# Page 1
GET /api/auctions?skip=0&limit=10

# Page 2
GET /api/auctions?skip=10&limit=10

# Page 3
GET /api/auctions?skip=20&limit=10
```

---

## 🔄 Run Migration Multiple Times?

**Yes, it's 100% safe!** The migration:
- Uses `IF NOT EXISTS` checks
- Won't duplicate columns
- Won't overwrite existing data
- Only updates NULL values

---

## 📊 After GCSurplus Maintenance (3 PM ET Today)

Trigger a fresh scrape to get new data with categories:
```bash
POST https://gcsurplus-scraper.vercel.app/api/scrape/manual
```

This will:
- Fetch all new auctions (with pagination)
- Auto-detect categories for each item
- Set country to "Canada"
- Store in your Neon database

---

## 🐛 Troubleshooting

### If migration fails:
1. Check Neon database connection
2. Verify DATABASE_URL is set in Vercel environment variables
3. Check Vercel function logs
4. Try running migration again (it's safe!)

### If no categories detected:
- Categories are auto-detected from titles
- If title doesn't match keywords, category will be "Other"
- You can manually update: `UPDATE auction_items SET category='X' WHERE id=Y`

---

## 📝 Notes for Neon PostgreSQL

✅ Neon supports `ALTER TABLE IF NOT EXISTS` (PostgreSQL 9.6+)
✅ Indexes created automatically
✅ Free tier: 512 MB storage, 1 GB data transfer/month
✅ No downtime during migration
✅ Changes are instant
