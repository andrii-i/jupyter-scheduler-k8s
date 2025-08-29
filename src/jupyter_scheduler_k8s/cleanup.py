"""Database retention cleanup for K8s jobs."""

import logging
import os
from datetime import datetime, timedelta
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


def cleanup_old_jobs(namespace: str = "default", dry_run: bool = False):
    """Clean up old execution jobs based on retention policy.
    
    Args:
        namespace: K8s namespace to clean up
        dry_run: If True, only log what would be deleted
    """
    # Get retention policy
    retention_days = os.environ.get("K8S_DATABASE_RETENTION_DAYS")
    
    if retention_days is None:
        retention_days = 30
    elif retention_days.lower() in ["never", "infinite", "0"]:
        logger.info("Retention policy set to 'never' - no cleanup will be performed")
        return
    else:
        try:
            retention_days = int(retention_days)
        except ValueError:
            logger.warning(f"Invalid K8S_DATABASE_RETENTION_DAYS value '{retention_days}', using default 30 days")
            retention_days = 30
    
    cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
    logger.info(f"Cleaning up jupyter-scheduler jobs older than {retention_days} days (before {cutoff_time})")
    
    # Initialize K8s client
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    
    k8s_batch = client.BatchV1Api()
    
    try:
        # List all jupyter-scheduler execution jobs
        jobs = k8s_batch.list_namespaced_job(
            namespace=namespace,
            label_selector="jupyter-scheduler.io/managed-by=jupyter-scheduler-k8s,jupyter-scheduler.io/type=execution"
        )
        
        jobs_to_delete = []
        for job in jobs.items:
            # Check job age based on creation timestamp
            job_created = job.metadata.creation_timestamp
            if job_created and job_created < cutoff_time:
                jobs_to_delete.append(job)
        
        logger.info(f"Found {len(jobs_to_delete)} jobs older than {retention_days} days")
        
        for job in jobs_to_delete:
            job_name = job.metadata.name
            job_age = (datetime.utcnow() - job.metadata.creation_timestamp.replace(tzinfo=None)).days
            
            if dry_run:
                logger.info(f"[DRY RUN] Would delete job {job_name} (age: {job_age} days)")
            else:
                try:
                    k8s_batch.delete_namespaced_job(
                        name=job_name, 
                        namespace=namespace, 
                        propagation_policy="Background"
                    )
                    logger.info(f"Deleted job {job_name} (age: {job_age} days)")
                except ApiException as e:
                    if e.status != 404:
                        logger.error(f"Failed to delete job {job_name}: {e}")
        
        if not dry_run:
            logger.info(f"Cleanup complete - deleted {len(jobs_to_delete)} old jobs")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


def main():
    """CLI entry point for cleanup utility."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up old jupyter-scheduler K8s jobs")
    parser.add_argument("--namespace", default="default", help="K8s namespace (default: default)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    cleanup_old_jobs(namespace=args.namespace, dry_run=args.dry_run)


if __name__ == "__main__":
    main()