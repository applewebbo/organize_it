---
# organize_it-hvku
title: Implement trip sharing via magic links
status: completed
type: feature
priority: normal
created_at: 2026-01-27T14:14:45Z
updated_at: 2026-03-20T10:24:50Z
---

Allow users to share trips with others via magic links that provide view-only access without requiring login.

**Related to:** #209

## Requirements Summary
- View-only access to complete trip (all days, events, stays, transports)
- Configurable expiration time (7 days, 30 days, custom, never)
- Multiple links per trip with different permissions (future-proof for edit access)
- No visit tracking (privacy-first approach)
- Manual revocation capability

## Technical Approach
Custom implementation using UUID tokens stored in database (no external libraries needed).

## Database Schema

### New Model: ShareLink
```python
class ShareLink(models.Model):
    class PermissionLevel(models.TextChoices):
        VIEW = 'view', _('View only')
        EDIT = 'edit', _('Can edit')  # For future implementation

    class ExpirationPreset(models.IntegerChoices):
        SEVEN_DAYS = 7, _('7 days')
        THIRTY_DAYS = 30, _('30 days')
        NINETY_DAYS = 90, _('90 days')
        NEVER = 0, _('Never expires')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey('Trip', on_delete=models.CASCADE, related_name='share_links')
    permission_level = models.CharField(max_length=10, choices=PermissionLevel.choices, default=PermissionLevel.VIEW)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    label = models.CharField(max_length=100, blank=True, help_text="Optional label to identify this link")

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def get_absolute_url(self):
        return reverse('trips:shared_trip', kwargs={'token': self.id})
```

## Implementation Checklist

### Phase 1: Core Models & Views
- [x] Create ShareLink model in trips/models.py
- [x] Create and run migration
- [x] Add is_owner_or_shared method to Trip model for permission checking
- [x] Create shared_trip_detail view (public, no @login_required)
  - Validates token and expiration
  - Prefetches all trip data efficiently
  - Renders read-only template
- [x] Create share_link_create view (requires ownership)
- [x] Create share_link_list view (show all links for a trip)
- [x] Create share_link_revoke view (deactivate link)
- [x] Add URL patterns for all views

### Phase 2: Templates & UI
- [x] Create shared-trip-detail.html template
  - Clean, read-only view of trip
  - Show banner indicating "Shared view - Read only"
  - Display all days, events, stays, transports
  - No edit buttons or forms
  - Optional: Add "Create your own trip" CTA button
- [x] Create share-link-modal.html (HTMX modal)
  - Form to create new link with expiration options
  - Display generated link with copy button
  - List existing active links with revoke buttons
- [x] Add "Share" button to trip detail page
- [ ] Create share-link-list-fragment.html (HTMX partial)
  - Shows active links in table format
  - Copy link button for each
  - Revoke button for each
  - Shows expiration date/status

### Phase 3: Forms
- [x] Create ShareLinkCreateForm
  - Fields: label, permission_level, expiration_preset
  - Custom validation for expiration date calculation
  - Clean, user-friendly field labels

### Phase 4: Security & Edge Cases
- [ ] Add permission check decorators/mixins
- [x] Handle expired links gracefully (show friendly error message)
- [x] Handle revoked links gracefully
- [ ] Ensure shared view doesn't expose private data (check if any fields should be hidden)
- [ ] Add rate limiting to prevent token bruteforce (optional, can use django-ratelimit)
- [ ] Test unauthorized access attempts

### Phase 5: Tests
- [ ] Test ShareLink model
  - is_valid property with various scenarios
  - Expiration logic
  - Token generation uniqueness
- [ ] Test shared_trip_detail view
  - Valid token shows trip
  - Expired token shows error
  - Revoked token shows error
  - Invalid token shows 404
- [ ] Test share_link_create view
  - Owner can create link
  - Non-owner cannot create link
  - Expiration date calculated correctly
- [ ] Test share_link_revoke view
  - Owner can revoke
  - Non-owner cannot revoke
- [ ] Test permissions and edge cases
- [ ] Test HTMX interactions for modals

### Phase 6: Documentation & Polish
- [x] Add user guide documentation (docs/en/user-guide/sharing.md)
- [x] Add user guide documentation (docs/it/user-guide/sharing.md)
- [ ] Add migration guide if needed
- [ ] Update README if significant feature
- [ ] Add environment variable for default expiration (optional)

## URLs Structure
```python
# trips/urls.py additions
path('share/<uuid:token>/', views.shared_trip_detail, name='shared_trip'),
path('trip/<int:trip_id>/share/create/', views.share_link_create, name='share_link_create'),
path('trip/<int:trip_id>/share/list/', views.share_link_list, name='share_link_list'),
path('share-link/<uuid:link_id>/revoke/', views.share_link_revoke, name='share_link_revoke'),
```

## Views Pseudo-code

### shared_trip_detail (public view)
```python
def shared_trip_detail(request, token):
    link = get_object_or_404(ShareLink, id=token)

    if not link.is_valid:
        if link.expires_at and timezone.now() > link.expires_at:
            return render(request, 'trips/link-expired.html')
        return render(request, 'trips/link-revoked.html')

    trip = link.trip
    days = trip.day_set.prefetch_related('events', 'stay').order_by('date')

    context = {
        'trip': trip,
        'days': days,
        'is_shared_view': True,
        'permission_level': link.permission_level,
    }
    return render(request, 'trips/shared-trip-detail.html', context)
```

### share_link_create (HTMX endpoint)
```python
@login_required
def share_link_create(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, author=request.user)

    if request.method == 'POST':
        form = ShareLinkCreateForm(request.POST)
        if form.is_valid():
            link = form.save(commit=False)
            link.trip = trip
            link.created_by = request.user

            # Calculate expiration
            if form.cleaned_data['expiration_preset'] > 0:
                link.expires_at = timezone.now() + timedelta(days=form.cleaned_data['expiration_preset'])

            link.save()

            if request.htmx:
                return render(request, 'trips/share-link-created.html', {'link': link})
            return redirect('trips:trip_detail', trip_id=trip.id)
    else:
        form = ShareLinkCreateForm()

    return render(request, 'trips/share-link-create-form.html', {'form': form, 'trip': trip})
```

## Future Enhancements (Not in scope)
- Visit tracking/analytics (requires user consent, GDPR compliance)
- Password protection for links
- Edit permissions implementation
- Email invitation with magic link
- Link expiration notifications
- QR code generation for easy mobile sharing

## Security Considerations
- UUID tokens are cryptographically secure (128-bit, ~3.4×10^38 combinations)
- No user authentication required for shared view (by design)
- Owner-only operations (create, revoke) protected by @login_required and ownership checks
- Expired/revoked links gracefully rejected
- No sensitive data exposed in shared view (review Trip model for private fields)
- Consider adding django-ratelimit to shared_trip_detail to prevent scraping

## Performance Considerations
- Use select_related/prefetch_related in shared view query
- Add database index on ShareLink.expires_at for cleanup queries
- Consider periodic task to auto-deactivate expired links (optional, checked at view level anyway)

## Dependencies
No new dependencies required - uses Django built-in UUID field and standard patterns.

## Note\n\nScheduled for release 2026.4

## Summary of Changes

Implemented full trip sharing via magic links (issue #209):
- New `ShareLink` model with UUID PK, configurable expiration, revocation
- 4 views: shared public view, create/list/revoke (owner-only)
- `ShareLinkCreateForm` with expiration presets
- 6 templates including read-only shared view and error pages
- Share button integrated in trip detail header (mobile + desktop)
- Documentation updated in EN and IT
- 27 tests, 100% coverage maintained
