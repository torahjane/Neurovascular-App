import streamlit as st
import pandas as pd
import joblib
import time

# Load model and columns
model = joblib.load("neurovas.pkl")
X_columns = pd.read_csv("X_columns.csv").columns.tolist()

# ------------------ Session State Init ------------------ #
if "stage_before" not in st.session_state:
    st.session_state.loop = 1
    st.session_state.stage_before = None
    st.session_state.rpi_before = None
    st.session_state.feedback_active = False
    st.session_state.show_updated_input = False
    st.session_state.improving = False
    st.session_state.log = []

# ------------------ Utility Functions ------------------ #
def check_signal_quality(hrv, emg_level, posture):
    if hrv < 20 or hrv > 120:
        return "❌ Poor HRV Signal"
    elif emg_level not in ["normal", "overactive", "underactive"]:
        return "❌ Unrecognized EMG Input"
    elif posture not in ["aligned", "lean_left", "lean_right", "slouched"]:
        return "❌ Posture Not Valid"
    else:
        return "✅ Good"

def calculate_rpi(stage, hrv, emg_level):
    score = stage * 33
    if hrv < 50:
        score += 10
    if emg_level == "overactive":
        score += 5
    elif emg_level == "underactive":
        score += 3
    return min(score, 100)

def interpret_rpi(rpi):
    if rpi < 35:
        return "🟢 Relaxed – No immediate action needed."
    elif 35 <= rpi < 70:
        return "🟡 Alert – Begin feedback session."
    else:
        return "🔴 Urgent – Trigger full feedback loop."

def run_prediction(hrv, emg_level, posture):
    row = dict.fromkeys(X_columns, 0)
    row["hrv"] = hrv
    emg_col = f"emg_level_{emg_level}"
    posture_col = f"posture_{posture}"
    if emg_col in row: row[emg_col] = 1
    if posture_col in row: row[posture_col] = 1
    input_df = pd.DataFrame([row])
    stage = model.predict(input_df)[0]
    rpi = calculate_rpi(stage, hrv, emg_level)
    return stage, rpi

def log_summary(loop, stage_before, rpi_before, stage_after, rpi_after, status):
    st.session_state.log.append({
        "Loop": loop,
        "Stage Before": stage_before,
        "RPI Before": rpi_before,
        "Stage After": stage_after,
        "RPI After": rpi_after,
        "Status": status
    })

# ------------------ UI ------------------ #
st.title("🧠 NeuroVas Healing Feedback Loop")
st.subheader(f"🌀 Session Loop #{st.session_state.loop}")

if not st.session_state.feedback_active and not st.session_state.show_updated_input:
    st.header("🔍 Initial Signal Input")
    hrv = st.number_input("💓 HRV", min_value=0.0, max_value=200.0, step=5.0)
    emg_level = st.selectbox("💪 EMG Level", ["normal", "overactive", "underactive"])
    posture = st.selectbox("🧟 Posture", ["aligned", "lean_left", "lean_right", "slouched"])

    if st.button("Start Prediction & Begin Feedback"):
        quality = check_signal_quality(hrv, emg_level, posture)
        st.write(f"📶 Signal Quality: {quality}")

        if "✅" not in quality:
            st.warning("Fix input to proceed.")
        else:
            stage, rpi = run_prediction(hrv, emg_level, posture)
            st.session_state.stage_before = stage
            st.session_state.rpi_before = rpi

            col1, col2 = st.columns(2)
            with col1:
                st.metric("🧠 Initial Stage", stage, help="Predicted varicose stage (0-3)")
            with col2:
                st.metric("📊 Initial RPI", f"{rpi}/100", help="Risk Prediction Index")

            st.progress(rpi / 100)
            st.write(interpret_rpi(rpi))

            if stage == 0 and rpi < 35:
                st.success("🟢 Patient is healthy. No healing required.")
                if st.button("🔄 Start New Session"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
            else:
                st.session_state.feedback_active = True
                st.rerun()

# ------------------ FEEDBACK TIMER ------------------ #
if st.session_state.feedback_active:
    st.warning("🧘 Begin healing now. Sit straight, breathe calm...")
    st.markdown("<script>window.setTimeout(() => window.location.reload(), 30000);</script>", unsafe_allow_html=True)
    with st.empty():
        for i in range(30, 0, -1):
            st.markdown(f"⏳ Feedback Time: **{i} seconds** remaining...")
            time.sleep(1)
    st.success("⏱️ Feedback session complete.")
    st.session_state.feedback_active = False
    st.session_state.show_updated_input = True
    st.rerun()

# ------------------ UPDATED SIGNAL INPUT ------------------ #
if st.session_state.show_updated_input:
    st.header("🗒️ Updated Signal After Feedback")
    after_hrv = st.number_input("💓 Updated HRV", min_value=0.0, max_value=200.0, step=5.0, key="after_hrv")
    after_emg = st.selectbox("💪 Updated EMG Level", ["normal", "overactive", "underactive"], key="after_emg")
    after_posture = st.selectbox("🧟 Updated Posture", ["aligned", "lean_left", "lean_right", "slouched"], key="after_posture")

    if st.button("🔁 Analyze Updated Signal"):
        stage_after, rpi_after = run_prediction(after_hrv, after_emg, after_posture)
        st.subheader("📊 Comparison Result")

        col1, col2 = st.columns(2)
        delta_stage = int(stage_after - st.session_state.stage_before)
        delta_rpi = int(rpi_after - st.session_state.rpi_before)

        emoji_stage = "🔼" if delta_stage < 0 else ("⚪" if delta_stage == 0 else "🔽")
        emoji_rpi = "🔼" if delta_rpi < 0 else ("⚪" if delta_rpi == 0 else "🔽")

        with col1:
            st.metric("Stage", st.session_state.stage_before, delta=emoji_stage + str(delta_stage), help="Stage change")
            st.metric("RPI", f"{st.session_state.rpi_before}/100", delta=emoji_rpi + str(delta_rpi), help="RPI change")

        with col2:
            st.metric("New Stage", stage_after)
            st.metric("New RPI", f"{rpi_after}/100")
            st.progress(rpi_after / 100)

        if rpi_after < st.session_state.rpi_before or stage_after < st.session_state.stage_before:
            st.success("✅ Feedback effective! Signal improved.")
            st.session_state.improving = True
            log_summary(st.session_state.loop, st.session_state.stage_before, st.session_state.rpi_before, stage_after, rpi_after, "Improved ✅")
        elif rpi_after == st.session_state.rpi_before and stage_after == st.session_state.stage_before:
            st.info("⚪ Signal remained the same. Repeating feedback...")
            log_summary(st.session_state.loop, st.session_state.stage_before, st.session_state.rpi_before, stage_after, rpi_after, "No Change ⚪")
        else:
            st.warning("❌ Signals worsened. Repeating feedback loop.")
            log_summary(st.session_state.loop, st.session_state.stage_before, st.session_state.rpi_before, stage_after, rpi_after, "Worsened ❌")

        if not st.session_state.improving:
            st.session_state.rpi_before = rpi_after
            st.session_state.stage_before = stage_after
            st.session_state.loop += 1
            st.session_state.show_updated_input = False
            st.session_state.feedback_active = True
            st.rerun()

# ------------------ NEW SESSION ------------------ #
if st.session_state.improving:
    if st.button("🔄 Start New Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ------------------ LIVE SESSION LOG DISPLAY ------------------ #
st.markdown("---")
st.subheader("📂 Session Summary (Live Only)")

if st.session_state.log:
    df_log = pd.DataFrame(st.session_state.log)
    st.dataframe(df_log.style.format({"RPI Before": "{:.0f}", "RPI After": "{:.0f}"}))
else:
    st.info("No session logs yet.")
