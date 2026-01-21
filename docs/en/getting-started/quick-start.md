# Quick Start Guide

Get up and running with Organize It in 5 minutes!

## What is Organize It?

Organize It is a web application designed to help you plan and organize your trips. Whether you're planning a weekend getaway or a month-long adventure, Organize It helps you keep track of:

- **Accommodations** (Stays)
- **Activities** (Experiences)
- **Restaurants** (Meals)
- **Transportation** (Transfers)
- **Important links and notes**

## Core Concepts

### Trips

A **Trip** is the main container for your travel plans. Each trip has:

- Start and end dates
- A cover image
- A collection of days (auto-generated from dates)
- Events organized by day

### Days

**Days** are automatically created based on your trip dates. Each day can contain:

- Multiple events (experiences, meals, transfers)
- One accommodation (stay)

### Events

**Events** are the activities in your itinerary. There are three types:

1. **Stays** - Hotels, apartments, hostels
2. **Experiences** - Museums, tours, walks, attractions
3. **Meals** - Restaurants, cafes, food experiences
4. **Transfers** - Flights, trains, car rentals, moving between locations

## Your First Trip in 5 Minutes

### Step 1: Create an Account

1. Navigate to [http://localhost:8000](http://localhost:8000)
2. Click **Sign Up**
3. Enter your email and password
4. Verify your email (in development, check the console)
5. Log in

### Step 2: Create Your First Trip

1. Click **Create New Trip**
2. Fill in the details:
   - Trip name (e.g., "Rome Weekend")
   - Destination (e.g., "Rome, Italy")
   - Start date
   - End date
   - Optional: Add a cover image or search Unsplash
3. Click **Save**

Days will be automatically created for each date in your trip!

### Step 3: Add a Stay

1. Navigate to your trip
2. Click on a day
3. Click **Add Stay**
4. Enter accommodation details:
   - Name (e.g., "Hotel Colosseo")
   - Address
   - Check-in time
   - Check-out time
5. Click **Save**

!!! tip
    Stays can span multiple consecutive days. Just set the start and end days!

### Step 4: Add Activities

1. Click **Add Experience**
2. Enter details:
   - Name (e.g., "Visit Colosseum")
   - Time
   - Duration
   - Location
   - Notes
3. Click **Save**

Repeat for meals and other activities!

### Step 5: Add Transportation

1. Click **Add Transfer**
2. Choose the transfer type:
   - **Arrival** - Getting to your first stay
   - **Departure** - Leaving your last stay
   - **Stay Transfer** - Moving between accommodations
   - **Simple Transfer** - Moving between events
3. Fill in details:
   - Transport mode (flight, train, car, etc.)
   - Departure and arrival times
   - Confirmation number
4. Click **Save**

### Step 6: View Your Itinerary

Your trip is now organized! You can:

- View all events in a timeline
- See events organized by day
- Click on any event to view full details
- Edit or delete events as needed
- Mark favorite trips with a star

## What's Next?

Now that you have your first trip set up, explore:

- [Your First Trip Tutorial](first-trip.md) - A detailed walkthrough
- [User Guide](../user-guide/trips.md) - In-depth documentation
- [FAQ](../faq.md) - Common questions

## Tips & Tricks

!!! tip "Use Google Places"
    Enable Google Places API to auto-fill restaurant and attraction details

!!! tip "Unsplash Integration"
    Search Unsplash for beautiful cover images directly from the trip form

!!! tip "Trip Statuses"
    Trips automatically update their status based on dates:
    - **Not Started** - Future trips
    - **Impending** - Starting within 30 days
    - **In Progress** - Currently happening
    - **Completed** - Past trips
    - **Archived** - Manually archived

!!! tip "Unpaired Events"
    You can create events without assigning them to a day. They'll appear in the "Unpaired Events" section and can be assigned later.

## Need Help?

- Check the [FAQ](../faq.md) for common questions
- Read the detailed [User Guide](../user-guide/trips.md)
- Report issues on [GitHub](https://github.com/applewebbo/organize_it/issues)

Happy planning! ✈️
