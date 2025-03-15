import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from scipy.stats import skew

# --- Helper Function ---
def perform_analysis(df, material):
    """
    For a given material, filter the data (using 'Material description' column),
    compute skewness for Embodied Energy (EE) and Embodied Carbon (EC),
    remove outliers with the IQR method,
    and return the median values along with the original filtered data.
    """
    # Filter rows where the material name appears in the description
    mat_df = df[df["Material description"].str.contains(material, case=False, na=False)]
    if mat_df.empty:
        return None
    
    # Calculate skewness for EE and EC (drop missing values)
    ee_skew = skew(mat_df["Embodied Energy"].dropna())
    ec_skew = skew(mat_df["Embodied Carbon"].dropna())
    
    # Outlier removal for EE using the IQR method
    Q1_ee = mat_df["Embodied Energy"].quantile(0.25)
    Q3_ee = mat_df["Embodied Energy"].quantile(0.75)
    IQR_ee = Q3_ee - Q1_ee
    ee_clean = mat_df["Embodied Energy"][(mat_df["Embodied Energy"] >= Q1_ee - 1.5 * IQR_ee) &
                                         (mat_df["Embodied Energy"] <= Q3_ee + 1.5 * IQR_ee)]
    
    # Outlier removal for EC using the IQR method
    Q1_ec = mat_df["Embodied Carbon"].quantile(0.25)
    Q3_ec = mat_df["Embodied Carbon"].quantile(0.75)
    IQR_ec = Q3_ec - Q1_ec
    ec_clean = mat_df["Embodied Carbon"][(mat_df["Embodied Carbon"] >= Q1_ec - 1.5 * IQR_ec) &
                                         (mat_df["Embodied Carbon"] <= Q3_ec + 1.5 * IQR_ec)]
    
    median_ee = ee_clean.median()
    median_ec = ec_clean.median()
    
    return {
        "skew_ee": ee_skew,
        "skew_ec": ec_skew,
        "median_ee": median_ee,
        "median_ec": median_ec,
        "data": mat_df  # Pass along data for plotting boxplots later
    }

# --- Dashboard Title ---
st.title("EPD Analysis Dashboard (Simplified)")

# --- Step 1: Project Details ---
st.header("1. Project Details")
project_name = st.text_input("Project Name")
project_area = st.text_input("Project Area")
project_location = st.text_input("Project Location")
work_package = st.selectbox("Project Work Package", ["Flooring", "False Ceiling", "Other"])

# --- Step 2: Define Primary and Secondary Materials ---
st.header("2. Define Materials")
primary_input = st.text_input(
    "Enter Primary Materials (comma-separated)", 
    value="vitrified, vitrified 20mm, granite, marble, terrazzo, engineered wood, grout, epoxy grout, adhesive, mortar, screed sheets"
)
primary_materials = [m.strip() for m in primary_input.split(",") if m.strip()]

st.write("**Enter details for Three Secondary Materials:**")
secondary_materials = {}
for i in range(1, 4):
    sec_name = st.text_input(f"Secondary Material {i} Name", key=f"sec_name_{i}")
    sec_purpose = st.text_input(f"Secondary Material {i} Purpose", key=f"sec_purpose_{i}")
    if sec_name:
        secondary_materials[sec_name] = sec_purpose

# --- Step 3: Map Primary Materials to Secondary ---
st.header("3. Map Primary to Secondary")
mapping = {}
if secondary_materials:
    for primary in primary_materials:
        sel = st.selectbox(
            f"Select secondary material for primary '{primary}'", 
            list(secondary_materials.keys()),
            key=primary
        )
        mapping[primary] = sel

# --- Step 4: Upload and Analyze Excel Data ---
st.header("4. Upload Excel File & Analyze Data")
st.markdown(
    "The Excel file should have at least the following columns:\n"
    "`Material description`, `Embodied Energy`, and `Embodied Carbon`."
)
uploaded_file = st.file_uploader("Upload EPD Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.subheader("Preview of Uploaded Data")
    st.dataframe(df.head())

    if st.button("Analyze Data"):
        analysis_results = {}
        # Analyze both primary and secondary materials
        all_materials = list(set(primary_materials + list(secondary_materials.keys())))
        for material in all_materials:
            result = perform_analysis(df, material)
            if result:
                analysis_results[material] = result
                st.markdown(f"### Analysis for {material}")
                st.write(f"Skewness for Embodied Energy (EE): {result['skew_ee']:.2f}")
                st.write(f"Skewness for Embodied Carbon (EC): {result['skew_ec']:.2f}")
                st.write(f"Representative EE (Median): {result['median_ee']:.2f}")
                st.write(f"Representative EC (Median): {result['median_ec']:.2f}")

                # Display box plots for EE and EC
                fig_ee = px.box(result["data"], y="Embodied Energy",
                                points="outliers", title=f"{material} – Embodied Energy")
                st.plotly_chart(fig_ee)

                fig_ec = px.box(result["data"], y="Embodied Carbon",
                                points="outliers", title=f"{material} – Embodied Carbon")
                st.plotly_chart(fig_ec)
            else:
                st.warning(f"No data found for material: {material}")

        # --- Step 5: Combine Primary and Secondary Values ---
        st.header("5. Combine & Compare Representative Values")
        combined = []
        for primary in primary_materials:
            secondary = mapping.get(primary)
            if primary in analysis_results:
                primary_res = analysis_results[primary]
                if secondary and secondary in analysis_results:
                    sec_res = analysis_results[secondary]
                    combined_ee = primary_res["median_ee"] + sec_res["median_ee"]
                    combined_ec = primary_res["median_ec"] + sec_res["median_ec"]
                else:
                    combined_ee = primary_res["median_ee"]
                    combined_ec = primary_res["median_ec"]
                combined.append({
                    "Primary": primary,
                    "Secondary": secondary if secondary else "None",
                    "Combined EE": combined_ee,
                    "Combined EC": combined_ec
                })

        if combined:
            df_combined = pd.DataFrame(combined)
            st.subheader("Results Sorted by Embodied Energy (EE)")
            st.dataframe(df_combined.sort_values("Combined EE"))
            st.subheader("Results Sorted by Embodied Carbon (EC)")
            st.dataframe(df_combined.sort_values("Combined EC"))
