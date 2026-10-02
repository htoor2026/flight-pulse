-- Flight Pulse local schema. All DATETIME values are stored as UTC.

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

CREATE TABLE IF NOT EXISTS weather_observations (
    airport_iata CHAR(3) NOT NULL,
    observation_time DATETIME(6) NOT NULL,
    temperature_c DECIMAL(6, 2) NULL,
    precipitation_mm DECIMAL(8, 2) NULL,
    snowfall_cm DECIMAL(8, 2) NULL,
    visibility_m DECIMAL(10, 2) NULL,
    wind_speed_kmh DECIMAL(7, 2) NULL,
    wind_gusts_kmh DECIMAL(7, 2) NULL,
    weather_code SMALLINT NULL,
    fetched_at DATETIME(6) NOT NULL,
    PRIMARY KEY (airport_iata, observation_time),
    INDEX idx_weather_observation_time (observation_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS news_articles (
    article_id CHAR(64) NOT NULL,
    title TEXT NOT NULL,
    source_domain VARCHAR(255) NULL,
    url TEXT NOT NULL,
    published_at DATETIME(6) NULL,
    language VARCHAR(64) NULL,
    query_topic VARCHAR(255) NOT NULL,
    fetched_at DATETIME(6) NOT NULL,
    PRIMARY KEY (article_id),
    INDEX idx_news_published_at (published_at),
    INDEX idx_news_source_domain (source_domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
