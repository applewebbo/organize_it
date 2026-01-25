---
# organize_it-pl6o
title: Home Page for authenticated user without trips
status: completed
type: feature
priority: normal
created_at: 2026-01-19T13:20:35Z
updated_at: 2026-01-25T06:40:20Z
parent: organize_it-oor7
---

## Description
Improve the home page experience for authenticated users who haven't created any trips yet.

### Current State
The current implementation shows a simple message: "You have no trips yet!" when an authenticated user has no trips.

### Desired State
**Before first trip is created:**
- Call to action to create the first trip
- Quick guide explaining key concepts of the flow (transfers, stays, experiences, meals)
- Link to deeper documentation

**After first trip is created:**
- Quick links to trips (already implemented via 'Other Trips' section)
- Link to deeper documentation

## Checklist

### Phase 1: Create the Empty State Component
- [x] Create a new Cotton component `templates/cotton/empty-state.html` for reusable empty state UI
- [x] Design a visually appealing hero section with:
  - Illustrative icon or image (using Phosphor icons or a static image)
  - Welcoming headline
  - Encouraging subtext
  - Prominent CTA button to create first trip

### Phase 2: Create Quick Guide Component
- [x] Create `templates/cotton/quick-guide.html` component with collapsible sections
- [x] Add section for **Trips**: explain what a trip is and how to create one
- [x] Add section for **Days**: auto-generated from trip dates
- [x] Add section for **Stays**: accommodations (hotels, apartments, etc.)
- [x] Add section for **Experiences**: activities, museums, tours
- [x] Add section for **Meals**: restaurants and food experiences
- [x] Add section for **Transfers**: movements between locations (arrival, departure, inter-event)
- [x] Use Alpine.js for accordion/collapsible behavior
- [x] Add appropriate Phosphor icons for each concept

### Phase 3: Integrate Empty State in Home Page
- [x] Modify `templates/includes/auth-index.html` to use the new empty state component
- [x] Replace the simple "You have no trips yet!" message with the new rich component
- [x] Ensure proper responsive design (mobile-first)

### Phase 4: Add Documentation Link
- [x] Decide where to host deeper documentation (GitHub wiki, separate docs page, or inline)
- [x] Add a "Learn more" or "Read documentation" link in the quick guide
- [x] If needed, create a simple documentation page template

### Phase 5: Add Quick Guide Toggle for Users with Trips
- [x] Add an optional "Show Guide" button in the home page for users who already have trips
- [x] Store user preference (show/hide guide) - consider using session or Profile model
- [x] Ensure guide can be dismissed and re-shown

### Phase 6: Testing
- [x] Write tests for the home page empty state rendering
- [x] Test that CTA button redirects to trip creation
- [x] Test responsive design on different screen sizes
- [x] Ensure 100% code coverage is maintained

### Phase 7: Internationalization
- [x] Wrap all new strings in `{% trans %}` tags
- [x] Note: do NOT edit .po files - leave for manual translation

## Technical Notes

### Files to modify:
- `templates/includes/auth-index.html` - main template modification
- `templates/cotton/empty-state.html` - new component (create)
- `templates/cotton/quick-guide.html` - new component (create)
- `tests/test_views.py` or create new `tests/test_home_page.py` - tests

### Dependencies:
- Phosphor icons (already available)
- Alpine.js (already available)
- DaisyUI components (already available)

### Related files (reference only):
- `trips/views.py:61-68` - home view
- `trips/utils.py:52-110` - get_trips function
- `templates/trips/index.html` - main index template

## GitHub Issue
This bean implements GitHub Issue #227
