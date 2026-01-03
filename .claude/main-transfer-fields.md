# MainTransfer Model - Field Specification

## 🔧 Campi Base del Modello

### Relazioni e Classificazione
- **trip** - ForeignKey al Trip
- **type** - IntegerField (PLANE=1, TRAIN=2, CAR=3, OTHER=4)
- **direction** - IntegerField (ARRIVAL=1, DEPARTURE=2)

---

## 📍 Campi Località (variano per tipo)

### Per PLANE (da CSV - no geocoding)
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `origin_code` | CharField(10) | Codice IATA aeroporto |
| `origin_name` | CharField(200) | Nome completo aeroporto |
| `destination_code` | CharField(10) | Codice IATA aeroporto |
| `destination_name` | CharField(200) | Nome completo aeroporto |

**Esempio:**
- origin_code: "FCO"
- origin_name: "Leonardo da Vinci–Fiumicino Airport"
- destination_code: "JFK"
- destination_name: "John F. Kennedy International Airport"

### Per TRAIN (da CSV - no geocoding, NO code)
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `origin_name` | CharField(200) | Nome completo stazione |
| `destination_name` | CharField(200) | Nome completo stazione |

**Esempio:**
- origin_name: "Roma Termini"
- destination_name: "Milano Centrale"

**Nota:** I treni NON hanno `origin_code`/`destination_code` perché non presenti nel CSV.

### Per CAR e OTHER (con geocoding Mapbox)
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `origin_address` | CharField(500) | Indirizzo completo di partenza |
| `destination_address` | CharField(500) | Indirizzo completo di arrivo |

**Esempio:**
- origin_address: "Via Roma 123, Rome, Italy"
- destination_address: "Piazza Duomo, Milan, Italy"

### Coordinate (per tutti i tipi)
| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `origin_latitude` | FloatField | Lat origine (da CSV o geocoding) |
| `origin_longitude` | FloatField | Lon origine (da CSV o geocoding) |
| `destination_latitude` | FloatField | Lat destinazione (da CSV o geocoding) |
| `destination_longitude` | FloatField | Lon destinazione (da CSV o geocoding) |

---

## ⏰ Campi Comuni (tutti i tipi)

| Campo | Tipo | Required | Descrizione |
|-------|------|----------|-------------|
| `start_time` | TimeField | ✅ | Orario partenza |
| `end_time` | TimeField | ✅ | Orario arrivo |
| `booking_reference` | CharField(100) | ❌ | Codice prenotazione |
| `ticket_url` | URLField | ❌ | Link al biglietto/prenotazione |
| `notes` | TextField | ❌ | Note aggiuntive |

---

## ✈️ Campi Specifici PLANE (in `type_specific_data` JSONField)

| Campo | Tipo | Descrizione | Esempio |
|-------|------|-------------|---------|
| `flight_number` | string | Numero volo | "AZ1234" |
| `terminal` | string | Terminal | "T1" |
| `company` | string | Compagnia aerea | "Alitalia" |
| `company_website` | string (URL) | Sito compagnia aerea | "https://www.alitalia.com" |

---

## 🚂 Campi Specifici TRAIN (in `type_specific_data` JSONField)

| Campo | Tipo | Descrizione | Esempio |
|-------|------|-------------|---------|
| `train_number` | string | Numero treno | "FR9612" |
| `carriage` | string | Numero carrozza | "7" |
| `seat` | string | Numero posto | "42A" |
| `company` | string | Operatore ferroviario | "Trenitalia" |
| `company_website` | string (URL) | Sito operatore | "https://www.trenitalia.com" |

---

## 🚗 Campi Specifici CAR (in `type_specific_data` JSONField)

| Campo | Tipo | Descrizione | Esempio |
|-------|------|-------------|---------|
| `is_rental` | boolean | Auto a noleggio? | true |
| `company` | string | Compagnia noleggio (se rental) | "Hertz" |
| `company_website` | string (URL) | Sito compagnia noleggio | "https://www.hertz.com" |

---

## 📦 Campi Specifici OTHER (in `type_specific_data` JSONField)

| Campo | Tipo | Descrizione | Esempio |
|-------|------|-------------|---------|
| `company` | string | Nome compagnia | "FlixBus" |
| `company_website` | string (URL) | Sito compagnia | "https://..." |

**Note:**
- OTHER copre: bus, boat, taxi, shuttle, etc.
- Campi minimi per massima flessibilità

---

## 📅 Metadata (automatici)

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `created_at` | DateTimeField | Data creazione (auto) |
| `updated_at` | DateTimeField | Data ultima modifica (auto) |

---

## 🔒 Constraints

1. **Unique Constraint**: Solo 1 MainTransfer per direzione per trip
   - `unique_together = ['trip', 'direction']`

2. **Database Index**: Su `['trip', 'direction']` per performance

---

## ✅ Validazioni

### Model-level (clean method)
1. **Plane** → DEVE avere `origin_code`, `origin_name`, `destination_code`, `destination_name`
2. **Train** → DEVE avere `origin_name` e `destination_name` (NO code)
3. **Car/Other** → DEVONO avere `origin_address` e `destination_address`

### Form-level
1. **Plane**: Validare codice IATA valido (da CSV)
2. **Train**: Validare nome stazione valido (da CSV, ricerca per nome)
3. **Orari**: start_time e end_time presenti (possono attraversare mezzanotte)

---

## 📝 Note Implementazione

### Geocoding Strategy
- **Plane**: Coordinate recuperate da CSV lookup via codice IATA
- **Train**: Coordinate recuperate da CSV lookup via nome stazione
- **Car/Other**: Coordinate via Mapbox geocoding (come eventi esistenti)
- Geocoding automatico in `model.save()` solo se coordinate mancanti

### Type-Specific Data Access
Proprietà del modello per accesso semplificato:
```python
transfer.flight_number  # invece di transfer.type_specific_data.get('flight_number')
transfer.company        # invece di transfer.type_specific_data.get('company')
transfer.is_rental      # invece di transfer.type_specific_data.get('is_rental')
```

### Company Field
Il campo `company` è stato **spostato da campo comune a type-specific** perché:
- Plane: nome compagnia aerea
- Train: nome operatore ferroviario
- Car: nome compagnia noleggio (solo se is_rental=true)
- Other: nome compagnia generica

Questo permette maggiore flessibilità e contesto specifico per tipo.

---

## 🎯 Riepilogo Campi Rimossi

### Rimossi dai campi comuni:
- ❌ `price` - Non necessario
- ❌ `company` - Spostato in type_specific_data

### Rimossi da PLANE:
- ❌ `gate` - Non essenziale
- ❌ `checked_baggage` - Non essenziale

### Rimossi da TRAIN:
- ❌ `origin_code` / `destination_code` - Non presenti nel CSV
- ❌ `platform` (binario) - Non essenziale

### Rimossi da CAR:
- ❌ `license_plate` - Non essenziale
- ❌ `car_type` - Non essenziale
- ❌ `rental_booking_reference` - Già coperto da booking_reference comune
