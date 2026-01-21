# Experiences

Experiences are activities, attractions, and things you plan to do during your trip. They represent the memorable moments that make your journey special.

## What is an Experience?

An **Experience** is any planned activity during your trip, such as:

- Museum visits
- Tours and guided walks
- Park visits
- Outdoor activities
- Sports and recreation
- Shows and performances
- Shopping
- Any other attraction or activity

## Creating an Experience

### From Day View

1. Navigate to a specific day
2. Click **Add Experience**
3. Fill in the experience details
4. Click **Save**

### From Trip Overview

1. Find the day section
2. Click **Add Experience**
3. Complete the form
4. Save

## Experience Fields

### Required Fields

**Name**
- The activity or attraction name
- Example: "Colosseum Tour", "Louvre Museum", "Seine River Cruise"
- Max 100 characters

**Start Time**
- When the experience begins
- Example: 09:30, 14:00, 16:30
- Used for timeline ordering and overlap detection

**End Time**
- When the experience ends
- Must be after start time
- Example: 11:30, 16:00, 18:30
- Duration is automatically calculated

**Experience Type**
- Category of the experience
- Options:
  - **Museum** - Museums, galleries, exhibitions
  - **Park** - Parks, gardens, outdoor spaces
  - **Walk** - Walking tours, self-guided walks
  - **Sport** - Sports activities, outdoor adventures
  - **Other** - Everything else

### Optional Fields

**Address**
- Location of the experience
- Example: "Piazza del Colosseo, 1, 00184 Rome, Italy"
- Used for geocoding and map display
- Max 200 characters

**City**
- City name
- Auto-populated during geocoding
- Max 100 characters

**Notes**
- Additional information
- Example: "Skip-the-line ticket. Meeting point: main entrance. Bring ID for student discount."
- Max 500 characters

**Confirmation Number**
- Booking reference
- Example: "TOUR123456", "COL202503141600"

**Price**
- Cost of the experience (if applicable)
- Example: "25€", "$50", "Free with city pass"

**Day**
- Which day this experience occurs
- Can be left blank to create an "unpaired" experience

## Experience Types

### Museum
- Art galleries
- History museums
- Science centers
- Exhibitions
- Cultural sites

**Examples**:
- "Vatican Museums and Sistine Chapel"
- "British Museum"
- "MoMA - Modern Art Exhibition"

### Park
- National parks
- City parks
- Botanical gardens
- Nature reserves
- Outdoor viewpoints

**Examples**:
- "Central Park Picnic"
- "Villa Borghese Gardens"
- "Yosemite Hiking Trail"

### Walk
- Walking tours (guided or self-guided)
- Historic walks
- Architecture tours
- Neighborhood explorations

**Examples**:
- "Trevi Fountain and Spanish Steps Walk"
- "Free Walking Tour - Old Town"
- "Street Art Tour - Brooklyn"

### Sport
- Hiking
- Cycling
- Water sports
- Skiing/snowboarding
- Adventure activities

**Examples**:
- "Mountain Bike Tour"
- "Snorkeling Trip"
- "Beach Volleyball"

### Other
- Shopping
- Shows/performances
- Classes/workshops
- Spa/wellness
- Anything not fitting other categories

**Examples**:
- "Opera at La Scala"
- "Cooking Class - Traditional Pasta"
- "Souk Shopping"

## Time Management

### Duration Calculation

Duration is automatically calculated from start and end times:

```
Start Time: 14:00
End Time: 16:30
Duration: 2 hours 30 minutes
```

### Time Overlaps

The system detects when experiences overlap with other events:

!!! warning "Overlap Detected"
    Experience at 16:00-18:00 overlaps with Meal at 17:30

**Common overlaps**:
- Experience runs into meal reservation
- Back-to-back experiences without travel time
- Experience conflicts with transfer times

**Solutions**:
- Adjust start/end times
- Reorder events
- Split longer experiences into multiple sessions
- Leave buffer time between events

### Planning Realistic Durations

✅ **Good practice**:
- Museum visit: 2-3 hours
- Walking tour: 2-4 hours
- Park visit: 1-2 hours
- Quick shopping: 1 hour
- Show/performance: Actual duration + 30 min buffer

❌ **Over-optimistic**:
- Major museum: 30 minutes (too short)
- Walking tour: 6 hours without breaks
- Back-to-back without travel time

## Location and Maps

### Geocoding

Enter a complete address to enable:
- Map pin display
- Distance calculations
- Nearby event grouping
- Travel time estimates

**Best address format**:
```
Piazza del Colosseo, 1
00184 Rome, Italy
```

### Viewing on Map

Experiences appear on:
- Day timeline maps
- Trip overview maps
- Location clustering (multiple events in same area)

!!! tip "Group Nearby Experiences"
    Plan experiences in the same neighborhood together to minimize travel time.

## Google Places Enrichment

Auto-fill experience details using Google Places.

### How to Enrich

1. Create an experience with a valid address
2. Click **Enrich** button
3. System searches Google Places
4. Select the correct result
5. Details auto-populate:
   - Official website
   - Phone number
   - Opening hours
   - Place ID

### When to Use Enrichment

✅ **Good for**:
- Popular attractions with Google listings
- Museums with official websites
- Verified businesses
- Places with specific hours

❌ **Not useful for**:
- Self-guided walks
- General outdoor activities
- Events without fixed locations
- Unlisted venues

## Managing Experiences

### Editing an Experience

1. Click on the experience card
2. Click **Edit**
3. Modify any fields
4. Click **Save**

### Deleting an Experience

1. Click on the experience card
2. Click **Delete**
3. Confirm deletion

!!! warning
    Deletion is permanent and cannot be undone.

### Moving to Another Day

1. Edit the experience
2. Change the **Day** field
3. Save

The experience moves to the selected day.

### Creating Unpaired Experiences

Sometimes you want to plan activities without assigning them to a specific day:

1. Create an experience
2. Leave **Day** field blank or set to "None"
3. Save

The experience appears in the "Unpaired Events" section. Assign it to a day later when you finalize your schedule.

## Best Practices

### Research and Planning

✅ **Before adding**:
- Check opening hours
- Verify if booking required
- Read reviews
- Check location on map
- Confirm admission prices

### Adding Complete Information

**Good example**:
```
Name: Colosseum and Roman Forum Tour
Type: Museum
Time: 09:00 - 12:30
Address: Piazza del Colosseo, 1, 00184 Rome, Italy
Notes: Skip-the-line combo ticket. Meeting point: main entrance.
       Includes audio guide. Wear comfortable shoes. Bring water.
Confirmation: COL-TOUR-2025-0314
```

**Incomplete example** (harder to use):
```
Name: Colosseum
Type: Museum
Time: 09:00 - 10:00
```

### Using Notes Effectively

Great notes include:
- Meeting point details
- What to bring
- Special instructions
- Accessibility information
- Dress code
- Student/senior discounts
- Cancellation policy

**Example**:
```
Meeting point: Main gate, look for red umbrella guide.
Bring: Passport for student discount, water bottle, sunscreen.
Note: First Sunday of month is free entry but very crowded.
Alternative: Book Thursday evening for fewer crowds.
```

### Balancing Your Day

Don't over-schedule:

❌ **Too packed**:
```
08:00-10:00 Museum A
10:30-12:30 Museum B
13:00-15:00 Museum C
15:30-17:30 Museum D
18:00-20:00 Museum E
```

✅ **Well-balanced**:
```
09:00-12:00 Museum A (major attraction)
12:00-13:30 Lunch break
14:00-16:00 Walking tour
16:00-17:00 Free time / café
19:00 Dinner
```

## Special Scenarios

### All-Day Experiences

For full-day activities:
- Set start time: 09:00
- Set end time: 18:00
- Note: "Full day tour with lunch included"

### Multi-Part Experiences

If an experience has multiple sessions:

**Option 1**: Create one long experience
```
Name: Guided City Tour (Morning & Afternoon)
Time: 09:00 - 17:00
Notes: Lunch break 12:00-13:00 (not included)
```

**Option 2**: Create separate experiences
```
Experience 1: City Tour - Morning Session (09:00-12:00)
Experience 2: City Tour - Afternoon Session (13:00-17:00)
```

### Weather-Dependent Activities

Add contingency notes:
```
Notes: Outdoor activity. Check weather forecast.
       Backup: Visit museum if raining (see Unpaired Events)
```

### Flexible Timing

For experiences without strict times:
```
Name: Explore Montmartre Neighborhood
Time: 14:00 - 17:00 (approximate)
Notes: Self-guided exploration. No fixed schedule.
       Visit Sacré-Cœur anytime before 18:00.
```

## Frequently Asked Questions

### Can I have multiple experiences at the same time?

Yes, but the system will warn you about time overlaps. This might be intentional (group splitting up) or an error (need to reschedule).

### How do I mark an experience as completed?

Currently, there's no "completed" status. This feature is planned for future releases.

### Can I add photos to an experience?

Photo attachments for events are planned for a future release.

### Can I duplicate an experience?

No built-in duplicate feature yet. You'll need to create a new experience manually.

### Can I set recurring experiences?

No, each experience must be created individually. If you have daily activities (e.g., morning run), create one for each day.

### How do I handle reservations?

Add reservation details in:
- Confirmation Number field
- Notes field (time, confirmation email, etc.)
- Links section (add reservation URL)

### What if I don't know the exact time yet?

Set approximate times and add a note:
```
Notes: Time TBD - will confirm 1 day before
```

Update the time once confirmed.

### Can I link experiences together?

Not directly. Use notes to reference related experiences:
```
Notes: Part 1 of Vatican tour. See also "Sistine Chapel" (Day 2)
```

## Related Guides

- [Days](days.md) - Understanding day organization
- [Meals](meals.md) - Adding restaurant reservations
- [Transfers](transfers.md) - Travel between experiences
- [Trips](trips.md) - Overall trip management

---

**Next**: Learn about [adding meals to your itinerary](meals.md)
