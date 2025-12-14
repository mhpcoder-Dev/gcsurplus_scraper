# 🚀 Deployment Checklist

## ✅ Pre-Deployment

- [ ] All code changes committed
- [ ] Python dependencies updated in `requirements.txt`
- [ ] `.gitignore` includes `.env` and `*.db` files
- [ ] Database.py configured for PostgreSQL
- [ ] Config.py uses environment variables

## 🗄️ Database Setup

Choose ONE option:

### Option A: Neon (Recommended)
- [ ] Sign up at https://neon.tech
- [ ] Create new project
- [ ] Copy PostgreSQL connection string
- [ ] Save connection string securely

### Option B: Supabase
- [ ] Sign up at https://supabase.com
- [ ] Create new project
- [ ] Navigate to Settings → Database
- [ ] Copy connection string (URI format)
- [ ] Replace `[YOUR-PASSWORD]` with actual password

### Option C: Railway
- [ ] Sign up at https://railway.app
- [ ] Create project + add PostgreSQL
- [ ] Copy `DATABASE_URL` from PostgreSQL service

## 🌐 Vercel Deployment

### 1. Install Vercel CLI
```bash
npm install -g vercel
```

### 2. Login to Vercel
```bash
vercel login
```

### 3. Deploy
```bash
cd e:\client\Brianne\gcsurplus-scraper
vercel --prod
```

- [ ] Deployment successful
- [ ] Note the deployment URL: `https://______________.vercel.app`

### 4. Add Environment Variables

```bash
vercel env add DATABASE_URL production
```
- [ ] DATABASE_URL added (paste your PostgreSQL connection string)

```bash
vercel env add CRON_SECRET production
```
- [ ] CRON_SECRET added (random string for security)

```bash
vercel env add NEXT_PUBLIC_URL production
```
- [ ] NEXT_PUBLIC_URL added (your MoneyMeta Next.js URL)

### 5. Redeploy with Environment Variables
```bash
vercel --prod
```
- [ ] Redeployed successfully

## ⏰ Configure Cron Jobs

1. Go to Vercel dashboard: https://vercel.com/dashboard
2. Select your project
3. Navigate to **Settings** → **Cron Jobs**
4. Click **Add Cron Job**
   - Path: `/api/scrape/cron`
   - Schedule: `0 2 * * *` (Daily at 2 AM UTC)
5. Save

- [ ] Cron job configured
- [ ] Cron job appears in dashboard

## 🧪 Test Deployment

### Test Root Endpoint
```bash
curl https://your-project.vercel.app/
```
- [ ] Returns API information

### Test Auctions Endpoint
```bash
curl https://your-project.vercel.app/api/auctions?limit=5
```
- [ ] Returns auction data (may be empty initially)

### Test Stats Endpoint
```bash
curl https://your-project.vercel.app/api/stats
```
- [ ] Returns database statistics

### Trigger Manual Scrape
```bash
curl -X POST https://your-project.vercel.app/api/scrape/manual
```
- [ ] Scraping job started
- [ ] Check Vercel logs for success

### Check Vercel Logs
1. Go to Vercel dashboard
2. Click on your project
3. Go to **Deployments** tab
4. Click on latest deployment
5. Go to **Functions** tab
6. Check logs for any errors

- [ ] No errors in logs
- [ ] Scraper ran successfully

## 🔗 Integrate with MoneyMeta (Next.js)

### 1. Add Environment Variable

In `moneymeta` project root, create/update `.env.local`:

```env
NEXT_PUBLIC_GCSURPLUS_API_URL=https://your-gcsurplus-api.vercel.app
```

- [ ] Environment variable added to MoneyMeta

### 2. Create API Client

Create `moneymeta/lib/gcsurplus-api.ts` (see README for full code)

- [ ] API client file created
- [ ] TypeScript types defined

### 3. Test in Next.js

Create a test page or component:

```typescript
import { getAuctions } from '@/lib/gcsurplus-api';

// Use in component...
```

- [ ] API calls work from Next.js
- [ ] Data displays correctly
- [ ] No CORS errors

## 🎯 Post-Deployment Verification

### Database
- [ ] Database connection works
- [ ] Tables created automatically
- [ ] Data being stored

### Cron Jobs
- [ ] Wait for next scheduled run (or test manually)
- [ ] Check Vercel logs after cron run
- [ ] Verify new data appears in database

### API Performance
- [ ] API responses are fast (< 2 seconds)
- [ ] Pagination works
- [ ] Search functionality works
- [ ] Filters work correctly

### Cleanup Automation
- [ ] Closed auctions are deleted immediately
- [ ] Database size stays under 500MB

## 🐛 Troubleshooting

If anything fails, check:

1. **Database Connection**
   - [ ] DATABASE_URL is correct
   - [ ] Database allows Vercel IP connections
   - [ ] Database is not paused (Neon)

2. **Cron Jobs**
   - [ ] Cron path is exactly `/api/scrape/cron`
   - [ ] Schedule is valid cron expression
   - [ ] CRON_SECRET matches in env vars

3. **CORS Issues**
   - [ ] NEXT_PUBLIC_URL is set
   - [ ] Origin matches exactly
   - [ ] Redeploy after env var changes

4. **Scraping Fails**
   - [ ] GCSurplus.ca is accessible
   - [ ] Selectors in scraper.py are still valid
   - [ ] Check Vercel function timeout (max 10s on free tier)

## 📊 Success Criteria

- ✅ API is live and accessible
- ✅ Database stores auction data
- ✅ Cron jobs run daily automatically
- ✅ Closed auctions are deleted
- ✅ Next.js can fetch data from API
- ✅ No CORS errors
- ✅ Database stays under free tier limits

## 🎉 Deployment Complete!

Your GCSurplus scraper is now live and will automatically scrape auction data daily.

**API URL**: https://______________.vercel.app
**Next.js Integration**: Complete
**Database**: PostgreSQL (Neon/Supabase/Railway)
**Scraping Schedule**: Daily at 2 AM UTC

---

**Next Steps:**
- Build UI in MoneyMeta to display auctions
- Add search and filter functionality
- Create auction detail pages
- Set up notifications for new auctions
