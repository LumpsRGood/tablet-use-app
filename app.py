import pandas as pd
import streamlit as st
import io
import numpy as np

# Title of the app
st.title("Tablet Use Report Processor")

# File uploader
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

# Process file
if uploaded_file:
    try:
        # Read the uploaded CSV file
        df = pd.read_csv(uploaded_file)

        # Normalize column names to handle line breaks
        df.columns = df.columns.str.replace("\n", " ").str.strip()

        # Rename columns for easier reference
        df = df.rename(columns={
            "Device Orders Report": "Device Orders",
            "Staff Customer": "Staff Customer",
            "Base (Including Disc.)": "Base"
        })

        # Normalize Device Orders column
        df["Device Orders"] = df["Device Orders"].str.strip().str.lower()
        df["Device Orders"] = df["Device Orders"].replace({
            "handheld": "handheld",
            "hand held": "handheld",
            "pos": "pos",
            "pos terminal": "pos"
        })

        # Consolidate all Device Orders variations (e.g., "handheld 2", "pos 1")
        df["Device Orders"] = df["Device Orders"].str.extract(r"(handheld|pos)", expand=False).fillna("unknown")

        # Ensure Base column is numeric
        df["Base"] = pd.to_numeric(df["Base"], errors="coerce").fillna(0)

        # Group and sum by Staff Customer and Device Orders
        grouped_df = df.groupby(["Staff Customer", "Device Orders"])["Base"].sum().unstack(fill_value=0)

        # Ensure the columns for Handheld and POS exist
        if "handheld" not in grouped_df.columns:
            grouped_df["handheld"] = 0
        if "pos" not in grouped_df.columns:
            grouped_df["pos"] = 0

        # Rename columns for clarity
        grouped_df = grouped_df.rename(columns={
            "handheld": "Handheld Total",
            "pos": "POS Total"
        }).reset_index()

        # Calculate Percentage Handheld Use
        grouped_df["Percentage Handheld Use"] = np.where(
            (grouped_df["Handheld Total"] + grouped_df["POS Total"]) == 0,
            0,
            (grouped_df["Handheld Total"] /
             (grouped_df["Handheld Total"] + grouped_df["POS Total"])) * 100
        ).round(2)

        # Sort by Percentage Handheld Use in descending order
        grouped_df = grouped_df.sort_values(by="Percentage Handheld Use", ascending=False)

        # Format percentage column with right justification for CSV output
        grouped_df["Percentage Handheld Use"] = grouped_df["Percentage Handheld Use"].apply(
            lambda x: f"{x:.2f}%".rjust(8)
        )

        # Limit decimals for Handheld Total and POS Total
        grouped_df["Handheld Total"] = grouped_df["Handheld Total"].round(2)
        grouped_df["POS Total"] = grouped_df["POS Total"].round(2)

        # Apply conditional formatting for display
        def highlight_row(row):
            percentage = row["Percentage Handheld Use"]
            percentage = float(percentage.strip('%').strip())  # Remove % sign and strip spaces
            if percentage >= 70:
                return ["background-color: green; color: white; border: 2px solid black"] * len(row)
            elif 50 <= percentage < 70:
                return ["background-color: yellow; color: black; border: 2px solid black"] * len(row)
            else:
                return ["background-color: red; color: white; border: 2px solid black"] * len(row)

        styled_display_df = grouped_df.style.apply(highlight_row, axis=1).set_properties(
            subset=["Percentage Handheld Use"], **{"text-align": "right"}
        ).set_properties(
            subset=["Handheld Total", "POS Total"], **{"text-align": "right"}
        )

        # Show processed data with styling
        st.write("Processed Data:")
        st.dataframe(grouped_df)  # Original data for download compatibility
        st.write(styled_display_df)

        # Write CSV with proper formatting
        output = io.BytesIO()
        grouped_df.to_csv(output, index=False, float_format="%.2f", lineterminator="\n")
        output.seek(0)

        # Download processed file
        st.download_button(
            label="Download Processed Report",
            data=output,
            file_name="processed_report.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
