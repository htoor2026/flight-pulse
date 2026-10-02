-- Milestone 1 schema only. All DATETIME values are stored as UTC.

CREATE TABLE IF NOT EXISTS flights (
    provider_flight_id VARCHAR(191) NOT NULL,
    flight_number VARCHAR(20) NOT NULL,
    airline VARCHAR(255) NULL,
    origin_iata CHAR(3) NULL,
    destination_iata CHAR(3) NULL,
    scheduled_departure DATETIME(6) NULL,
    actual_departure DATETIME(6) NULL,
    scheduled_arrival DATETIME(6) NULL,
    actual_arrival DATETIME(6) NULL,
    status VARCHAR(32) NOT NULL,
    departure_delay_minutes INT NULL,
    arrival_delay_minutes INT NULL,
    fetched_at DATETIME(6) NOT NULL,
    PRIMARY KEY (provider_flight_id),
    INDEX idx_flights_flight_number (flight_number),
    INDEX idx_flights_origin_iata (origin_iata),
    INDEX idx_flights_destination_iata (destination_iata),
    INDEX idx_flights_scheduled_departure (scheduled_departure),
    INDEX idx_flights_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
