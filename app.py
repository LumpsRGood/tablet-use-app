import pandas as pd
import streamlit as st
import io
import numpy as np

# Title of the app
st.title("Tablet Use Report Processor")

# File uploader
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file:
    try:
        # ---------------------------
        # Step 1: Load and Clean Data
        # ---------------------------
        df = pd.read_csv(uploaded_file)

        # Normalize column names (remove line breaks, trim spaces)
        df.columns = df.columns.str.replace("\n", " ").str.strip()

        # Rename columns for easier reference
        df = df.rename(columns={
            "Device Orders Report": "Device Orders",
            "Staff Customer": "Staff Customer",
            "Base (Including Disc.)": "Base"
        })

        # Normalize Device Orders values
        df["Device Orders"] = df["Device Orders"].str.strip().str.lower()
        df["Device Orders"] = df["Device Orders"].replace({
            "handheld": "handheld",
            "hand held": "handheld",
            "pos": "pos",
            "pos terminal": "pos"
        })

        # Extract only 'handheld' or 'pos', defaulting to 'unknown'
        df["Device Orders"] = df["Device Orders"].str.extract(r"(handheld|pos)", expand=False).fillna("unknown")

        # Ensure 'Base' column is numeric
        df["Base"] = pd.to_numeric(df["Base"], errors="coerce").fillna(0)

        # -------------------------------------
        # Step 2: Group Data & Calculate Totals
        # -------------------------------------
        grouped_df = df.groupby(["Staff Customer", "Device Orders"])["Base"].sum().unstack(fill_value=0)

        # Ensure columns exist for both device types
        if "handheld" not in grouped_df.columns:
            grouped_df["handheld"] = 0
        if "pos" not in grouped_df.columns:
            grouped_df["pos"] = 0

        grouped_df = grouped_df.rename(columns={"handheld": "Handheld Total", "pos": "POS Total"}).reset_index()

        # Calculate numeric Percentage Handheld Use for sorting and further calculations
        grouped_df["Percentage Handheld Use Numeric"] = np.where(
            (grouped_df["Handheld Total"] + grouped_df["POS Total"]) == 0,
            0,
            (grouped_df["Handheld Total"] / (grouped_df["Handheld Total"] + grouped_df["POS Total"])) * 100
        ).round(2)

        # Format columns for display
        grouped_df["Handheld Total"] = grouped_df["Handheld Total"].map(lambda x: f"{x:,.2f}")
        grouped_df["POS Total"] = grouped_df["POS Total"].map(lambda x: f"{x:,.2f}")
        grouped_df["Percentage Handheld Use"] = grouped_df["Percentage Handheld Use Numeric"].map(lambda x: f"{x:.2f}%")

        # Calculate overall totals using raw numeric values (extracted from formatted strings)
        total_handheld = grouped_df["Handheld Total"].astype(str).str.replace(",", "").astype(float).sum()
        total_pos = grouped_df["POS Total"].astype(str).str.replace(",", "").astype(float).sum()
        overall_percentage = (total_handheld / (total_handheld + total_pos) * 100) if (total_handheld + total_pos) > 0 else 0

        # Create the summary row
        summary_row = pd.DataFrame({
            "Staff Customer": ["Overall Total"],
            "Handheld Total": [f"{total_handheld:,.2f}"],
            "POS Total": [f"{total_pos:,.2f}"],
            "Percentage Handheld Use Numeric": [overall_percentage],
            "Percentage Handheld Use": [f"{overall_percentage:.2f}%"]
        })

        # Exclude any preexisting summary rows and sort by the numeric percentage
        non_summary_df = grouped_df[grouped_df["Staff Customer"] != "Overall Total"]
        sorted_df = non_summary_df.sort_values(by="Percentage Handheld Use Numeric", ascending=False)
        final_df = pd.concat([sorted_df, summary_row], ignore_index=True)

        # ----------------------------
        # Step 2.5: Rename Output Column Titles
        # ----------------------------
        final_df = final_df.rename(columns={
            "Staff Customer": "Server",
            "Handheld Total": "Tablet Sales",
            "POS Total": "POS Sales",
            "Percentage Handheld Use Numeric": "Tablet Use Percentage (Numeric)",
            "Percentage Handheld Use": "Tablet Use Percentage"
        })

        # -------------------------------------
        # Step 3: Apply Conditional Formatting
        # -------------------------------------
        def highlight_row(row):
            if row["Server"] == "Overall Total":
                return ["background-color: blue; color: white; border: 2px solid black"] * len(row)
            percentage = row["Tablet Use Percentage (Numeric)"]
            if percentage >= 70:
                return ["background-color: green; color: white; border: 2px solid black"] * len(row)
            elif 50 <= percentage < 70:
                return ["background-color: yellow; color: black; border: 2px solid black"] * len(row)
            else:
                return ["background-color: red; color: white; border: 2px solid black"] * len(row)

        styled_display_df = final_df.style.apply(highlight_row, axis=1).set_properties(
            subset=["Tablet Use Percentage"], **{"text-align": "right"}
        ).set_properties(
            subset=["Tablet Sales", "POS Sales"], **{"text-align": "right"}
        )

        # Hide the "Tablet Use Percentage (Numeric)" column.
        # The rendered table includes the DataFrame index as the first column,
        # so the column order becomes:
        # 1: Index, 2: Server, 3: Tablet Sales, 4: POS Sales, 5: Tablet Use Percentage (Numeric), 6: Tablet Use Percentage.
        # We hide the 5th column.
        styled_display_df = styled_display_df.set_table_styles(
            [
                {'selector': 'th:nth-child(5)', 'props': [('display', 'none')]},
                {'selector': 'td:nth-child(5)', 'props': [('display', 'none')]}
            ]
        )

        # ----------------------------
        # Step 4: Provide CSV Download
        # ----------------------------
        output = io.BytesIO()
        final_df.to_csv(output, index=False, float_format="%.2f", lineterminator="\n")
        output.seek(0)
        st.download_button(
            label="Download Processed Report",
            data=output,
            file_name="processed_report.csv",
            mime="text/csv"
        )

        # -------------------------------------------------
        # Step 5: Display the Fully Expanded Color-Coded Table
        # -------------------------------------------------
        html_table = styled_display_df.to_html()
        st.markdown(html_table, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"An error occurred: {e}")
