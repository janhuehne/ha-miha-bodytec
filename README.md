# miha bodytec for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Unofficial Home Assistant integration for the **miha bodytec LogX** customer portal
([training.miha-bodytec.com](https://training.miha-bodytec.com/login)) — EMS training
appointments, membership, and studio info.

> Not affiliated with miha bodytec GmbH. For personal use only — respect studio ToS.

## Features

| Entity | Description |
|---|---|
| `sensor.miha_bodytec_next_appointment` | Next training (timestamp) |
| `sensor.miha_bodytec_days_until_next_training` | Days until next session |
| `sensor.miha_bodytec_upcoming_count` | Upcoming appointments (+ list attributes) |
| `sensor.miha_bodytec_past_count` | Recent past appointments |
| `sensor.miha_bodytec_trainings_this_week` / `_month` | Counts |
| `sensor.miha_bodytec_membership_until` | Contract end date |
| `sensor.miha_bodytec_contract_name` | Membership / service name |
| `sensor.miha_bodytec_studio_*` | Studio name, city, phone, email |
| `sensor.miha_bodytec_cancellation_deadline_hours` | Cancel policy |
| `sensor.miha_bodytec_booking_lead_time_minutes` | Min lead time to book |
| `sensor.miha_bodytec_slot_duration_minutes` | Default slot length |
| `binary_sensor.miha_bodytec_training_today` / `_tomorrow` | Session flags |
| `binary_sensor.miha_bodytec_membership_active` | Ongoing services |
| `binary_sensor.miha_bodytec_online_booking_allowed` | Portal booking enabled |
| `calendar.miha_bodytec_appointments` | HA calendar of sessions |

### Services

| Service | Purpose |
|---|---|
| `miha_bodytec.refresh` | Force poll |
| `miha_bodytec.cancel_appointment` | Cancel by `appointment_id` |
| `miha_bodytec.book_appointment` | Book a free slot |
| `miha_bodytec.reschedule_appointment` | Move a booking |

## Install (HACS)

1. HACS → Integrations → ⋮ → Custom repositories  
2. URL: `https://github.com/janhuehne/ha-miha-bodytec` — category **Integration**  
3. Download **miha bodytec**, restart Home Assistant  
4. Settings → Devices & services → Add → **miha bodytec**  
5. Enter your LogX email + password

### Manual

Copy `custom_components/miha_bodytec` into `config/custom_components/`, restart, add the integration.

## Sports / Training dashboard

A ready-made Lovelace dashboard lives in [`lovelace/sports_training.yaml`](lovelace/sports_training.yaml).

1. Settings → Dashboards → **Add dashboard** → take control (YAML)  
2. Paste the contents of `sports_training.yaml`  
3. Adjust entity IDs if you renamed the device

## Requirements

- Home Assistant **2024.1+**
- LogX member login from your studio (same as the training portal)

## Privacy

Credentials are stored in the Home Assistant config entry (and therefore in HA backups).
The integration polls every **15 minutes**.
