# Your First Trip - Complete Tutorial

This comprehensive tutorial will walk you through creating your first complete trip in Organize It. We'll create a 3-day weekend trip to Rome as an example.

## Prerequisites

Before starting this tutorial, make sure you:

- Have installed Organize It (see [Installation Guide](installation.md))
- Have created an account and are logged in
- Have the development server running

## Tutorial Overview

In this tutorial, you will:

1. Create a new trip to Rome
2. Add a hotel stay
3. Add arrival and departure transfers
4. Add experiences (activities)
5. Add meals (restaurants)
6. View and organize your complete itinerary

Let's get started!

## Step 1: Create a New Trip

### 1.1 Navigate to Trip Creation

From the homepage, click the **Create New Trip** button.

### 1.2 Fill in Trip Details

Enter the following information:

- **Name**: "Rome Weekend Getaway"
- **Destination**: "Rome, Italy"
- **Start Date**: Choose a Friday (e.g., March 14, 2025)
- **End Date**: Choose a Sunday (e.g., March 16, 2025)
- **Description**: "A wonderful weekend exploring ancient Rome"

### 1.3 Add a Cover Image

You have two options:

**Option A: Upload Your Own Image**

Click **Upload Image** and select a photo from your computer.

**Option B: Search Unsplash (Recommended)**

1. Click **Search Unsplash**
2. Type "rome colosseum" in the search box
3. Click on an image you like
4. Click **Use This Photo**

### 1.4 Save the Trip

Click **Save** to create your trip.

!!! success
    Your trip is now created! Notice that 3 days (Friday, Saturday, Sunday) have been automatically generated.

## Step 2: Add Your Accommodation

### 2.1 Navigate to the First Day

Click on **Day 1 (Friday, March 14)** to open the day view.

### 2.2 Create a Stay

1. Click **Add Stay**
2. Fill in the stay details:
   - **Name**: "Hotel Forum Roma"
   - **Address**: "Via Tor de' Conti, 25, 00184 Rome, Italy"
   - **Start Day**: Day 1 (Friday)
   - **End Day**: Day 3 (Sunday)
   - **Check-in Time**: 15:00
   - **Check-out Time**: 11:00
   - **Confirmation Number**: "HTLFORUM123" (optional)
   - **Notes**: "Near the Colosseum. Free breakfast included."

3. Click **Save**

!!! info "Multi-Day Stays"
    Since this stay spans all 3 days, it will appear on Day 1, Day 2, and Day 3.

### 2.3 Enrich with Google Places (Optional)

If you have a Google Places API key configured:

1. Click **Enrich** next to the stay
2. The system will automatically fetch:
   - Website URL
   - Phone number
   - Opening hours
   - Additional details

## Step 3: Add Arrival Transfer

### 3.1 Create the Arrival Transfer

1. From Day 1, click **Add Transfer**
2. Select **Arrival** as the transfer type
3. Fill in details:
   - **Transport Mode**: Flight
   - **Origin**: "London Heathrow (LHR)"
   - **Destination**: "Rome Fiumicino (FCO)"
   - **Departure Time**: 08:00
   - **Arrival Time**: 11:30
   - **Confirmation Number**: "BA123456"
   - **Notes**: "British Airways BA500. Seat 12A."

4. Click **Save**

### 3.2 Add Airport to Hotel Transfer

1. Click **Add Transfer** again
2. Select **Simple Transfer**
3. Fill in details:
   - **Transport Mode**: Train
   - **Origin**: "Fiumicino Airport"
   - **Destination**: "Hotel Forum Roma"
   - **Departure Time**: 12:00
   - **Arrival Time**: 13:00
   - **Notes**: "Leonardo Express to Termini, then metro to Colosseo"

4. Click **Save**

## Step 4: Add Experiences (Activities)

### 4.1 Friday Afternoon - Colosseum Visit

1. Click **Add Experience**
2. Fill in details:
   - **Name**: "Colosseum Tour"
   - **Category**: Museum/Attraction
   - **Start Time**: 16:00
   - **Duration**: 2 hours
   - **Address**: "Piazza del Colosseo, 1, 00184 Rome"
   - **Price**: 25€ (optional)
   - **Confirmation**: "COL202503141600" (optional)
   - **Notes**: "Guided tour. Skip-the-line ticket. Meeting point: main entrance"

3. Click **Save**

### 4.2 Saturday Morning - Roman Forum

1. Navigate to **Day 2 (Saturday)**
2. Click **Add Experience**
3. Fill in details:
   - **Name**: "Roman Forum and Palatine Hill"
   - **Category**: Museum/Attraction
   - **Start Time**: 09:30
   - **Duration**: 3 hours
   - **Address**: "Via della Salara Vecchia, 5/6, 00186 Rome"
   - **Notes**: "Included in Colosseum ticket. Wear comfortable shoes!"

4. Click **Save**

### 4.3 Saturday Afternoon - Trevi Fountain Walk

1. Click **Add Experience**
2. Fill in details:
   - **Name**: "Trevi Fountain and Spanish Steps Walk"
   - **Category**: Walk/Exploration
   - **Start Time**: 15:00
   - **Duration**: 2 hours
   - **Notes**: "Bring coins for the fountain!"

3. Click **Save**

### 4.4 Sunday Morning - Vatican Museums

1. Navigate to **Day 3 (Sunday)**
2. Click **Add Experience**
3. Fill in details:
   - **Name**: "Vatican Museums and Sistine Chapel"
   - **Category**: Museum/Attraction
   - **Start Time**: 09:00
   - **Duration**: 3.5 hours
   - **Address**: "Viale Vaticano, 00165 Rome"
   - **Price**: 17€
   - **Notes**: "Book in advance. Last Sunday of month is free but crowded."

4. Click **Save**

## Step 5: Add Meals

### 5.1 Friday Dinner

1. Navigate to **Day 1 (Friday)**
2. Click **Add Meal**
3. Fill in details:
   - **Name**: "Trattoria da Enzo"
   - **Cuisine Type**: Italian
   - **Meal Type**: Dinner
   - **Start Time**: 19:30
   - **Address**: "Via dei Vascellari, 29, 00153 Rome"
   - **Reservation**: Yes
   - **Notes**: "Traditional Roman cuisine. Try the cacio e pepe!"

4. Click **Save**

### 5.2 Saturday Lunch

1. Navigate to **Day 2 (Saturday)**
2. Click **Add Meal**
3. Fill in details:
   - **Name**: "Roscioli"
   - **Cuisine Type**: Italian/Deli
   - **Meal Type**: Lunch
   - **Start Time**: 13:00
   - **Address**: "Via dei Giubbonari, 21, 00186 Rome"
   - **Notes**: "Famous bakery and deli. Try the pizza bianca!"

4. Click **Save**

### 5.3 Saturday Dinner

1. Click **Add Meal**
2. Fill in details:
   - **Name**: "La Pergola"
   - **Cuisine Type**: Fine Dining
   - **Meal Type**: Dinner
   - **Start Time**: 20:00
   - **Address**: "Via Alberto Cadlolo, 101, 00136 Rome"
   - **Reservation**: Yes
   - **Confirmation**: "LP20250315" (optional)
   - **Notes**: "3 Michelin stars. Dress code: elegant. Reserve well in advance."

4. Click **Save**

### 5.4 Sunday Lunch

1. Navigate to **Day 3 (Sunday)**
2. Click **Add Meal**
3. Fill in details:
   - **Name**: "Pizzarium"
   - **Cuisine Type**: Pizza
   - **Meal Type**: Lunch
   - **Start Time**: 13:30
   - **Address**: "Via della Meloria, 43, 00136 Rome"
   - **Notes**: "Best pizza al taglio in Rome. Near Vatican."

4. Click **Save**

## Step 6: Add Departure Transfer

### 6.1 Hotel to Airport Transfer

1. Still on **Day 3 (Sunday)**
2. Click **Add Transfer**
3. Select **Simple Transfer**
4. Fill in details:
   - **Transport Mode**: Taxi
   - **Origin**: "Hotel Forum Roma"
   - **Destination**: "Rome Fiumicino Airport"
   - **Departure Time**: 15:00
   - **Arrival Time**: 16:00
   - **Notes**: "Pre-booked taxi. Approx 50€ fixed rate."

5. Click **Save**

### 6.2 Flight Home

1. Click **Add Transfer**
2. Select **Departure**
3. Fill in details:
   - **Transport Mode**: Flight
   - **Origin**: "Rome Fiumicino (FCO)"
   - **Destination**: "London Heathrow (LHR)"
   - **Departure Time**: 18:00
   - **Arrival Time**: 19:45
   - **Confirmation**: "BA234567"
   - **Notes**: "British Airways BA501. Seat 15C."

4. Click **Save**

## Step 7: Review Your Itinerary

### 7.1 View the Complete Trip

1. Click on the trip name to go back to the trip overview
2. You should now see:
   - 3 days with automatically generated dates
   - 1 stay spanning all 3 days
   - Multiple experiences, meals, and transfers organized by day
   - Events displayed in chronological order

### 7.2 Check for Overlaps

The system automatically detects time conflicts. If you see a warning icon next to an event, it means there's a time overlap with another event on the same day.

!!! warning "Time Conflicts"
    Review any overlapping events and adjust times as needed to avoid conflicts.

### 7.3 View Day Details

Click on any day to see:

- All events for that day in timeline format
- The accommodation (if any)
- Event details with expand/collapse functionality

## Step 8: Make Edits and Adjustments

### 8.1 Edit an Event

1. Click on any event card
2. Click the **Edit** button
3. Make your changes
4. Click **Save**

### 8.2 Delete an Event

1. Click on any event card
2. Click the **Delete** button
3. Confirm deletion

### 8.3 Move an Event to Another Day

1. Edit the event
2. Change the **Day** field to a different day
3. Save

!!! tip "Unpaired Events"
    You can also leave an event unpaired (no day assigned) and assign it later.

## Step 9: Add Trip Links (Optional)

### 9.1 Add Useful Links

1. Go to the trip overview
2. Click **Add Link**
3. Add links such as:
   - Flight confirmations
   - Hotel booking confirmations
   - Restaurant reservation emails
   - Tour booking pages
   - Travel guides

Example:
- **Title**: "Colosseum Ticket"
- **URL**: "https://www.coopculture.it/..."
- **Description**: "Skip-the-line ticket confirmation"

## Congratulations!

You've successfully created your first complete trip in Organize It! You now know how to:

- ✅ Create trips with dates and images
- ✅ Add multi-day accommodations
- ✅ Add arrival and departure transfers
- ✅ Plan experiences and activities
- ✅ Add restaurant reservations
- ✅ View your complete itinerary organized by day
- ✅ Edit and manage events

## What's Next?

Explore more features:

- **Trip Statuses**: Learn how trips automatically update status (see [Trips Guide](../user-guide/trips.md))
- **Google Places Integration**: Auto-fill location details (see [Experiences Guide](../user-guide/experiences.md))
- **Maps Integration**: View events on a map (see [Transfers Guide](../user-guide/transfers.md))
- **Favorites**: Mark your favorite trips with a star

## Tips for Better Trip Planning

!!! tip "Plan in Stages"
    1. Create the trip skeleton (dates, accommodation)
    2. Add major transfers (flights, trains)
    3. Add must-see experiences
    4. Fill in meals and other activities
    5. Review and adjust for timing

!!! tip "Use Notes"
    Add detailed notes to events:
    - Confirmation numbers
    - Booking references
    - Special instructions
    - Tips and recommendations

!!! tip "Check Times"
    Always verify:
    - Event durations are realistic
    - Travel time between locations
    - Opening hours of attractions
    - Restaurant reservation times

!!! tip "Leave Buffer Time"
    Don't over-schedule! Leave gaps for:
    - Unexpected delays
    - Spontaneous discoveries
    - Rest and relaxation

Happy travels! ✈️🏛️🍝
