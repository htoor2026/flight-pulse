"""Flight Pulse dashboard backed by the local MySQL analytics layer."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd
import streamlit as st

from flight_pulse.analysis import FlightAnalysis
from flight_pulse.analyst import FlightAnalyst
from flight_pulse.chat import GeminiAnalystChat
from flight_pulse.config import GeminiSettings, MySQLSettings
from flight_pulse.repository import connect_mysql


st.set_page_config(
    page_title="Flight Pulse",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)


NUMERIC_COLUMNS = {
    "total_flights",
    "delayed_flights",
    "cancelled_flights",
    "flight_count",
    "delay_rate_percent",
    "average_departure_delay_minutes",
    "average_arrival_delay_minutes",
    "departure_delay_samples",
    "arrival_delay_samples",
    "maximum_delay_minutes",
    "departure_delay_minutes",
    "arrival_delay_minutes",
    "scheduled_hour_utc",
    "temperature_c",
    "precipitation_mm",
    "snowfall_cm",
    "visibility_m",
    "wind_speed_kmh",
    "wind_gusts_kmh",
    "weather_code",
}


def _frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    for column in frame.columns.intersection(NUMERIC_COLUMNS):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _metric(value: object, *, suffix: str = "", decimals: int = 0) -> str:
    if value is None:
        return "—"
    if isinstance(value, Decimal):
        value = float(value)
    if not isinstance(value, (int, float)):
        return str(value)
    return f"{value:,.{decimals}f}{suffix}"


@st.cache_data(ttl=300, show_spinner="Loading Flight Pulse data…")
def load_dashboard_data() -> dict[str, Any]:
    """Load one read-only dashboard snapshot, then close the connection."""
    connection = connect_mysql(MySQLSettings.from_env())
    try:
        return FlightAnalysis(connection).report(minimum_flights=1, top_limit=10)
    finally:
        connection.close()


def ask_flight_pulse(
    question: str,
    history: list[dict[str, str]],
) -> str:
    """Answer one question, closing the read-only database connection afterward."""
    connection = connect_mysql(MySQLSettings.from_env())
    try:
        chat = GeminiAnalystChat(
            FlightAnalyst(connection),
            GeminiSettings.from_env(),
        )
        return chat.answer(question, history=history).text
    finally:
        connection.close()


st.title("Flight Pulse")
st.caption("YYZ flight operations, delay patterns, and hourly weather context")

try:
    report = load_dashboard_data()
except Exception:
    st.error(
        "Flight Pulse could not read the local MySQL database. "
        "Verify the database is running and the local environment variables are set."
    )
    st.stop()

overview = report["overview"]
sample_size = int(overview.get("total_flights") or 0)
st.info(
    f"Current sample: {sample_size} YYZ flights from one short collection window. "
    "Results describe this dataset only."
)

with st.sidebar:
    st.subheader("Data snapshot")
    st.write(f"{sample_size} flights")
    st.write("All displayed times are UTC")
    if st.button("Refresh MySQL data", width="stretch"):
        st.cache_data.clear()
        st.rerun()


st.header("Overview")
metric_columns = st.columns(3)
metric_columns[0].metric("Total flights", _metric(overview.get("total_flights")))
metric_columns[1].metric("Delayed flights", _metric(overview.get("delayed_flights")))
metric_columns[2].metric(
    "Cancelled flights",
    _metric(overview.get("cancelled_flights")),
)
metric_columns = st.columns(3)
metric_columns[0].metric(
    "Delay rate",
    _metric(overview.get("delay_rate_percent"), suffix="%", decimals=2),
)
metric_columns[1].metric(
    "Average departure delay",
    _metric(
        overview.get("average_departure_delay_minutes"),
        suffix=" min",
        decimals=2,
    ),
    help=(
        f"Based on {int(overview.get('departure_delay_samples') or 0)} flights "
        "with actual departure timestamps."
    ),
)
metric_columns[2].metric(
    "Average arrival delay",
    _metric(
        overview.get("average_arrival_delay_minutes"),
        suffix=" min",
        decimals=2,
    ),
    help=(
        f"Based on {int(overview.get('arrival_delay_samples') or 0)} flights "
        "with actual arrival timestamps. Negative values indicate early arrival."
    ),
)


st.header("Flight Status")
status_frame = _frame(report["status_counts"])
disrupted_frame = _frame(report["disrupted_flights"])
status_chart, disruption_table = st.columns((1, 2))
with status_chart:
    st.subheader("Status distribution")
    if status_frame.empty:
        st.info("No status data is available.")
    else:
        st.bar_chart(status_frame.set_index("status")[["flight_count"]])
with disruption_table:
    st.subheader("Delayed and cancelled flights")
    st.dataframe(
        disrupted_frame,
        hide_index=True,
        width="stretch",
        column_order=(
            "flight_number",
            "airline",
            "origin_iata",
            "destination_iata",
            "status",
            "departure_delay_minutes",
            "arrival_delay_minutes",
            "scheduled_departure",
            "scheduled_arrival",
        ),
    )


st.header("Airline Analysis")
airline_frame = _frame(report["delays_by_airline"])
if airline_frame.empty:
    st.info("No airline data is available.")
else:
    airline_chart, airline_table = st.columns((1, 2))
    with airline_chart:
        st.subheader("Flights and delays by airline")
        st.bar_chart(
            airline_frame.set_index("airline")[["total_flights", "delayed_flights"]],
            horizontal=True,
        )
    with airline_table:
        st.subheader("Airline detail")
        display_airlines = airline_frame.copy()
        display_airlines.loc[
            display_airlines["departure_delay_samples"] < 2,
            "average_departure_delay_minutes",
        ] = pd.NA
        display_airlines.loc[
            display_airlines["arrival_delay_samples"] < 2,
            "average_arrival_delay_minutes",
        ] = pd.NA
        st.dataframe(
            display_airlines,
            hide_index=True,
            width="stretch",
            column_order=(
                "airline",
                "total_flights",
                "delayed_flights",
                "delay_rate_percent",
                "average_departure_delay_minutes",
                "departure_delay_samples",
                "average_arrival_delay_minutes",
                "arrival_delay_samples",
            ),
        )
    st.caption(
        "Average airline delays are shown only with at least two observed values. "
        "These results are not representative beyond the current sample."
    )


st.header("Route Analysis")
route_frame = _frame(report["delays_by_route"])
top_delayed_frame = _frame(report["top_delayed_flights"])
if route_frame.empty:
    st.info("No route data is available.")
else:
    route_frame["route"] = (
        route_frame["origin_iata"].fillna("Unknown")
        + " → "
        + route_frame["destination_iata"].fillna("Unknown")
    )
    top_routes = route_frame.sort_values(
        ["delayed_flights", "total_flights"],
        ascending=False,
    ).head(15)
    route_chart, route_table = st.columns((1, 2))
    with route_chart:
        st.subheader("Flights and delays by route")
        st.bar_chart(
            top_routes.set_index("route")[["total_flights", "delayed_flights"]],
            horizontal=True,
        )
    with route_table:
        st.subheader("Delayed routes")
        st.dataframe(
            top_routes[top_routes["delayed_flights"] > 0],
            hide_index=True,
            width="stretch",
            column_order=(
                "route",
                "total_flights",
                "delayed_flights",
                "delay_rate_percent",
            ),
        )
    st.subheader("Top delayed flights with observed delay values")
    st.dataframe(top_delayed_frame, hide_index=True, width="stretch")
    st.caption("Route rankings describe only the current 72-flight sample.")


st.header("Time Analysis")
hour_frame = _frame(report["delays_by_hour"])
if hour_frame.empty:
    st.info("No scheduled-time data is available.")
else:
    hour_frame["scheduled_hour_utc"] = hour_frame["scheduled_hour_utc"].astype(
        "Int64"
    )
    hour_chart, hour_table = st.columns((2, 1))
    with hour_chart:
        st.subheader("Flights and delays by scheduled YYZ hour")
        st.bar_chart(
            hour_frame.set_index("scheduled_hour_utc")[[
                "total_flights",
                "delayed_flights",
            ]]
        )
    with hour_table:
        st.subheader("Hourly detail")
        st.dataframe(
            hour_frame,
            hide_index=True,
            width="stretch",
            column_order=(
                "scheduled_hour_utc",
                "total_flights",
                "delayed_flights",
                "delay_rate_percent",
            ),
        )
    st.caption("Hours are UTC and use scheduled departure or arrival at YYZ.")


st.header("Weather Context")
weather_frame = _frame(report["weather_context"])
if weather_frame.empty:
    st.info("No YYZ weather data is available.")
else:
    weather_frame["observation_time"] = pd.to_datetime(
        weather_frame["observation_time"],
        utc=True,
    )
    weather_frame = weather_frame.set_index("observation_time")
    conditions_tab, relationship_tab, weather_table_tab = st.tabs(
        ("Conditions over time", "Delay context", "Hourly records")
    )
    with conditions_tab:
        temperature_chart, wind_chart = st.columns(2)
        with temperature_chart:
            st.subheader("Temperature")
            st.line_chart(weather_frame[["temperature_c"]])
        with wind_chart:
            st.subheader("Wind speed and gusts")
            st.line_chart(weather_frame[["wind_speed_kmh", "wind_gusts_kmh"]])
        precipitation_chart, visibility_chart = st.columns(2)
        with precipitation_chart:
            st.subheader("Precipitation and snowfall")
            st.bar_chart(weather_frame[["precipitation_mm", "snowfall_cm"]])
        with visibility_chart:
            st.subheader("Visibility")
            st.line_chart(weather_frame[["visibility_m"]])
    with relationship_tab:
        st.subheader("Weather alongside delayed flights")
        st.bar_chart(
            weather_frame[["total_flights", "delayed_flights", "cancelled_flights"]]
        )
        active_hours = weather_frame[weather_frame["total_flights"] > 0].reset_index()
        st.scatter_chart(
            active_hours,
            x="precipitation_mm",
            y="delayed_flights",
            size="total_flights",
            color="wind_gusts_kmh",
        )
        st.caption(
            "Weather is aligned to each flight's scheduled YYZ UTC hour. "
            "This visual association does not establish that weather caused a delay."
        )
    with weather_table_tab:
        st.dataframe(
            weather_frame.reset_index(),
            hide_index=True,
            width="stretch",
            column_order=(
                "observation_time",
                "temperature_c",
                "precipitation_mm",
                "snowfall_cm",
                "visibility_m",
                "wind_speed_kmh",
                "wind_gusts_kmh",
                "weather_code",
                "total_flights",
                "delayed_flights",
                "cancelled_flights",
            ),
        )


st.header("Data Quality and Limitations")
quality = report["data_quality"]
quality_columns = st.columns(4)
quality_columns[0].metric(
    "Missing actual departures",
    _metric(quality.get("missing_actual_departure")),
)
quality_columns[1].metric(
    "Missing actual arrivals",
    _metric(quality.get("missing_actual_arrival")),
)
quality_columns[2].metric(
    "Duplicate provider IDs",
    _metric(quality.get("duplicate_provider_ids")),
)
quality_columns[3].metric(
    "Extreme departure delays",
    _metric(quality.get("extreme_departure_delay")),
)
st.warning(
    "This dashboard uses a small, single-window sample. Actual timestamps are "
    "sparse, one extreme delay materially affects averages, and airline or route "
    "results should not be generalized. Weather is supporting context only and "
    "does not prove causation."
)


st.header("Ask Flight Pulse")
st.caption(
    "Ask about the current flight sample, a flight number, airline, route, "
    "weather context, or a possible delay explanation. The assistant can use "
    "only the approved read-only analytical tools."
)

if "flight_pulse_chat_messages" not in st.session_state:
    st.session_state.flight_pulse_chat_messages = [
        {
            "role": "assistant",
            "content": (
                "Ask me about the current YYZ sample—for example, "
                "“Why was AA 3606 delayed?”"
            ),
        }
    ]

for message in st.session_state.flight_pulse_chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if question := st.chat_input("Ask Flight Pulse about the current sample"):
    previous_messages = list(st.session_state.flight_pulse_chat_messages)
    st.session_state.flight_pulse_chat_messages.append(
        {"role": "user", "content": question}
    )
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing the current Flight Pulse sample…"):
            try:
                answer = ask_flight_pulse(question, previous_messages)
            except Exception:
                answer = (
                    "The AI analyst is unavailable. Verify the local MySQL "
                    "connection and GEMINI_API_KEY configuration, then try again."
                )
        st.markdown(answer)

    st.session_state.flight_pulse_chat_messages.append(
        {"role": "assistant", "content": answer}
    )
