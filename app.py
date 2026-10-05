"""Flight Pulse dashboard backed by MySQL or a synthetic public-demo report."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd
import streamlit as st

from flight_pulse.analysis import FlightAnalysis
from flight_pulse.analyst import FlightAnalyst
from flight_pulse.chat import GeminiAnalystChat
from flight_pulse.config import GeminiSettings, MySQLSettings, demo_mode_enabled
from flight_pulse.demo import load_demo_report
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
    "median_departure_delay_minutes",
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
def load_dashboard_data(demo_mode: bool = False) -> dict[str, Any]:
    """Load a synthetic demo report or one read-only MySQL snapshot."""
    if demo_mode:
        return load_demo_report()

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


def render_flight_analytics(demo_mode: bool = False) -> None:
    """Render the existing read-only analytics and AI assistant experience."""
    try:
        report = load_dashboard_data(demo_mode)
    except Exception:
        if demo_mode:
            st.error("Flight Pulse could not load the bundled synthetic demo data.")
        else:
            st.error(
                "Flight Pulse could not read the local MySQL database. "
                "Verify the database is running and the local environment variables "
                "are set."
            )
        return

    overview = report["overview"]
    sample_size = int(overview.get("total_flights") or 0)
    if demo_mode:
        st.info(
            "Public demo mode uses a synthetic snapshot modeled on the project's "
            "validated local results. It does not query live flight, weather, news, "
            "or database services."
        )
    st.info(
        f"Current sample: {sample_size} YYZ flights from one short collection "
        "window. Results describe this dataset only."
    )

    with st.sidebar:
        st.subheader("Synthetic demo snapshot" if demo_mode else "Data snapshot")
        st.write(f"{sample_size} flights")
        st.write("All displayed times are UTC")
        refresh_label = "Reload demo snapshot" if demo_mode else "Refresh MySQL data"
        if st.button(refresh_label, width="stretch"):
            st.cache_data.clear()
            st.rerun()

    st.header("Overview")
    metric_columns = st.columns(3)
    metric_columns[0].metric("Total flights", _metric(overview.get("total_flights")))
    metric_columns[1].metric(
        "Delayed flights", _metric(overview.get("delayed_flights"))
    )
    metric_columns[2].metric(
        "Cancelled flights",
        _metric(overview.get("cancelled_flights")),
    )
    metric_columns = st.columns(4)
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
        "Median departure delay (current sample)",
        _metric(
            overview.get("median_departure_delay_minutes"),
            suffix=" min",
            decimals=2,
        ),
        help=(
            f"Typical stored departure delay across the current sample's "
            f"{int(overview.get('departure_delay_samples') or 0)} flights "
            "with known departure delays."
        ),
    )
    metric_columns[3].metric(
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
                airline_frame.set_index("airline")[
                    ["total_flights", "delayed_flights"]
                ],
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
            "Average airline delays are shown only with at least two observed "
            "values. These results are not representative beyond the current sample."
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
        hour_frame["scheduled_hour_utc"] = hour_frame[
            "scheduled_hour_utc"
        ].astype("Int64")
        hour_chart, hour_table = st.columns((2, 1))
        with hour_chart:
            st.subheader("Flights and delays by scheduled YYZ hour")
            st.bar_chart(
                hour_frame.set_index("scheduled_hour_utc")[
                    ["total_flights", "delayed_flights"]
                ]
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
                weather_frame[
                    ["total_flights", "delayed_flights", "cancelled_flights"]
                ]
            )
            active_hours = weather_frame[
                weather_frame["total_flights"] > 0
            ].reset_index()
            st.scatter_chart(
                active_hours,
                x="precipitation_mm",
                y="delayed_flights",
                size="total_flights",
                color="wind_gusts_kmh",
            )
            st.caption(
                "Weather is aligned to each flight's scheduled YYZ UTC hour. "
                "This visual association does not establish that weather caused a "
                "delay."
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
        "sparse, one extreme delay materially affects averages, and airline or "
        "route results should not be generalized. Weather is supporting context "
        "only and does not prove causation."
    )

    st.header("Ask Flight Pulse")
    if demo_mode:
        st.info(
            "AI chat is disabled in the public demo. Run Flight Pulse locally with "
            "MySQL and a Gemini API key to use the seven read-only analyst tools."
        )
        return

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


def render_business_overview() -> None:
    """Explain Flight Pulse for non-technical stakeholders."""
    st.header("Business Overview")
    st.caption(
        "A concise view of the problem, the product, and the value demonstrated by "
        "the current YYZ sample."
    )

    problem_column, solution_column = st.columns(2)
    with problem_column:
        st.subheader("Business problem")
        st.write(
            "Flight disruption information is spread across operational flight "
            "records, weather observations, and public disruption reporting. That "
            "fragmentation makes it harder to quickly understand what happened and "
            "which context is available."
        )
    with solution_column:
        st.subheader("Flight Pulse solution")
        st.write(
            "Flight Pulse brings those signals into one evidence-grounded view. It "
            "summarizes YYZ operations, highlights delay patterns, aligns flights "
            "with weather, stores relevant news metadata, and supports plain-language "
            "questions through a constrained analytical assistant."
        )

    st.subheader("Questions it can answer")
    question_columns = st.columns(2)
    with question_columns[0]:
        st.markdown(
            "- How many flights were delayed or cancelled?\n"
            "- Which airlines and routes had delays in this sample?\n"
            "- At what scheduled hours were delays observed?"
        )
    with question_columns[1]:
        st.markdown(
            "- What is known about a specific stored flight?\n"
            "- What weather was recorded near its scheduled YYZ time?\n"
            "- Is there enough stored evidence to explain a delay?"
        )

    st.subheader("Validated project results")
    result_columns = st.columns(5)
    result_columns[0].metric("YYZ flights", "72")
    result_columns[1].metric("Weather observations", "48")
    result_columns[2].metric("Flights matched to weather", "72 / 72")
    result_columns[3].metric(
        "Median departure delay",
        "21.00 min",
        help="Based on 3 flights with observed departure-delay values.",
    )
    result_columns[4].metric("Automated tests", "70")
    st.write(
        "The project also includes a reusable analytics layer, an interactive "
        "dashboard, seven read-only analyst tools, and Gemini function-calling chat."
    )
    st.caption(
        "The 21.00-minute median uses the 3 flights with observed departure-delay "
        "values in the current sample. Delivery quality is supported by automated "
        "testing, CI validation, reviewed pull requests, and human-controlled merges."
    )
    st.caption(
        "The full local system uses MySQL and optionally Gemini. The public portfolio "
        "demo uses a clearly labeled synthetic static snapshot and makes no provider "
        "or database calls."
    )

    value_column, limits_column = st.columns(2)
    with value_column:
        st.subheader("Potential operational value")
        st.markdown(
            "- Faster review of disruption patterns in a selected operating window\n"
            "- A shared view of flight, weather, and news context\n"
            "- Repeatable, grounded answers instead of ad hoc data inspection\n"
            "- A foundation for broader monitoring once more data is collected"
        )
    with limits_column:
        st.subheader("Current sample limitations")
        st.markdown(
            "- The flight sample is small and covers one short collection window.\n"
            "- Actual departure and arrival timestamps are sparse.\n"
            "- One extreme delay materially affects aggregate averages.\n"
            "- Weather and news are context, not proof of delay causation."
        )


def render_technical_overview() -> None:
    """Explain the implemented system for technical reviewers."""
    st.header("Technical Overview")
    st.caption(
        "A read-only analytical pipeline with isolated provider adapters, normalized "
        "persistence, reusable analytics, and validated AI tool routing."
    )

    st.subheader("End-to-end architecture")
    st.markdown(
        "**AeroDataBox** → **ingestion and normalization** → **MySQL** → "
        "**analytics** → **weather and news context** → **Streamlit dashboard** → "
        "**Gemini tool-calling assistant**"
    )
    st.caption(
        "External provider calls are separate ingestion operations. The dashboard "
        "and assistant read stored data and do not refresh providers."
    )

    st.subheader("Runtime modes")
    st.markdown(
        "- **Local full system:** MySQL-backed analytics, seven read-only analyst "
        "tools, and optional Gemini function calling.\n"
        "- **Public portfolio demo:** bundled synthetic static report, no provider or "
        "database calls, and AI chat disabled."
    )

    architecture_left, architecture_right = st.columns(2)
    with architecture_left:
        st.subheader("Data sources and ingestion")
        st.markdown(
            "- **AeroDataBox:** flight schedules and operational status for YYZ\n"
            "- **Open-Meteo:** hourly YYZ weather observations\n"
            "- **GDELT DOC 2.0:** disruption-related article metadata\n"
            "- Provider-specific responses are normalized before persistence.\n"
            "- Timestamps are handled consistently in UTC where practical."
        )
        st.subheader("MySQL persistence")
        st.markdown(
            "- Separate tables retain normalized flights, weather observations, "
            "and news metadata.\n"
            "- Stable provider or deterministic identifiers prevent obvious "
            "duplicates.\n"
            "- Upsert behavior supports repeatable ingestion without duplicating "
            "the same records."
        )
        st.subheader("Analytics and enrichment")
        st.markdown(
            "- Reusable SQL-backed analytics calculate operational, airline, route, "
            "hourly, and data-quality summaries.\n"
            "- Weather is matched to each flight's scheduled YYZ UTC hour.\n"
            "- News metadata is searched within a bounded window around the flight.\n"
            "- Neither enrichment source is treated as causal proof."
        )
    with architecture_right:
        st.subheader("Dashboard and analyst tools")
        st.write(
            "Streamlit renders the stored analytics and exposes seven structured, "
            "read-only tools:"
        )
        st.markdown(
            "1. `get_flight_overview`\n"
            "2. `find_flight`\n"
            "3. `get_airline_analysis`\n"
            "4. `get_route_analysis`\n"
            "5. `get_weather_context`\n"
            "6. `get_news_context`\n"
            "7. `investigate_delay`"
        )
        st.subheader("Gemini function calling")
        st.markdown(
            "- Gemini receives explicit function declarations, not database access.\n"
            "- Tool names and structured arguments are validated before dispatch.\n"
            "- The function loop is bounded and returns local tool results for a "
            "grounded response.\n"
            "- Gemini cannot execute arbitrary SQL or Python."
        )
        st.subheader("AI safety boundaries")
        st.markdown(
            "- Analytical queries use fixed read-only repository operations.\n"
            "- No database credentials are included in prompts or responses.\n"
            "- Weather and news are labeled as context or possible contributors.\n"
            "- Delay investigations retain an explicit insufficient-evidence "
            "outcome."
        )

    st.subheader("Testing, CI, and Git workflow")
    st.markdown(
        "- **Testing:** 70 unit tests cover normalization, delay calculations, "
        "repositories, analytics, enrichment, tool validation, and mocked Gemini "
        "routing without consuming provider quota.\n"
        "- **Application validation:** Streamlit is exercised offline to verify the "
        "page renders without making provider calls.\n"
        "- **CI:** GitHub Actions performs the repository's configured syntax checks.\n"
        "- **Git:** milestone work is developed on feature branches, validated, and "
        "merged into `main` after review."
    )

    st.subheader("Engineering workflow and governance")
    st.markdown(
        "**Human** → **Master / Orchestrator** → **Genesis task, scope, evidence, "
        "gates, and checkpoints** → **specialist agents**\n\n"
        "The Master coordinates bounded work and triages findings. Genesis stores "
        "bounded task state, scope, evidence, gates, and checkpoints. The "
        "Implementation Agent writes approved code; the Test Agent validates locally "
        "without live provider calls; Code Review and Security are read-only "
        "reviewers; the Documentation Agent is docs-focused; and the Shipping Agent "
        "may stage, commit, push, and open an approved pull request, but cannot merge "
        "`main`. Final merges and sensitive boundaries remain human-controlled."
    )

    st.subheader("Layered validation example")
    st.write(
        "FP-001 implemented the median departure-delay metric and passed semantic "
        "tests. Exact local MySQL validation then exposed a production-dialect issue: "
        "`row_number` conflicted with MySQL reserved terminology. FP-002 changed the "
        "alias to `delay_rank`; exact MySQL validation succeeded, the final 63-test "
        "suite and CI passed, and the merge remained human-controlled."
    )

    decisions_column, limitations_column = st.columns(2)
    with decisions_column:
        st.subheader("Engineering challenges and decisions")
        st.markdown(
            "- Isolated provider JSON handling from the normalized domain model.\n"
            "- Derived delays only when scheduled and actual timestamps were present.\n"
            "- Used deterministic identifiers and upserts for duplicate control.\n"
            "- Kept weather/news association distinct from causal claims.\n"
            "- Chose explicit tool dispatch over unrestricted model-generated SQL."
        )
    with limitations_column:
        st.subheader("Known technical limitations")
        st.markdown(
            "- The dataset contains 72 flights from one collection window.\n"
            "- Sparse actual timestamps limit observed delay calculations.\n"
            "- One delay over the existing 360-minute quality threshold affects "
            "aggregates.\n"
            "- GDELT live validation returned HTTP 429.\n"
            "- Gemini live validation returned HTTP 503 before tool selection.\n"
            "- Live provider validation may require a future approved retry."
        )


st.title("Flight Pulse")
st.caption("YYZ flight operations, delay patterns, and evidence-grounded context")

try:
    DEMO_MODE = demo_mode_enabled()
except ValueError as error:
    st.error(str(error))
    st.stop()

flight_analytics_tab, business_overview_tab, technical_overview_tab = st.tabs(
    ("Flight Analytics", "Business Overview", "Technical Overview")
)

with flight_analytics_tab:
    render_flight_analytics(DEMO_MODE)

with business_overview_tab:
    render_business_overview()

with technical_overview_tab:
    render_technical_overview()
