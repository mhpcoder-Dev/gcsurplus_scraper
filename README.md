# GCSurplus Scraper API - Vercel Deployment Guide

FastAPI application for scraping and providing API access to GCSurplus.ca auction data. Optimized for deployment on Vercel with PostgreSQL database (free tier compatible).

## 🚀 Features

- **Automated Scraping**: Daily scraping of GCSurplus.ca auction listings via Vercel Cron Jobs
- **PostgreSQL Database**: Cloud-hosted database (Neon, Supabase, or Railway)
- **Free Tier Optimized**: Automatically deletes closed auctions to minimize database usage
- **REST API**: Full CRUD operations with pagination, search, and filters
- **Serverless**: Runs on Vercel's serverless platform (no always-on server costs)

## 📋 Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **PostgreSQL Database**: Choose one:
   - **Neon** (Recommended): https://neon.tech - 500MB free
   - **Supabase**: https://supabase.com - 500MB free
   - **Railway**: https://railway.app - Limited free tier

## 🗄️ Database Setup

### Option 1: Neon (Recommended)

1. Go to [neon.tech](https://neon.tech) and sign up
2. Create a new project
3. Copy the connection string (starts with `postgresql://`)
4. Keep it secure - you'll add it to Vercel later

### Option 2: Supabase

1. Go to [supabase.com](https://supabase.com) and create an account
2. Create a new project
3. Go to **Project Settings** → **Database**
4. Copy the **Connection string** (URI format)
5. Replace `[YOUR-PASSWORD]` with your actual database password

### Option 3: Railway

1. Go to [railway.app](https://railway.app)
2. Create a new project and add PostgreSQL
3. Copy the `DATABASE_URL` from the PostgreSQL service

## 🚢 Deployment Steps

### 1. Install Vercel CLI

```bash
npm install -g vercel
```

### 2. Initialize Project

```bash
cd e:\client\Brianne\gcsurplus-scraper
vercel login
```

### 3. Deploy to Vercel

```bash
vercel --prod
```

Follow the prompts:
- Link to existing project? **No**
- Project name? **gcsurplus-scraper** (or your choice)
- Which directory? **.** (current directory)

### 4. Add Environment Variables

After deployment, add your database URL:

```bash
vercel env add DATABASE_URL production
```

Paste your PostgreSQL connection string when prompted.

**Optional**: Add a cron secret for security:
```bash
vercel env add CRON_SECRET production
```
Enter a random string (e.g., `your-secret-key-here`)

### 5. Set Up Vercel Cron Jobs

1. Go to your project dashboard on [vercel.com](https://vercel.com)
2. Navigate to **Settings** → **Cron Jobs**
3. Add a new cron job:
   - **Path**: `/api/scrape/cron`
   - **Schedule**: `0 2 * * *` (runs daily at 2 AM UTC)
   - Click **Add Cron Job**

### 6. Redeploy

```bash
vercel --prod
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file locally (don't commit this!):

```env
# Database - Use your PostgreSQL connection string
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Optional: Protect cron endpoint
CRON_SECRET=your-secret-key-here

# Next.js app URL (for CORS)
NEXT_PUBLIC_URL=https://your-nextjs-app.vercel.app
```

## 📡 API Endpoints

### Base URL
```
https://your-project.vercel.app
```

### Endpoints

#### 1. Get All Auctions
```http
GET /api/auctions?skip=0&limit=50&status=active&search=truck
```

**Query Parameters**:
- `skip` (optional): Number of items to skip (default: 0)
- `limit` (optional): Number of items to return (default: 50)
- `status` (optional): Filter by status (`active`, `closed`, `expired`)
- `search` (optional): Search in title and description

**Response**:
```json
[
  {
    "id": 1,
    "lot_number": "123456",
    "sale_number": "SALE2024",
    "title": "2015 Ford F-150",
    "description": "...",
    "current_bid": 15000.00,
    "minimum_bid": 10000.00,
    "status": "active",
    "closing_date": "2024-01-15T10:00:00",
    "location_city": "Ottawa",
    "location_province": "ON",
    "image_urls": "[\"https://...\"]"
  }
]
```

#### 2. Get Specific Auction
```http
GET /api/auctions/{lot_number}
```

#### 3. Get Statistics
```http
GET /api/stats
```

**Response**:
```json
{
  "total_items": 150,
  "active_auctions": 120,
  "closed_auctions": 30,
  "expired_auctions": 0
}
```

#### 4. Manual Scrape (Trigger scraping)
```http
POST /api/scrape/manual
```

#### 5. Cleanup Old Items
```http
DELETE /api/cleanup
```

#### 6. Cron Endpoint (For Vercel Cron Jobs)
```http
POST /api/scrape/cron
Authorization: Bearer your-cron-secret
```

## 🔗 Integration with Next.js (MoneyMeta)

### 1. Add Environment Variable

In your Next.js project (`moneymeta`), create or update `.env.local`:

```env
NEXT_PUBLIC_GCSURPLUS_API_URL=https://your-gcsurplus-api.vercel.app
```

### 2. Create API Client

Create `lib/gcsurplus-api.ts`:

```typescript
const API_URL = process.env.NEXT_PUBLIC_GCSURPLUS_API_URL;

export interface AuctionItem {
  id: number;
  lot_number: string;
  sale_number: string;
  title: string;
  description: string;
  current_bid: number;
  minimum_bid: number;
  status: string;
  closing_date: string;
  location_city: string;
  location_province: string;
  image_urls: string;
}

export async function getAuctions(params: {
  skip?: number;
  limit?: number;
  status?: string;
  search?: string;
}): Promise<AuctionItem[]> {
  const queryParams = new URLSearchParams();
  if (params.skip) queryParams.append('skip', params.skip.toString());
  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.status) queryParams.append('status', params.status);
  if (params.search) queryParams.append('search', params.search);

  const response = await fetch(`${API_URL}/api/auctions?${queryParams}`);
  if (!response.ok) throw new Error('Failed to fetch auctions');
  return response.json();
}

export async function getAuction(lotNumber: string): Promise<AuctionItem> {
  const response = await fetch(`${API_URL}/api/auctions/${lotNumber}`);
  if (!response.ok) throw new Error('Auction not found');
  return response.json();
}

export async function getStats() {
  const response = await fetch(`${API_URL}/api/stats`);
  if (!response.ok) throw new Error('Failed to fetch stats');
  return response.json();
}
```

### 3. Use in Next.js Components

```typescript
'use client';

import { useEffect, useState } from 'react';
import { getAuctions, AuctionItem } from '@/lib/gcsurplus-api';

export default function AuctionsPage() {
  const [auctions, setAuctions] = useState<AuctionItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAuctions() {
      try {
        const data = await getAuctions({ limit: 20, status: 'active' });
        setAuctions(data);
      } catch (error) {
        console.error('Error fetching auctions:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchAuctions();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {auctions.map((auction) => (
        <div key={auction.id} className="border rounded-lg p-4">
          <h3 className="font-bold">{auction.title}</h3>
          <p>Current Bid: ${auction.current_bid}</p>
          <p>Location: {auction.location_city}, {auction.location_province}</p>
          <p>Closes: {new Date(auction.closing_date).toLocaleDateString()}</p>
        </div>
      ))}
    </div>
  );
}
```

## 🎯 Free Tier Optimization

The API is configured to stay within free database limits:

- **Automatic Cleanup**: Closed/expired auctions are deleted immediately
- **Only Active Data**: Database stores only active auctions
- **Efficient Queries**: Indexed searches for fast performance
- **Connection Pooling**: Optimized database connections

This keeps database size under 500MB for Neon/Supabase free tiers.

## 🐛 Troubleshooting

### Database Connection Issues
- Verify `DATABASE_URL` is correct in Vercel environment variables
- Check if database allows connections from Vercel IPs
- Ensure database is not paused (Neon pauses after inactivity)

### Cron Jobs Not Running
- Verify cron job is configured in Vercel dashboard
- Check **Deployments** → **Functions** log for errors
- Ensure `/api/scrape/cron` endpoint exists

### CORS Errors in Next.js
- Add your Next.js domain to `NEXT_PUBLIC_URL` environment variable
- Redeploy after adding environment variables

### Scraping Fails
- GCSurplus.ca may have changed their HTML structure
- Check logs in Vercel Functions tab
- Update selectors in `app/scraper.py` if needed

## 📝 Local Development

For local testing:

```bash
# Install dependencies
pip install -r requirements.txt

# Set up local PostgreSQL or use a cloud database
export DATABASE_URL="postgresql://user:pass@localhost:5432/gcsurplus"

# Run locally
python run.py
```

API will be available at `http://localhost:8001`

## 🔐 Security

- Never commit `.env` files
- Use Vercel environment variables for secrets
- Add `CRON_SECRET` to protect the cron endpoint
- Use HTTPS for all production requests

## 📦 Project Structure

```
gcsurplus-scraper/
├── api/
│   └── index.py          # Vercel serverless entry point
├── app/
│   ├── __init__.py
│   ├── config.py         # Settings (DATABASE_URL, etc.)
│   ├── database.py       # PostgreSQL models
│   ├── scraper.py        # GCSurplus scraper logic
│   ├── crud.py           # Database operations
│   └── main.py           # FastAPI app & endpoints
├── vercel.json           # Vercel configuration
├── requirements.txt      # Python dependencies
├── .env                  # Local environment variables (git ignored)
├── .gitignore
└── README.md
```

## 📄 License

This project is for educational purposes. Always respect the terms of service of websites you scrape.

## 🙏 Disclaimer

This scraper is designed to access publicly available data from GCSurplus.ca. Use responsibly and in accordance with the website's terms of service. The authors are not responsible for any misuse of this software.

---

**Need Help?** Open an issue on GitHub or contact the project maintainers.
