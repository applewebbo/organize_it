---
# optimize
title: Optimize session cleanup task
status: scrapped
type: task
priority: "3"
created_at: 2026-03-31T06:02:32Z
updated_at: 2026-04-07T18:35:03Z
---

# Optimize session cleanup task

## Objective
Reduce query count from 2 to 1 for session cleanup.

## Required changes

### `trips/tasks.py` - cleanup_old_sessions() (line ~101)
```python
def cleanup_old_sessions():
    """
    Delete expired sessions from database.
    """
    try:
        logger.info("Starting cleanup_old_sessions task")

        # Single queryset for count and delete
        expired_qs = Session.objects.filter(expire_date__lt=timezone.now())

        # Count using queryset (single query)
        expired_count = expired_qs.count()

        if expired_count > 0:
            expired_qs.delete()  # Reuse same queryset
            result_msg = f"Deleted {expired_count} expired sessions"
            logger.info(result_msg)
            return result_msg
        else:
            logger.debug("No expired sessions to delete")  # DEBUG level
            return "No expired sessions found"

    except Exception as e:
        logger.error(f"Error in cleanup_old_sessions task: {e}", exc_info=True)
        raise
```

## Test
1. Create expired sessions manually
2. Run task: `python manage.py qcluster`
3. Verify sessions deleted
4. Run `just ftest`

## Acceptance criteria
- [ ] Single query for cleanup
- [ ] Log shows correct count
- [ ] All tests pass

## Reasons for Scrapping\n\nNot a priority for current release cycle.
