# Treasury.gov Scraper - Deployment Checklist

## Pre-Deployment

### 1. Testing
- [ ] Run test script: `python test_treasury_scraper.py`
- [ ] Verify scraper finds auctions (if any are listed)
- [ ] Check sample data looks correct
- [ ] Verify detail pages are being scraped
- [ ] Check images are loading

### 2. Configuration
- [ ] Verify `config.py` has Treasury URLs
- [ ] Check `.env` file (if using)
- [ ] Ensure database connection works
- [ ] Verify API port is available

### 3. Dependencies
- [ ] All packages in `requirements.txt` installed
- [ ] `beautifulsoup4` version compatible
- [ ] `requests` working correctly
- [ ] `sqlalchemy` properly configured

## Deployment Steps

### 1. Initial Scrape
```bash
# Start the API server
python start.py

# In another terminal, trigger first scrape
curl -X POST http://localhost:8001/api/scrape/treasury
```

- [ ] Scrape completes without errors
- [ ] Check logs for scrape results
- [ ] Verify data in database

### 2. Verify API Endpoints
```bash
# Check root endpoint
curl http://localhost:8001/

# Check Treasury endpoint
curl http://localhost:8001/api/auctions/treasury

# Check upcoming endpoint
curl http://localhost:8001/api/auctions/upcoming

# Check stats
curl http://localhost:8001/api/stats
```

- [ ] All endpoints respond
- [ ] Data format is correct
- [ ] Statistics show Treasury auctions
- [ ] Pagination works

### 3. Frontend Integration
- [ ] Create upcoming auctions page
- [ ] Test API connection from frontend
- [ ] Verify data displays correctly
- [ ] Check image URLs work
- [ ] Test filtering and search

### 4. Schedule Automation
- [ ] Set up weekly scraping (recommended)
- [ ] Configure cron job or scheduler
- [ ] Test scheduled scrape runs
- [ ] Monitor execution logs

## Post-Deployment

### 1. Monitoring
- [ ] Set up log monitoring
- [ ] Check scrape success rate
- [ ] Monitor API response times
- [ ] Track database growth

### 2. Data Quality
- [ ] Verify auction data is accurate
- [ ] Check detail pages load correctly
- [ ] Confirm dates are parsed properly
- [ ] Validate location data

### 3. Performance
- [ ] Check API response times
- [ ] Monitor database query performance
- [ ] Verify scraping doesn't timeout
- [ ] Test with multiple concurrent users

### 4. User Experience
- [ ] Test upcoming auctions page load time
- [ ] Verify auction details display correctly
- [ ] Check mobile responsiveness
- [ ] Test filtering functionality

## Ongoing Maintenance

### Daily
- [ ] Check for scrape errors in logs
- [ ] Monitor API availability

### Weekly
- [ ] Review scrape results
- [ ] Check data quality
- [ ] Verify detail pages accessible

### Monthly
- [ ] Review database size
- [ ] Check index performance
- [ ] Update documentation if needed
- [ ] Test with latest website structure

## Troubleshooting Checklist

### If No Auctions Found
- [ ] Check if Treasury website has active auctions
- [ ] Run test script to diagnose
- [ ] Verify URLs in config are correct
- [ ] Check network connectivity
- [ ] Review website structure for changes

### If Detail Pages Failing
- [ ] Check detail page URLs in database
- [ ] Verify detail pages exist on website
- [ ] Check for temporary URL patterns
- [ ] Review error logs for specifics
- [ ] Confirm base URL is correct

### If API Errors
- [ ] Check database connection
- [ ] Verify migration was run
- [ ] Check logs for errors
- [ ] Test individual endpoints
- [ ] Restart API server

### If Data Issues
- [ ] Verify scraper completed successfully
- [ ] Check for parsing errors in logs
- [ ] Review sample data from test script
- [ ] Validate against website data
- [ ] Check extra_data field for details

## Rollback Plan

If issues occur:

1. **Stop Current Scraping**
   ```bash
   # If using systemd
   sudo systemctl stop auction-scraper
   ```

2. **Check Logs**
   ```bash
   tail -f logs/scraper.log
   ```

3. **Revert Database** (if needed)
   ```sql
   DELETE FROM auction_items WHERE source = 'treasury';
   ```

4. **Fix Issues**
   - Update configuration
   - Fix code if needed
   - Re-test with test script

5. **Restart**
   ```bash
   python start.py
   ```

## Success Criteria

✅ All checks passed:
- [ ] Test script runs successfully
- [ ] Initial scrape finds auctions
- [ ] API endpoints return data
- [ ] Frontend displays auctions
- [ ] Automated scraping scheduled
- [ ] Monitoring in place
- [ ] Documentation reviewed

## Notes

**Date Deployed:** _________________

**Deployed By:** _________________

**Initial Auction Count:** _________________

**Issues Encountered:**
- 
- 
- 

**Resolution:**
- 
- 
- 

## Contact Information

**Technical Issues:** _________________

**Data Quality:** _________________

**Frontend Integration:** _________________

---

## Quick Reference Commands

```bash
# Test scraper
python test_treasury_scraper.py

# Start API
python start.py

# Manual scrape
curl -X POST http://localhost:8001/api/scrape/treasury

# Check results
curl http://localhost:8001/api/auctions/upcoming

# View stats
curl http://localhost:8001/api/stats
```
