# Transfers

Transfers represent all transportation during your trip - from flights and trains to walking between attractions. Organize It helps you track arrival, departure, and inter-destination movement.

## What is a Transfer?

A **Transfer** is any movement from one location to another during your trip. There are three types:

1. **Main Transfers** - Arrival and departure (flights, trains to/from destination)
2. **Stay Transfers** - Moving between different accommodations
3. **Simple Transfers** - Moving between events on the same day

## Main Transfers

Main transfers handle your journey to and from the trip destination.

### Arrival Transfer

Your journey TO the destination at the start of the trip.

**Examples**:
- Flight from London to Rome
- Train from Paris to Barcelona
- Driving from home to vacation rental

### Departure Transfer

Your journey FROM the destination at the end of the trip.

**Examples**:
- Flight from Rome back to London
- Train from Barcelona to Paris
- Driving from vacation rental back home

### Creating a Main Transfer

1. Navigate to the trip
2. Click **Add Transfer** → **Arrival** or **Departure**
3. Fill in transfer details
4. Click **Save**

### Main Transfer Fields

#### Required Fields

**Transport Type**
- Type of transportation
- Options:
  - **Plane** - Flights, air travel
  - **Train** - Rail transport
  - **Car** - Personal vehicle, rental car
  - **Other** - Bus, boat, etc.

**Direction**
- **Arrival** - Coming to the destination
- **Departure** - Leaving the destination

**Start Time** (Departure time)
- When you depart from origin
- Example: 08:00, 14:30

**End Time** (Arrival time)
- When you arrive at destination
- Example: 11:30, 18:45

#### Origin and Destination

**For Plane and Train**:
- **Origin Code** - IATA code (plane) or station ID (train)
  - Example: LHR, FCO, NYP, GCT
- **Origin Name** - Airport/station full name
  - Example: "London Heathrow", "Rome Fiumicino"
- **Destination Code** - IATA code or station ID
- **Destination Name** - Airport/station full name

**For Car and Other**:
- **Origin Address** - Full street address
- **Destination Address** - Full street address

#### Optional Fields

**Booking Reference**
- Confirmation number
- Example: "BA123456", "EUROSTAR-2025-0314"

**Ticket URL**
- Link to e-ticket or booking
- Example: "https://www.airline.com/tickets/ABC123"

**Notes**
- Additional details
- Example: "Seat 12A. Check-in opens 24h before. Baggage: 1x23kg included."

**Type-Specific Data** (JSON field for flexibility)
- Flight number (e.g., "BA500")
- Airline/company name
- Train number
- Platform information
- Terminal details

### Main Transfer Examples

#### Flight Arrival

```
Type: Plane
Direction: Arrival
Origin: LHR (London Heathrow)
Destination: FCO (Rome Fiumicino)
Departure Time: 08:00
Arrival Time: 11:30
Booking Reference: BA123456
Notes: British Airways BA500. Seat 12A. Terminal 5.
      Check-in online 24h before. 1x23kg baggage included.
Type-Specific Data:
  - flight_number: BA500
  - airline: British Airways
  - terminal: 5
```

#### Train Arrival

```
Type: Train
Direction: Arrival
Origin: Gare de Lyon (Paris)
Destination: Milano Centrale (Milan)
Departure Time: 14:15
Arrival Time: 21:25
Booking Reference: THELLO-2025-0314
Notes: Thello night train. Sleeper cabin #12. Platform 3.
Type-Specific Data:
  - train_number: TH9426
  - company: Thello
  - cabin: 12
```

#### Car Departure

```
Type: Car
Direction: Departure
Origin Address: 123 Main St, Vacation Town, CA 12345
Destination Address: 456 Home Ave, Home City, CA 54321
Departure Time: 10:00
Arrival Time: 16:00
Notes: 6-hour drive. Stop for lunch halfway. Return rental at airport.
```

## Stay Transfers

Movement between different accommodations during your trip.

### When to Use Stay Transfers

Create a stay transfer when:
- Changing hotels mid-trip
- Moving from one city to another
- Switching from hotel to vacation rental

**Example Scenario**:
```
Day 1-3: Hotel in Rome
Day 4: Travel day - Move to Florence
Day 5-7: Hotel in Florence
```

Add a stay transfer from Rome hotel to Florence hotel on Day 4.

### Creating a Stay Transfer

1. Navigate to the day when you're moving
2. Click **Add Transfer** → **Stay Transfer**
3. Select:
   - **From Stay**: Current accommodation
   - **To Stay**: Next accommodation
4. Fill in details
5. Save

### Stay Transfer Fields

**From Stay**
- The accommodation you're leaving
- Auto-populated with checkout time

**To Stay**
- The accommodation you're moving to
- Auto-populated with check-in time

**Transport Mode**
- How you're traveling
- Options:
  - **Driving** - Car, taxi, rental
  - **Walking** - On foot (short distances)
  - **Bicycling** - Bike, e-scooter
  - **Transit** - Public transportation (bus, metro, train)

**Departure Time** (optional)
- When you leave the first stay
- Often matches checkout time

**Arrival Time** (optional)
- When you reach the next stay
- Should be before check-in time

**Notes**
- Additional information
- Example: "Taxi pre-booked. €50 fixed rate. Driver: Marco +39 123 456 7890"

### Stay Transfer Example

```
From Stay: Hotel Forum Roma
To Stay: Hotel Brunelleschi (Florence)
Transport Mode: Transit
Departure Time: 11:00 (after checkout)
Arrival Time: 14:30 (before 15:00 check-in)
Notes: Train from Roma Termini to Firenze SMN.
       Freccia Rossa #9352. Booking: TRENITALIA-123456
       Metro to Termini from hotel (20 min)
       Walk from SMN to hotel (15 min)
       Total journey: ~3.5 hours
```

## Simple Transfers

Quick movements between events on the same day.

### When to Use Simple Transfers

Create simple transfers for:
- Walking between museum and restaurant
- Taxi from lunch to afternoon activity
- Metro ride between two attractions

### Creating a Simple Transfer

1. Navigate to a day
2. Click **Add Transfer** → **Simple Transfer**
3. Select:
   - **From Event**: Starting point
   - **To Event**: Destination
4. Choose transport mode
5. Add notes if needed
6. Save

### Simple Transfer Fields

**From Event**
- The event you're leaving
- Auto-populated with location

**To Event**
- The event you're going to
- Auto-populated with location

**Transport Mode**
- How you're traveling
- Options same as stay transfers:
  - Driving, Walking, Bicycling, Transit

**Notes**
- Additional information
- Example: "15-minute walk along the river. Scenic route."

### Simple Transfer Features

#### Auto-Generated Google Maps Link

Simple transfers automatically generate a Google Maps URL:
- Uses addresses from both events
- Includes selected transport mode
- Click to open directions in Google Maps

#### Visual Timeline

Simple transfers appear between events in the day timeline:

```
12:00 - Lunch at Roscioli (Meal)
    ↓ [Walking - 10 min]
14:00 - Colosseum Tour (Experience)
    ↓ [Metro - 20 min]
17:00 - Dinner at Trastevere (Meal)
```

### Simple Transfer Examples

#### Walking

```
From Event: Louvre Museum
To Event: Café de Flore (Lunch)
Transport Mode: Walking
Notes: 20-minute scenic walk along Seine.
       Cross Pont des Arts.
```

#### Metro/Transit

```
From Event: Colosseum Tour
To Event: Vatican Museums
Transport Mode: Transit
Notes: Metro Line A (Colosseo → Ottaviano).
       15 minutes + 5 min walk to Vatican entrance.
       Buy tickets in advance.
```

#### Taxi/Driving

```
From Event: Dinner at Restaurant
To Event: Hotel (end of day)
Transport Mode: Driving
Notes: Taxi. Approx €15-20. 10 minutes.
       Use Uber or hail on street.
```

## Transport Modes

### Driving
- Personal car
- Rental car
- Taxi/Uber/Lyft
- Private driver

**Best for**: Long distances, multiple stops, heavy luggage, groups

### Walking
- On foot
- Short distances

**Best for**: Nearby locations (<20 min walk), sightseeing along the way, good weather

### Bicycling
- Bicycle
- E-bike
- Scooter rental

**Best for**: Medium distances, bike-friendly cities, avoiding traffic

### Transit
- Metro/subway
- Bus
- Tram
- Local trains
- Ferry

**Best for**: Cities with good public transport, avoiding parking, budget-friendly

## Managing Transfers

### Editing a Transfer

1. Click on the transfer
2. Click **Edit**
3. Modify fields
4. Save

### Deleting a Transfer

1. Click on the transfer
2. Click **Delete**
3. Confirm deletion

!!! warning
    Deleting a transfer is permanent.

### Viewing on Maps

Transfers with location data appear on:
- Day timeline maps
- Trip overview maps
- Route visualization (from → to)

## Best Practices

### Main Transfers Planning

✅ **Always include**:
- Arrival and departure transfers
- Booking confirmations
- Departure and arrival times
- Check-in requirements
- Baggage allowances

**Example checklist**:
```
✓ Flight booked
✓ Seats selected
✓ Online check-in reminder (24h before)
✓ Baggage rules noted
✓ Airport parking/transport arranged
✓ Confirmation numbers recorded
```

### Buffer Time

Leave adequate time between:

**After arrival transfer**:
- Customs/immigration (international): 60-90 min
- Baggage claim: 30-45 min
- Transport to hotel: Variable
- **Buffer before first event**: 2-3 hours minimum

**Before departure transfer**:
- International flights: Arrive 3 hours early
- Domestic flights: Arrive 2 hours early
- Trains: Arrive 30-45 min early
- **Last event should end**: 4-5 hours before flight

**Between stays**:
- Allow time for checkout (hotel may hold bags)
- Travel time + 30% buffer
- Time before check-in (store bags if early)

### Notes Best Practices

**For flights, include**:
```
Airline: British Airways
Flight: BA500
Departure: Terminal 5, Gate opens 1h before
Seat: 12A (window)
Baggage: 1x23kg checked, 1x10kg carry-on
Check-in: Online 24h before
Confirmation: BA123456
```

**For trains, include**:
```
Company: Trenitalia
Train: Freccia Rossa #9352
Platform: TBD (check 20 min before)
Seat: Coach 5, Seat 22A
Booking: TRENITALIA-123456
```

**For stay transfers, include**:
```
Checkout: 11:00 (bags held by hotel until 14:00)
Transport: Pre-booked taxi, €50 fixed
Driver: Marco +39 123 456 7890
Drop-off: New hotel, Via Example 123
Arrival: ~14:30 (check-in 15:00)
```

### Simple Transfer Planning

Don't create transfers for:
- ❌ Events in the same building
- ❌ Adjacent locations (<2 min walk)
- ❌ Very obvious connections

Do create transfers for:
- ✅ Different neighborhoods
- ✅ Transport requiring tickets/booking
- ✅ Routes needing specific instructions

## Time Calculations

### Estimating Transfer Duration

**Walking**: ~5 km/h (3 mph)
- 1 km = ~12 minutes
- 1 mile = ~20 minutes

**Driving (city)**:  ~30 km/h (20 mph) with traffic
- 5 km = ~10 minutes
- 3 miles = ~10 minutes

**Metro/Transit**: Variable
- Check specific routes
- Add waiting time (5-10 min)
- Add walk to/from stations

**Taxi/Uber**: Similar to driving
- Add wait time for pickup (5-15 min)

!!! tip "Add 30% Buffer"
    Always add extra time for unexpected delays, getting lost, or slow travel.

## Frequently Asked Questions

### Can I have multiple arrival/departure transfers?

Each trip can have one arrival and one departure transfer. If you have multiple flights (with connections), add connection details in notes.

### How do I handle flight connections?

Add connection details in the notes:
```
Notes: LHR → FCO (direct)
       Connection option: Change at CDG
       If delayed, backup flight: BA502 (2 hours later)
```

### Can I track train station to hotel transport?

Yes! Use a simple transfer:
```
From Event: Arrival at Roma Termini (arrival transfer endpoint)
To Event: Check-in at Hotel (first stay)
Transport Mode: Metro
Notes: Line B to Colosseo. 10 minutes.
```

### Should I add transfers for every movement?

No. Only add transfers when:
- Different locations/neighborhoods
- Specific transport needed
- Time/route planning important

Skip for:
- Same building
- Adjacent locations
- Obvious walking routes

### How do I handle rental cars?

**Pickup**:
```
Type: Car (Rental)
Direction: Arrival (if part of arrival)
Notes: Enterprise Rent-A-Car. Pickup at airport.
       Confirmation: ENT-123456. Full insurance included.
       Return: Day 7, same location.
```

**Return**:
Include in departure transfer notes or create separate event.

### Can I attach tickets/confirmations?

Currently, no direct file attachments. Options:
- Add **Ticket URL** for e-tickets
- Use trip **Links** section for booking pages
- Store confirmation numbers in notes

### How do I track multi-leg journeys?

**Option 1**: One transfer with detailed notes
```
Notes: Multi-leg journey:
       1. Train: Rome → Florence (2h)
       2. Change in Florence (1h wait)
       3. Train: Florence → Venice (2h)
       Total: 5 hours
```

**Option 2**: Separate events for each leg (if staying overnight between)

## Related Guides

- [Stays](stays.md) - Managing accommodations
- [Days](days.md) - Organizing daily schedules
- [Experiences](experiences.md) - Planning activities
- [Trips](trips.md) - Trip overview

---

**Next**: Visit the [FAQ section](../faq.md) for common questions
