## Selected Flight Data Source

**Status:** APPROVED FOR MVP

**Primary provider:** AeroDataBox

### Purpose

AeroDataBox will be used as the initial operational flight-data source for
Flight Pulse.

The first implementation will focus on flights involving Toronto Pearson
International Airport (YYZ).

### Why AeroDataBox

AeroDataBox was selected because it provides the operational flight fields
needed for the Flight Pulse MVP, including:

- flight identification
- airline information
- origin and destination airports
- scheduled flight times
- operational/revised timing information
- flight status
- cancellation/diversion information where available
- airport/terminal/gate information where available

It also provides documented API specifications and free/trial options suitable
for development and portfolio experimentation.

### Initial scope

The initial ingestion pipeline will retrieve recent/current YYZ flight data and
normalize it into the Flight Pulse internal schema.

No prediction model is part of this milestone.

### Cost policy

Development must use a free/trial option initially.

Do not enable a paid subscription, overage billing, or any other billable
service without explicit approval.

### Data retention

Flight Pulse must respect the retention terms of the active AeroDataBox plan.

The initial MVP does not depend on permanent storage of AeroDataBox raw API
responses.

If long-term historical analysis becomes necessary, a separately suitable
historical dataset may be introduced later.

### Provider abstraction

Provider-specific response structures should remain isolated inside the
ingestion layer.

The rest of Flight Pulse should operate on normalized flight records rather
than AeroDataBox-specific JSON.

### Fallback provider

No fallback provider is selected for the MVP.

A fallback will only be introduced if there is a demonstrated need.

### Decision

AeroDataBox is approved as the Flight Pulse MVP flight-data provider.

Research phase complete.

Next milestone:

Flight Data → MySQL