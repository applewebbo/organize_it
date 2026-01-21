# Frequently Asked Questions (FAQ)

Common questions and answers about using Organize It.

## General Questions

### What is Organize It?

Organize It is a web application designed to help you plan and organize trips. It allows you to:

- Create detailed trip itineraries
- Manage accommodations (stays)
- Plan activities and attractions (experiences)
- Schedule restaurant reservations (meals)
- Track transportation (transfers)
- Keep all trip information in one place

### Is Organize It free?

Yes, Organize It is currently free to use. There are no subscription fees or premium tiers.

### What makes Organize It different from other trip planners?

Organize It focuses on:

- **Day-by-day organization**: Events are automatically organized by day
- **Automatic status updates**: Trip statuses update based on dates
- **Time conflict detection**: Warns when events overlap
- **Multi-day stays**: Accommodations can span multiple days
- **Flexible event assignment**: Create events before assigning to specific days
- **Beautiful UI**: Clean, modern interface built with TailwindCSS

### Can I use Organize It for business trips?

Yes! Organize It works for any type of trip:

- Leisure vacations
- Business trips
- Weekend getaways
- Multi-city tours
- Road trips
- Conferences and events

### How many trips can I create?

There is no limit on the number of trips you can create.

### Can I use Organize It offline?

Currently, Organize It requires an internet connection. Offline support is planned for a future release.

## Account Questions

### Do I need an account to use Organize It?

Yes, you need to create an account to use Organize It. This ensures your trips are saved securely.

### How do I create an account?

1. Click **Sign Up**
2. Enter your email address
3. Create a password (minimum 8 characters)
4. Verify your email
5. Log in

### Do you support social login (Google, Facebook)?

Currently, only email/password authentication is supported. Social login may be added in a future release.

### I didn't receive the verification email. What should I do?

Check:

- **Spam/Junk folder**: Verification emails sometimes get filtered
- **Email address**: Ensure you typed it correctly
- **Wait a few minutes**: Email delivery can be delayed

If still missing, try:
- Request a new verification email (if available)
- Contact support for assistance

### Can I change my email address?

Email address changes are currently not supported through the UI. Contact support if you need to change your email.

### Can I change my password?

Yes:

1. Log in to your account
2. Go to **Profile** or **Account Settings**
3. Click **Change Password**
4. Enter current and new password
5. Save

### How do I delete my account?

Account deletion is currently not available through the UI. Contact support to request account deletion.

### Is my data secure?

Yes. Organize It uses:

- Encrypted password storage
- Secure HTTPS connections
- Django security best practices
- Regular security updates

## Trip Questions

### How do I create a trip?

1. Click **Create New Trip** from the homepage
2. Fill in:
   - Trip name
   - Destination
   - Start and end dates
   - Optional: Description, cover image
3. Click **Save**

Days are automatically generated based on your dates.

### Can I create trips without specific dates?

No, start and end dates are required. Days are auto-generated from these dates, and the status system depends on them.

### Can I edit a trip after creating it?

Yes:

1. Navigate to the trip
2. Click **Edit Trip**
3. Modify any fields
4. Save

!!! info
    Changing dates will regenerate days. Events will be reassigned to the closest matching day.

### What happens if I change trip dates?

**Extending the trip**: New days are created.

**Shortening the trip**: Extra days are deleted. Events on deleted days become "unpaired."

**Changing start date**: All days shift. Events remain on the same day number.

### Can I delete a trip?

Yes:

1. Go to the trip detail page
2. Click **Delete Trip**
3. Confirm deletion

!!! danger
    Deleting a trip permanently removes all days, events, and stays. This cannot be undone.

### How do trip statuses work?

Statuses update automatically based on dates:

- **Not Started**: Start date is more than 7 days away
- **Impending**: Start date is within 7 days
- **In Progress**: Between start and end dates
- **Completed**: After end date
- **Archived**: Manually archived (remains in this status)

### How do I archive a trip?

1. Navigate to the trip
2. Click **Archive**
3. The trip status becomes "Archived"

Archived trips are hidden from the main trip list. Use the filter to view archived trips.

### Can I share trips with others?

Trip sharing is not currently supported but is planned for a future release.

### Can I duplicate a trip?

Trip duplication is not currently supported but is planned for a future release.

### Can I export my trip?

Trip export (PDF, ICS calendar) is planned for a future release.

### Can I add co-travelers to a trip?

Multi-user trip collaboration is planned for a future release.

### How do I add a cover image?

**Upload your own**:
1. Edit trip
2. Click **Upload Image**
3. Select image file
4. Save

**Use Unsplash**:
1. Edit trip
2. Click **Search Unsplash**
3. Search for images
4. Select an image
5. Click **Use This Photo**
6. Save

### What image formats are supported?

Supported formats: JPG, PNG, WebP

Maximum file size: 2MB

Recommended aspect ratio: 16:9 or 4:3 (landscape)

## Event Questions

### What are "unpaired events"?

Unpaired events are events (experiences, meals, transfers) that haven't been assigned to a specific day.

**Uses**:
- Planning activities before finalizing schedule
- Creating a wishlist of options
- Storing backup plans

**Assigning to a day**:
1. Edit the event
2. Select a day
3. Save

### Can I move an event to a different day?

Yes:

1. Click on the event
2. Click **Edit**
3. Change the **Day** field
4. Save

### What happens when events overlap?

The system detects time conflicts and displays a warning. Review overlapping events and:

- Adjust times
- Reorder events
- Remove/delete conflicts

### Can I create recurring events?

No, each event must be created individually. Recurring events are not currently supported.

### How do I delete an event?

1. Click on the event
2. Click **Delete**
3. Confirm

!!! warning
    Deletion is permanent.

### Can I add photos to events?

Event photo attachments are planned for a future release.

### Can I attach files or documents?

Direct file attachments are not currently supported. You can:

- Add links to confirmation emails (Trip Links)
- Store confirmation numbers in event fields
- Add URLs in notes

### Can I mark events as completed?

Event completion tracking is planned for a future release.

### How do I reorder events within a day?

Events are automatically ordered by start time. To reorder:

1. Edit event times
2. Adjust start time to desired position
3. Save

### Can I swap event times?

Currently, you need to manually edit both events to swap times. A swap feature is planned for a future release.

## Stay Questions

### Can I have multiple stays on the same day?

No, each day can have only one stay. If you're changing accommodations mid-day, assign one stay to that day and the next stay to the following day.

### How do multi-day stays work?

Set **Start Day** and **End Day**. The stay appears on all days in that range.

Example:
- Start Day: Day 1
- End Day: Day 3
- Result: Stay appears on Days 1, 2, and 3

### Can I change the duration of a stay?

Yes:

1. Edit the stay
2. Change **Start Day** or **End Day**
3. Save

The stay automatically updates to appear on the correct days.

### What is Google Places enrichment?

Enrichment auto-fills stay details using Google Places API:

- Official website
- Phone number
- Opening hours
- Additional data

**To enrich**:
1. Create/edit stay with valid address
2. Click **Enrich**
3. Select correct result
4. Data auto-fills

### Why isn't my address geocoding correctly?

Try:

- Adding complete address (street number, postal code, country)
- Using official format from Google Maps
- Checking for typos
- Using English transliterations for non-Latin addresses

## Transfer Questions

### What are the different types of transfers?

1. **Main Transfers**: Arrival and departure (flights, trains to/from destination)
2. **Stay Transfers**: Moving between accommodations
3. **Simple Transfers**: Moving between events on the same day

### Do I need to add transfers for every movement?

No. Only add transfers when:

- Different locations/neighborhoods
- Specific transport planning needed
- Time/route information important

Skip for:
- Same building
- Adjacent locations
- Obvious walking routes

### How does Google Maps integration work?

Simple transfers auto-generate Google Maps URLs based on:

- Event addresses
- Selected transport mode

Click the link to open directions in Google Maps.

### Can I track multi-leg journeys?

**Option 1**: One transfer with detailed notes
```
Notes: Multi-leg journey:
       1. Rome → Florence (train, 2h)
       2. Florence stopover (1h)
       3. Florence → Venice (train, 2h)
```

**Option 2**: Separate events for each leg (if overnight stays between)

## Technical Questions

### What browsers are supported?

Organize It works best on modern browsers:

✅ **Fully supported**:
- Chrome 90+
- Firefox 90+
- Safari 14+
- Edge 90+

⚠️ **May have issues**:
- Internet Explorer (not supported)
- Older browser versions

### Is there a mobile app?

Currently, there is no native mobile app. However, the web interface is mobile-responsive and works on smartphones and tablets.

A dedicated mobile app may be developed in the future.

### Can I use Organize It on my phone?

Yes! The web interface is mobile-responsive:

1. Open your mobile browser
2. Navigate to the Organize It URL
3. Log in
4. Use normally

**Tip**: Add to home screen for app-like experience:
- **iOS**: Safari → Share → Add to Home Screen
- **Android**: Chrome → Menu → Add to Home Screen

### Does Organize It work offline?

Currently, no. An internet connection is required.

Offline support (Progressive Web App features) is planned for a future release.

### What happens to my data if the server goes down?

Your data is safely stored in a database and backed up regularly. Temporary outages don't affect your data.

### Can I export my data?

Data export is planned for a future release. Export formats will likely include:

- JSON (all data)
- PDF (printable itinerary)
- ICS (calendar format)

### How do I report a bug?

Report bugs on GitHub:

1. Visit [https://github.com/applewebbo/organize_it/issues](https://github.com/applewebbo/organize_it/issues)
2. Click **New Issue**
3. Describe the bug:
   - What you did
   - What you expected
   - What actually happened
   - Screenshots if relevant
4. Submit

### How do I request a feature?

Request features on GitHub Issues:

1. Visit [https://github.com/applewebbo/organize_it/issues](https://github.com/applewebbo/organize_it/issues)
2. Click **New Issue**
3. Describe the feature:
   - What you want to do
   - Why it would be useful
   - How you envision it working
4. Submit

### Is Organize It open source?

Check the GitHub repository for license information: [https://github.com/applewebbo/organize_it](https://github.com/applewebbo/organize_it)

### Can I contribute to Organize It?

Contributions are welcome! Check the repository for:

- Contributing guidelines
- Development setup instructions
- Open issues to work on

## Privacy & Data Questions

### What data do you collect?

Organize It collects:

- **Account data**: Email, password (encrypted)
- **Trip data**: All trip, event, stay information you create
- **Usage data**: Basic analytics (if enabled)

### Do you share my data with third parties?

Your trip data is private and not shared with third parties except:

- **Mapbox**: For geocoding addresses (no personal info)
- **Google Places**: For enrichment (no personal info)
- **Unsplash**: For photo downloads (attribution requirements)

### Can other users see my trips?

No. Your trips are private and only visible to you (until sharing features are implemented).

### How long do you keep my data?

Data is retained as long as your account is active. If you delete your account, data is permanently removed.

### Can I download all my data?

Data export/download is planned for a future release.

## Troubleshooting

### I can't log in. What should I do?

Check:

1. **Email**: Ensure correct email address
2. **Password**: Verify password (case-sensitive)
3. **Caps Lock**: Ensure Caps Lock is off
4. **Browser**: Try a different browser
5. **Cookies**: Ensure cookies are enabled

If still unable to log in, use "Forgot Password" to reset.

### Events aren't appearing on the map

Possible causes:

- **No address**: Event must have a valid address
- **Geocoding failed**: Address couldn't be converted to coordinates
- **API issue**: Mapbox service temporarily unavailable

**Solution**:
- Add complete address with postal code and country
- Edit and re-save the event
- Check address format

### I can't upload an image

Check:

- **File size**: Must be under 2MB
- **File format**: Must be JPG, PNG, or WebP
- **Browser**: Try a different browser
- **Connection**: Ensure stable internet

**Solution**:
- Compress large images
- Convert to supported format
- Try Unsplash search instead

### The page isn't loading

Try:

1. Refresh the page (F5 or Cmd+R)
2. Clear browser cache
3. Try incognito/private mode
4. Check internet connection
5. Try a different browser

If the problem persists, the server may be temporarily down. Try again later or report the issue on GitHub.

## Still Have Questions?

Can't find an answer to your question?

- **Check the User Guide**: Detailed documentation for all features
- **GitHub Issues**: Search existing issues or create new one
- **Contact Support**: Email support (if available)

---

**Helpful Links**:

- [Getting Started Guide](getting-started/installation.md)
- [User Guide](user-guide/trips.md)
- [GitHub Repository](https://github.com/applewebbo/organize_it)
