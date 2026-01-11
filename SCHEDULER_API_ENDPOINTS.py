"""
Optional API endpoints for managing the scheduler at runtime.

Add these endpoints to main.py if you want to expose scheduler management via HTTP.
This allows you to pause/resume scraping, trigger immediate scrapes, and monitor jobs
without restarting the application.
"""

# Add these imports to main.py
from fastapi import HTTPException
from scheduler import get_scheduler

# Then add these routes to main.py after the existing endpoints:


@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """
    Get status of all scheduled jobs.
    
    Returns:
        List of jobs with their status, next run time, and last execution info
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler is disabled")
    
    jobs = scheduler.get_all_jobs_status()
    return {
        "scheduler_running": scheduler.scheduler.running,
        "timezone": scheduler.timezone,
        "jobs": jobs,
        "total_jobs": len(jobs)
    }


@app.get("/api/scheduler/jobs/{site_name}")
async def get_job_status(site_name: str):
    """
    Get status of a specific site's scraping job.
    
    Args:
        site_name: Name of the site ('gcsurplus', 'gsa', 'treasury')
        
    Returns:
        Job details including next run time and last execution status
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler is disabled")
    
    job_id = f"scrape_{site_name}"
    job = scheduler.scheduler.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"No job found for site: {site_name}")
    
    job_status = scheduler.job_status.get(job_id, {})
    
    return {
        "site": site_name,
        "job_id": job_id,
        "name": job.name,
        "next_run": job.next_run_time,
        "status": job_status.get('status', 'unknown'),
        "last_run": job_status.get('last_run'),
        "error": job_status.get('error')
    }


@app.post("/api/scheduler/run/{site_name}")
async def run_site_now(site_name: str):
    """
    Trigger an immediate scrape for a specific site.
    Useful for manual testing or urgent updates.
    
    Args:
        site_name: Name of the site ('gcsurplus', 'gsa', 'treasury')
        
    Returns:
        Confirmation that the job was triggered
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler is disabled")
    
    success = scheduler.run_site_now(site_name)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"No job found for site: {site_name}")
    
    return {
        "site": site_name,
        "message": f"Scrape triggered for {site_name}",
        "status": "queued"
    }


@app.post("/api/scheduler/pause/{site_name}")
async def pause_scraping(site_name: str):
    """
    Pause scraping for a specific site.
    The scheduled job will not run until resumed.
    
    Args:
        site_name: Name of the site ('gcsurplus', 'gsa', 'treasury')
        
    Returns:
        Confirmation that the site was paused
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler is disabled")
    
    success = scheduler.pause_site(site_name)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"No job found for site: {site_name}")
    
    return {
        "site": site_name,
        "message": f"Scraping paused for {site_name}",
        "status": "paused"
    }


@app.post("/api/scheduler/resume/{site_name}")
async def resume_scraping(site_name: str):
    """
    Resume scraping for a specific site.
    The job will resume its regular schedule.
    
    Args:
        site_name: Name of the site ('gcsurplus', 'gsa', 'treasury')
        
    Returns:
        Confirmation that the site was resumed
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler is disabled")
    
    success = scheduler.resume_site(site_name)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"No job found for site: {site_name}")
    
    return {
        "site": site_name,
        "message": f"Scraping resumed for {site_name}",
        "status": "running"
    }


@app.get("/api/scheduler/next-run/{site_name}")
async def get_next_run_time(site_name: str):
    """
    Get the next scheduled run time for a specific site.
    
    Args:
        site_name: Name of the site ('gcsurplus', 'gsa', 'treasury')
        
    Returns:
        Next run time in ISO format
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler is disabled")
    
    next_run = scheduler.get_next_run_time(site_name)
    
    if next_run is None:
        raise HTTPException(status_code=404, detail=f"No job found for site: {site_name}")
    
    return {
        "site": site_name,
        "next_run": next_run.isoformat()
    }


"""
USAGE EXAMPLES:

Get all job statuses:
  GET http://localhost:8001/api/scheduler/status

Get status of GCSurplus job:
  GET http://localhost:8001/api/scheduler/jobs/gcsurplus

Trigger immediate scrape for GSA:
  POST http://localhost:8001/api/scheduler/run/gsa

Pause Treasury scraping:
  POST http://localhost:8001/api/scheduler/pause/treasury

Resume Treasury scraping:
  POST http://localhost:8001/api/scheduler/resume/treasury

Get next run time for GCSurplus:
  GET http://localhost:8001/api/scheduler/next-run/gcsurplus


RESPONSE EXAMPLES:

GET /api/scheduler/status
{
  "scheduler_running": true,
  "timezone": "UTC",
  "jobs": [
    {
      "id": "scrape_gcsurplus",
      "name": "Scrape GCSURPLUS",
      "next_run": "2026-01-12T02:00:00+00:00",
      "status": "success",
      "last_run": "2026-01-11T02:00:15.123456+00:00"
    },
    {
      "id": "scrape_gsa",
      "name": "Scrape GSA",
      "next_run": "2026-01-11T14:00:00+00:00",
      "status": "success",
      "last_run": "2026-01-11T14:00:22.456789+00:00"
    },
    {
      "id": "scrape_treasury",
      "name": "Scrape TREASURY",
      "next_run": "2026-01-13T03:00:00+00:00",
      "status": "success",
      "last_run": "2026-01-11T03:00:18.789012+00:00"
    }
  ],
  "total_jobs": 3
}

GET /api/scheduler/jobs/gcsurplus
{
  "site": "gcsurplus",
  "job_id": "scrape_gcsurplus",
  "name": "Scrape GCSURPLUS",
  "next_run": "2026-01-12T02:00:00+00:00",
  "status": "success",
  "last_run": "2026-01-11T02:00:15.123456+00:00",
  "error": null
}

POST /api/scheduler/run/gsa
{
  "site": "gsa",
  "message": "Scrape triggered for gsa",
  "status": "queued"
}

POST /api/scheduler/pause/treasury
{
  "site": "treasury",
  "message": "Scraping paused for treasury",
  "status": "paused"
}

GET /api/scheduler/next-run/gcsurplus
{
  "site": "gcsurplus",
  "next_run": "2026-01-12T02:00:00+00:00"
}
"""
