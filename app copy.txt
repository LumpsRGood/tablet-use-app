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

        # Limit decimals for POS and Handheld Total columns
        grouped_df["Handheld Total"] = grouped_df["Handheld Total"].map(lambda x: f"{x:,.2f}")
        grouped_df["POS Total"] = grouped_df["POS Total"].map(lambda x: f"{x:,.2f}")

        # Format percentage column correctly
        grouped_df["Percentage Handheld Use"] = grouped_df["Percentage Handheld Use"].map(lambda x: f"{x:.2f}%")

        # Calculate overall totals
        total_handheld = grouped_df["Handheld Total"].astype(str).str.replace(",", "").astype(float).sum()
        total_pos = grouped_df["POS Total"].astype(str).str.replace(",", "").astype(float).sum()
        overall_percentage = (total_handheld / (total_handheld + total_pos) * 100) if (total_handheld + total_pos) > 0 else 0

        # Create the summary row
        summary_row = pd.DataFrame({
            "Staff Customer": ["Overall Total"],
            "Handheld Total": [f"{total_handheld:,.2f}"],
            "POS Total": [f"{total_pos:,.2f}"],
            "Percentage Handheld Use": [f"{overall_percentage:.2f}%"]
        })

        # Separate the summary row before sorting
        summary_row_df = grouped_df[grouped_df["Staff Customer"] == "Overall Total"]
        non_summary_df = grouped_df[grouped_df["Staff Customer"] != "Overall Total"]

        # Sort the non-summary data
        sorted_df = non_summary_df.sort_values(by="Percentage Handheld Use", ascending=False)

        # Append the summary row to the sorted data
        final_df = pd.concat([sorted_df, summary_row], ignore_index=True)

        # Apply conditional formatting for display
        def highlight_row(row):
            if row["Staff Customer"] == "Overall Total":
                # Blue for overall total
                return ["background-color: blue; color: white; border: 2px solid black"] * len(row)
            else:
                percentage = row["Percentage Handheld Use"]
                if isinstance(percentage, str):
                    percentage = float(percentage.replace('%', '').replace(',', ''))
                if percentage >= 70:
                    return ["background-color: green; color: white; border: 2px solid black"] * len(row)
                elif 50 <= percentage < 70:
                    return ["background-color: yellow; color: black; border: 2px solid black"] * len(row)
                else:
                    return ["background-color: red; color: white; border: 2px solid black"] * len(row)

        styled_display_df = final_df.style.apply(highlight_row, axis=1).set_properties(
            subset=["Percentage Handheld Use"], **{"text-align": "right"}
        ).set_properties(
            subset=["Handheld Total", "POS Total"], **{"text-align": "right"}
        )

        # Write CSV with proper formatting
        output = io.BytesIO()
        final_df.to_csv(output, index=False, float_format="%.2f", lineterminator="\n")
        output.seek(0)

        # Download processed file
        st.download_button(
            label="Download Processed Report",
            data=output,
            file_name="processed_report.csv",
            mime="text/csv"
        )

        # Show processed data with styling
        st.write("Processed Data:")
        st.dataframe(final_df)  # Original data for download compatibility
        st.write(styled_display_df)

    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
