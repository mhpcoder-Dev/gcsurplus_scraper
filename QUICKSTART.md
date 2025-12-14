# ⚡ Quick Start Guide

Get your GCSurplus scraper deployed in 15 minutes!

## 📋 What You Need

1. GitHub account (to store code)
2. Vercel account (for hosting) - [Sign up free](https://vercel.com)
3. Database account (choose one):
   - [Neon](https://neon.tech) - **Recommended for beginners**
   - [Supabase](https://supabase.com)
   - [Railway](https://railway.app)

## 🚀 5-Minute Setup

### Step 1: Get Your Database (2 min)

**Using Neon (Easiest)**:
1. Go to [neon.tech](https://neon.tech) and click "Sign Up"
2. Click "Create a project"
3. Copy the connection string that appears
4. Save it somewhere - you'll need it soon!

### Step 2: Deploy to Vercel (2 min)

Open terminal/PowerShell in the project folder:

```bash
# Install Vercel CLI (one-time setup)
npm install -g vercel

# Login
vercel login

# Deploy!
cd e:\client\Brianne\gcsurplus-scraper
vercel --prod
```

Follow the prompts:
- **Set up and deploy?** → Y
- **Which scope?** → Your account
- **Link to existing project?** → N
- **Project name?** → gcsurplus-scraper
- **In which directory?** → . (just press Enter)

**Save your deployment URL** - looks like: `https://gcsurplus-scraper.vercel.app`

### Step 3: Add Database URL (1 min)

```bash
vercel env add DATABASE_URL production
```

When prompted, paste your Neon connection string (from Step 1).

### Step 4: Redeploy (1 min)

```bash
vercel --prod
```

### Step 5: Set Up Daily Scraping (1 min)

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Click your project
3. Go to **Settings** → **Cron Jobs**
4. Click **Add Cron Job**:
   - Path: `/api/scrape/cron`
   - Schedule: `0 2 * * *`
5. Click **Create**

## ✅ Test It!

Open your browser and visit:

```
https://your-project-name.vercel.app/api/auctions
```

You should see: `[]` (empty array - no data yet)

Trigger first scrape:

```
https://your-project-name.vercel.app/api/scrape/manual
```

Wait 30 seconds, then check again:

```
https://your-project-name.vercel.app/api/auctions?limit=5
```

You should see auction data! 🎉

## 🔗 Connect to MoneyMeta

In your MoneyMeta (Next.js) project:

1. Create `.env.local`:
```env
NEXT_PUBLIC_GCSURPLUS_API_URL=https://your-project-name.vercel.app
```

2. Create `lib/gcsurplus-api.ts`:
```typescript
const API_URL = process.env.NEXT_PUBLIC_GCSURPLUS_API_URL;

export async function getAuctions(params?: {
  skip?: number;
  limit?: number;
  status?: string;
  search?: string;
}) {
  const query = new URLSearchParams();
  if (params?.skip) query.append('skip', params.skip.toString());
  if (params?.limit) query.append('limit', params.limit.toString());
  if (params?.status) query.append('status', params.status);
  if (params?.search) query.append('search', params.search);

  const response = await fetch(`${API_URL}/api/auctions?${query}`);
  return response.json();
}
```

3. Use in your components:
```typescript
'use client';
import { useEffect, useState } from 'react';
import { getAuctions } from '@/lib/gcsurplus-api';

export default function AuctionsPage() {
  const [auctions, setAuctions] = useState([]);

  useEffect(() => {
    getAuctions({ limit: 20 }).then(setAuctions);
  }, []);

  return (
    <div>
      {auctions.map(auction => (
        <div key={auction.id}>
          <h3>{auction.title}</h3>
          <p>${auction.current_bid}</p>
        </div>
      ))}
    </div>
  );
}
```

## 🎯 What Happens Now?

- ✅ Your API is live at `https://your-project.vercel.app`
- ✅ Database stores only active auctions (saves space!)
- ✅ Scraper runs automatically every day at 2 AM UTC
- ✅ Closed auctions are deleted automatically
- ✅ Everything stays within free tiers!

## 📊 Check Your Data

Visit the Swagger docs:
```
https://your-project-name.vercel.app/docs
```

Interactive API documentation where you can test all endpoints!

## 🆘 Having Issues?

### "Database connection failed"
- Double-check your DATABASE_URL in Vercel dashboard
- Make sure you pasted the full connection string

### "No data appearing"
- Trigger manual scrape: `POST /api/scrape/manual`
- Check Vercel logs: Dashboard → Your Project → Deployments → Functions

### "CORS error in Next.js"
- Add env var: `vercel env add NEXT_PUBLIC_URL production`
- Enter your MoneyMeta URL
- Redeploy: `vercel --prod`

## 📚 More Help

- **Detailed guide**: See [README.md](./README.md)
- **Step-by-step**: See [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)
- **Migration info**: See [MIGRATION_SUMMARY.md](./MIGRATION_SUMMARY.md)

## 🎉 You're Done!

Your GCSurplus auction scraper is now:
- ✅ Deployed on Vercel (free)
- ✅ Using PostgreSQL database (free)
- ✅ Scraping daily automatically
- ✅ Ready to use with MoneyMeta

**API URL**: `https://your-project-name.vercel.app`

---

**Pro Tip**: Star your Vercel project in the dashboard to find it easily!
