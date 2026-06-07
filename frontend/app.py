"""Frontend Streamlit pentru aplicația Curs BNR."""

from datetime import datetime
from pathlib import Path
from typing import Any

import json
import os
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import streamlit.components.v1 as components
from frontend.chatbot_tools import (
    answer_with_llm_or_local_tools_with_source,
    answer_with_local_tools,
    test_gemini_connection,
)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

API_BASE_URL = "http://localhost:7772"


def _load_environment() -> None:
    """Încarcă variabilele de mediu din .env dacă dotenv este disponibil."""
    if load_dotenv is not None:
        env_file = Path(__file__).resolve().parent / ".env"
        if env_file.exists():
            load_dotenv(dotenv_path=str(env_file))
        else:
            load_dotenv()


def _check_llm_available() -> bool:
    """Verifică dacă LLM-ul Gemini este disponibil."""
    _load_environment()
    gemini_key = os.getenv("GEMINI_API_KEY")
    return bool(gemini_key)


def _check_gemini_available() -> bool:
    """Verifică dacă Google Gemini este disponibil."""
    _load_environment()
    api_key = os.getenv("GEMINI_API_KEY")
    return bool(api_key)


def _format_error_message(error: str) -> str:
    """
    Formatează mesajul de eroare pentru afișare.
    Ascunde erorile mari 429, RESOURCE_EXHAUSTED, quota cu un mesaj scurt.
    """
    if not error:
        return ""
    
    error_lower = error.lower()
    
    # Detectează erori 429 sau RESOURCE_EXHAUSTED și ascunde JSON/detalii
    if any(keyword in error_lower for keyword in ["429", "resource_exhausted", "quota exceeded", "quota"]):
        return "Gemini a atins limita de request-uri. S-a folosit fallback local."
    
    # Pentru alte erori, afișează scurt (primele 100 caractere)
    if len(error) > 100:
        return error[:100] + "..."
    
    return error



def fetch_json(endpoint: str) -> Any:
    """Trimite o cerere GET la backend și returnează JSON-ul răspuns."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        return {"error": str(error)}


def post_json(endpoint: str, timeout: int = 60) -> Any:
    """Trimite o cerere POST la backend și returnează JSON-ul răspuns."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.post(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return {
            "error": "Antrenarea durează mai mult decât limita de așteptare. Verifică backend-ul sau lista rulărilor."
        }
    except requests.RequestException as error:
        return {"error": str(error)}


def _display_rates(rates: Any) -> None:
    if isinstance(rates, list) and rates:
        df_rates = pd.DataFrame(rates)
        if not df_rates.empty:
            df_rates = df_rates.drop_duplicates(subset=["date", "currency"]).reset_index(drop=True)
            st.dataframe(df_rates)
        else:
            st.info("Nu există cursuri salvate încă.")
    else:
        st.info("Nu există cursuri salvate încă.")


def _plot_rate_history(rates: Any) -> None:
    """Afișează graficul istoric EUR/RON folosind datele recente."""
    if not isinstance(rates, list) or not rates:
        st.info("Nu există suficiente date pentru graficul de istoric EUR/RON.")
        return

    df_rates = pd.DataFrame(rates)
    if df_rates.empty or "date" not in df_rates.columns or "value" not in df_rates.columns:
        st.info("Datele pentru graficul EUR/RON nu sunt disponibile.")
        return

    df_rates = df_rates.drop_duplicates(subset=["date", "currency"]).sort_values(by="date")
    try:
        df_rates["date"] = pd.to_datetime(df_rates["date"], errors="coerce")
    except Exception:
        st.info("Formatul datelor de tip dată nu este valid pentru grafic.")
        return

    df_rates = df_rates.dropna(subset=["date"])
    if df_rates.empty:
        st.info("Nu există date valide pentru graficul EUR/RON.")
        return

    # Folosește ultimele 90 de valori, dar doar dacă sunt suficiente
    df_rates = df_rates.tail(120)
    fig = px.line(
        df_rates,
        x="date",
        y="value",
        title="Evoluția recentă a cursului EUR/RON",
        labels={"date": "Dată", "value": "Curs EUR/RON"},
    )
    fig.update_layout(hovermode="x unified", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)


def _plot_model_metrics(runs: Any) -> None:
    """Afișează graficul metricilor pe ultimele rulări de antrenare."""
    if not isinstance(runs, list) or len(runs) < 2:
        st.info("Nu există suficiente rulări pentru graficul metricilor.")
        return

    df_runs = pd.DataFrame(runs)
    if df_runs.empty or "created_at" not in df_runs.columns:
        st.info("Nu există suficiente date pentru graficul metricilor.")
        return

    try:
        df_runs["created_at"] = pd.to_datetime(df_runs["created_at"], errors="coerce")
    except Exception:
        st.info("Formatul datelor de timp pentru rulări nu este valid.")
        return

    df_runs = df_runs.dropna(subset=["created_at"]).sort_values(by="created_at")
    if len(df_runs) < 2:
        st.info("Nu există suficiente rulări pentru graficul metricilor.")
        return

    metric_columns = [col for col in ["mae", "rmse", "mape"] if col in df_runs.columns]
    if not metric_columns:
        st.info("Nu există metrici disponibile pentru afișarea graficului.")
        return

    fig = px.line(
        df_runs,
        x="created_at",
        y=metric_columns,
        title="Evoluția MAE, RMSE și MAPE în ultimele rulări",
        labels={"created_at": "Data rulării", "value": "Valoare metrică", "variable": "Metrică"},
    )
    fig.update_layout(hovermode="x unified", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    """Afișează interfața Streamlit principală."""
    st.title("Aplicație Curs BNR")

    health = fetch_json("/api/health")
    if isinstance(health, dict) and health.get("status") == "ok":
        st.success("Backend OK: ok")
    else:
        error_message = health.get("error") if isinstance(health, dict) else str(health)
        st.error(f"Backend indisponibil: {error_message}")
        return

    tab_dashboard, tab_date, tab_model, tab_optuna, tab_chatbot = st.tabs(
        [
            "📊 Dashboard",
            "⚙️ Date & Scraping",
            "🔄 Model & Reantrenare",
            "🔬 Optuna",
            "💬 Chatbot",
        ]
    )

    with tab_dashboard:
        st.subheader("📈 Prognoză curentă")
        forecast = fetch_json("/api/forecast/latest")
        if isinstance(forecast, dict) and forecast.get("error"):
            st.error(f"Eroare la încărcarea prognozei: {forecast['error']}")
        elif forecast.get("predicted_value") is not None:
            predicted_value = forecast.get("predicted_value", 0.0)
            mae_14_days = forecast.get("mae_14_days") or 0.0
            if mae_14_days < 0.01:
                emoji_kpi = "🟢"
            elif mae_14_days < 0.05:
                emoji_kpi = "🟡"
            else:
                emoji_kpi = "🔴"

            col1, col2 = st.columns(2)
            col1.metric("Curs prognozat EUR/RON", f"{predicted_value:.4f}")
            col2.metric(f"{emoji_kpi} MAE 14 zile", f"{mae_14_days:.4f}")
        else:
            st.info("Nicio prognoză disponibilă. Rulează antrenarea mai întâi.")

        st.subheader("📊 Grafic forecast")
        st.markdown("**Grafic principal: forecastul celui mai bun model**")
        plot_files = sorted(
            Path("reports").glob("forecast_plot_*.html"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        latest_rate_info = fetch_json("/api/rates?limit=1")
        last_rate_date = None
        if isinstance(latest_rate_info, list) and latest_rate_info:
            last_rate_date = latest_rate_info[0].get("date")

        if plot_files:
            latest_plot = plot_files[0]
            plot_name = latest_plot.name
            plot_mod_time = datetime.fromtimestamp(latest_plot.stat().st_mtime)
            st.write(f"Grafic principal: {plot_name}")
            st.write(f"Ultima modificare grafic: {plot_mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if last_rate_date:
                st.write(f"Ultimul curs disponibil: {last_rate_date}")
                try:
                    last_rate_dt = datetime.fromisoformat(last_rate_date).date()
                    if plot_mod_time.date() < last_rate_dt:
                        st.warning(
                            "Graficul pare mai vechi decât ultimele date disponibile. Rulează reantrenarea pentru regenerare."
                        )
                except ValueError:
                    pass

            with open(latest_plot, "r", encoding="utf-8") as file:
                html_content = file.read()
            components.html(html_content, height=520, scrolling=True)
        else:
            st.info("Nu există grafice generate. Rulează reantrenarea mai întâi.")

        rates_120 = fetch_json("/api/rates?limit=120")
        st.subheader("Evoluția recentă a cursului EUR/RON")
        _plot_rate_history(rates_120)

        if st.button("Regenerare grafic forecast"):
            generate_plot_result = post_json("/api/generate-plot")
            if isinstance(generate_plot_result, dict) and generate_plot_result.get("status") == "ok":
                st.success(f"Grafic regenerat: {generate_plot_result.get('plot_file')}")
            else:
                st.error(
                    f"Nu s-a putut genera graficul: {generate_plot_result.get('message', 'Eroare')}")

        st.subheader("Ultimele cursuri")
        rates = fetch_json("/api/rates?limit=20")
        _display_rates(rates)

    with tab_date:
        st.subheader("⚙️ Date & Scraping")
        col1, col2 = st.columns(2)

        import_result = None
        scrape_result = None

        with col1:
            if st.button("Importă date din CSV"):
                import_result = post_json("/api/import-rates")
                if isinstance(import_result, dict) and import_result.get("error"):
                    st.error(f"Eroare la import: {import_result['error']}")
                else:
                    st.success("Import realizat.")
                    st.json(import_result)

        with col2:
            if st.button("Actualizează date prin scraping"):
                scrape_result = post_json("/api/scrape")
                if isinstance(scrape_result, dict) and scrape_result.get("error"):
                    st.error(f"Eroare la scraping: {scrape_result['error']}")
                else:
                    st.success("Scraping realizat.")
                    st.json(scrape_result)

        rates_stats = fetch_json("/api/rates/stats")
        if isinstance(rates_stats, dict) and rates_stats.get("error"):
            st.warning("Endpoint /api/rates/stats nu este disponibil.")
        else:
            st.subheader("Statistici rates")
            st.json(rates_stats)

        st.subheader("Ultimele cursuri")
        rates = fetch_json("/api/rates?limit=20")
        _display_rates(rates)

    with tab_model:
        st.subheader("🔄 Model & Reantrenare")
        retrain_result = None
        if st.button("Reantrenează modelul"):
            with st.spinner("Antrenare în curs... poate dura câteva minute."):
                retrain_result = post_json("/api/retrain", timeout=300)
                if isinstance(retrain_result, dict) and retrain_result.get("error"):
                    st.error(f"Eroare la reantrenare: {retrain_result['error']}")
                elif retrain_result.get("status") == "ok":
                    st.success(f"Model antrenat: {retrain_result.get('model_name', 'necunoscut')}")
                else:
                    st.error(f"Eroare la reantrenare: {retrain_result.get('message', 'Răspuns invalid de la backend')}")

        if isinstance(retrain_result, dict) and retrain_result.get("status") == "ok":
            col1, col2, col3 = st.columns(3)
            col1.metric("MAE", f"{retrain_result.get('mae', 0):.4f}")
            col2.metric("RMSE", f"{retrain_result.get('rmse', 0):.4f}")
            col3.metric("MAPE", f"{retrain_result.get('mape', 0):.2f}%")
            if retrain_result.get("forecast_saved") is False:
                st.warning(retrain_result.get("message", "Prognoza nu a putut fi salvată."))

        st.subheader("Ultimele rulări de antrenare")
        runs = fetch_json("/api/runs?limit=20")
        if isinstance(runs, list) and runs:
            df_runs = pd.DataFrame(runs)
            if not df_runs.empty:
                st.dataframe(df_runs)
                st.subheader("Evoluția metricilor modelului")
                _plot_model_metrics(runs)
            else:
                st.info("Nu există încă rulări de antrenare în baza de date.")
        else:
            st.info("Nu există încă rulări de antrenare în baza de date.")

    with tab_optuna:
        st.subheader("🔬 Optuna")
        directories = [Path("models"), Path("reports"), Path("agentic_docs")]
        patterns = ["*optuna*", "*study*", "*.json", "*.db", "*.sqlite"]
        found_files = []
        for directory in directories:
            if directory.exists():
                for pattern in patterns:
                    found_files.extend(directory.rglob(pattern))

        if found_files:
            unique_files = sorted({file.resolve() for file in found_files})
            for file in unique_files:
                st.write(f"**{file.name}** — {file.parent} — ultima modificare: {file.stat().st_mtime}")
                if file.suffix.lower() == ".json":
                    try:
                        with open(file, "r", encoding="utf-8") as json_file:
                            content = json.load(json_file)
                        with st.expander(f"Conținut JSON: {file.name}"):
                            st.json(content)
                    except Exception:
                        st.write("Fișier JSON invalid sau prea mare pentru afișare.")
        else:
            st.info("Nu s-au găsit fișiere Optuna/study în directoarele analizate.")

        st.markdown(
            "Studiile Optuna pot fi vizualizate cu optuna-dashboard dacă există fișiere/studii salvate. "
            "Nu porni optuna-dashboard automat."
        )

    with tab_chatbot:
        st.subheader("💬 Chatbot curs valutar")
        
        # Status provider
        if _check_gemini_available():
            st.success("🟢 **Gemini: activ**")
        else:
            st.info("⚪ **Gemini: inactiv**")

        # Test Gemini
        if st.button("Testează Gemini"):
            test_result = test_gemini_connection()
            st.json(test_result)

        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
        
        if "use_llm_checkbox" not in st.session_state:
            st.session_state["use_llm_checkbox"] = False

        llm_available = _check_llm_available()
        use_llm = st.checkbox(
            "Folosește LLM dacă este disponibil",
            value=st.session_state["use_llm_checkbox"],
            disabled=not llm_available,
            key="use_llm_checkbox_widget",
        )
        st.session_state["use_llm_checkbox"] = use_llm
        st.caption("Fallback local activ dacă LLM nu este disponibil sau dacă răspunsul eșuează.")

        with st.form("chatbot_form", clear_on_submit=True):
            user_message = st.text_input(
                "Întreabă despre prognoză, cursuri sau model...",
                key="chatbot_message_input",
            )
            submitted = st.form_submit_button("Trimite")

            if submitted:
                if user_message and user_message.strip():
                    st.session_state["chat_history"].append(
                        {"role": "user", "content": user_message.strip()}
                    )
                    
                    if st.session_state["use_llm_checkbox"] and llm_available:
                        result = answer_with_llm_or_local_tools_with_source(user_message.strip())
                        answer = result.get("answer", "Eroare la generarea răspunsului.")
                        source = result.get("source", "unknown")
                        error = result.get("error")
                    else:
                        answer = answer_with_local_tools(user_message.strip())
                        source = "local"
                        error = None
                    
                    st.session_state["chat_history"].append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "source": source,
                            "error": error,
                        }
                    )
                else:
                    st.warning("Te rog scrie mai întâi o întrebare.")

        for chat_item in st.session_state["chat_history"]:
            role = chat_item.get("role")
            content = chat_item.get("content")
            source = chat_item.get("source")
            error = chat_item.get("error")
            
            if role == "user":
                st.markdown(f"**Tu:** {content}")
            else:
                st.markdown(f"**Asistent:** {content}")
                
                if source == "gemini_tools":
                    st.caption("🟢 Mod răspuns: **GEMINI TOOLS**")
                elif source == "gemini":
                    st.caption("🟢 Mod răspuns: **GEMINI**")
                elif source == "local_fallback":
                    st.caption("🟡 Mod răspuns: **LOCAL FALLBACK** (LLM indisponibil)")
                else:
                    st.caption("⚪ Mod răspuns: **LOCAL**")

                if error:
                    formatted_error = _format_error_message(error)
                    st.caption(f"Detalii fallback: {formatted_error}")




if __name__ == "__main__":
    main()
