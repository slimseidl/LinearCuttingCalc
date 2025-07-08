import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go
import pyodbc

# ================================================
# Helper Functions
# ================================================

# --- Convert feet + inches to total inches ---
def to_inches(feet, inches):
    return feet * 12 + inches

# --- Convert total inches to feet + inches (string format) ---
def to_feet_inches(inches):
    feet = int(inches) // 12
    remaining_inches = round(inches - feet * 12, 2)
    return f"{feet}' {remaining_inches}\""

# --- Greedy Cut Optimization using First-Fit Decreasing algorithm ---
# This function takes available stock lengths and the required cuts
# and assigns the cuts to stock pieces minimizing waste.
def optimize_cuts(stock_lengths, cuts):
    # Sort cuts from longest to shortest
    cuts = sorted(cuts, key=lambda x: x[0], reverse=True)
    layouts = []

    # Create pool of all available stock pieces
    stock_pool = []
    for length, qty in stock_lengths:
        stock_pool.extend([length] * qty)

    # Create layout containers for each stock piece
    for stock in stock_pool:
        layouts.append({"stock_length": stock, "cuts": []})

    # Attempt to place each cut in an existing layout
    for length, qty, label, jobnum, asmseq in cuts:
        for _ in range(int(qty)):
            placed = False
            for layout in layouts:
                used = sum([c[0] for c in layout["cuts"]])
                if used + length <= layout["stock_length"]:
                    layout["cuts"].append((length, label, jobnum, asmseq))
                    placed = True
                    break
            if not placed:
                break

    return layouts

# --- Optimization by total linear inventory ---
# Useful when you want to optimize from a bulk inventory instead of discrete pieces.
def optimize_by_total_inventory(total_inches, stock_length, cuts):
    max_pieces = total_inches // stock_length
    stock_lengths = [(stock_length, int(max_pieces))]
    return optimize_cuts(stock_lengths, cuts)

# ================================================
# Visualization of Cut Layouts
# ================================================

# --- Display the layout using plotly and Streamlit ---
def display_layout(layouts):
    any_displayed = False
    for i, layout in enumerate(layouts):
        if not layout["cuts"]:
            continue

        any_displayed = True
        stock_length = layout["stock_length"]

        st.markdown(f"### Layout {chr(65 + i)}")
        st.write(f"Stock Length: {to_feet_inches(stock_length)}")

        # Create a dataframe for this layout
        df = pd.DataFrame(layout["cuts"], columns=["Length", "Label", "JobNum", "AsmSeq"])
        df["CombinedLabel"] = df.apply(lambda row: f"{row['Label']}\nJob: {row['JobNum']}\nAsm: {row['AsmSeq']}", axis=1)

        # Summarize the part details for display
        part_summary = df.groupby(["Length", "Label", "JobNum", "AsmSeq"]).size().reset_index(name="Qty")
        part_summary["Length (ft/in)"] = part_summary["Length"].apply(to_feet_inches)
        st.dataframe(part_summary[["Length (ft/in)", "Label", "JobNum", "AsmSeq", "Qty"]])

        # Calculate waste for this layout
        waste = stock_length - sum(df["Length"])
        st.write(f"Material remnant: {to_feet_inches(waste)}")

        # Plot horizontal bar chart
        fig = go.Figure(layout=dict(margin=dict(l=60, r=60, t=30, b=30), autosize=False, width=1400))
        for j, row in df.iterrows():
            fig.add_trace(go.Bar(
                x=[row["Length"]],
                y=["Layout " + chr(65 + i)],
                orientation='h',
                name=row["CombinedLabel"],
                text=row["CombinedLabel"] + f"\n{to_feet_inches(row['Length'])}",
                textposition='inside',
                insidetextanchor='start',
                hoverinfo='text',
                marker=dict(line=dict(width=1))
            ))

        # Add waste section if needed
        if waste > 0:
            fig.add_trace(go.Bar(
                x=[waste],
                y=["Layout " + chr(65 + i)],
                orientation='h',
                name="Waste",
                marker=dict(color="lightgray"),
                text="Remnant",
                textposition='inside'
            ))

        fig.update_layout(
            barmode='stack',
            showlegend=False,
            height=350,
            xaxis=dict(title=dict(text="Length (in)", font=dict(size=18)), showgrid=True, tickfont=dict(size=16)),
            yaxis=dict(title="", tickfont=dict(size=16))
        )
        st.plotly_chart(fig, use_container_width=True)

    if not any_displayed:
        st.warning("None of the cuts fit within the available stock length.")

# ================================================
# Streamlit App Interface
# ================================================

st.title("Linear Cutting Calculator")

# User chooses input method
method = st.sidebar.radio("Input Method", ["Manual Entry", "Upload CSV", "Load from Epicor SQL"], index=2)

# Keep session state for all materials and their cut details
if "cuts_by_material" not in st.session_state:
    st.session_state["cuts_by_material"] = {}

# --------------------------------------------
# Load data from Epicor SQL if selected
# --------------------------------------------
if method == "Load from Epicor SQL":
    if st.button("Refresh from Epicor SQL"):
        try:
            # Use secret connection string
            from app_secrets import conn_str
            conn = pyodbc.connect(conn_str)

            # Read SQL from file
            with open("query.sql", "r") as file:
                sql = file.read()
            df = pd.read_sql(sql, conn)

            # Filter only jobs starting in next 15 days
            df = df[pd.to_datetime(df['JobOper_StartDate']).dt.date <= pd.Timestamp.today().date() + pd.Timedelta(days=15)]

            # Calculate needed fields
            df["CutQty"] = df["JobMtl_RequiredQty"]
            df["RunQty"] = df["JobOper_RunQty"]
            df["Length"] = df["CutQty"] / 18.97 * 12
            df["TotalQty"] = df["RunQty"]
            df["Label"] = df["JobAsmbl_Description"]
            df["EarliestStart"] = pd.to_datetime(df['JobOper_StartDate']).dt.date

            # Group by material part number
            grouped = df.groupby("JobMtl_PartNum")
            cuts_by_material = {
                material: (
                    list(zip(group["Length"], group["TotalQty"], group["Label"], group["JobHead_JobNum"], group["JobOper_AssemblySeq"])),
                    group["EarliestStart"].min(),
                    group["JobMtl_Description"].iloc[0]
                )
                for material, group in grouped
            }

            # Store in session in order of earliest start date
            sorted_materials = sorted(cuts_by_material.items(), key=lambda x: x[1][1])
            st.session_state["cuts_by_material"] = {material: data for material, data in sorted_materials}

            st.success("Loaded materials: " + str(len(st.session_state["cuts_by_material"])))

        except Exception as e:
            st.error(f"Failed to load data from SQL: {e}")

# ================================================
# Optimizer UI for each material
# ================================================

if st.session_state["cuts_by_material"]:
    last_optimized = st.session_state.get("last_optimized", None)

    for material, (cuts, start_date, mtl_desc) in st.session_state["cuts_by_material"].items():
        is_expanded = (material == last_optimized)
        total_qty = sum([int(qty) for length, qty, label, jobnum, asmseq in cuts])

        with st.expander(f"Material: {material} - {mtl_desc} ({total_qty} cuts, Start: {start_date})", expanded=is_expanded):
            st.write("### Add Stock Lengths")

            # Choose optimization mode: discrete lengths vs total inventory
            mode = st.radio("Optimization Mode", ["Fixed Stock Lengths", "Total Linear Inventory"], key=f"mode_{material}")

            if mode == "Fixed Stock Lengths":
                stock_entries = st.session_state.get(f"stock_entries_{material}", [(21, 0, 1)])
                updated_stock_entries = []

                for i, (ft, inch, qty) in enumerate(stock_entries):
                    cols = st.columns(3)
                    ft_val = cols[0].number_input(f"Length {i+1} - Feet", value=ft, key=f"ft_{material}_{i}")
                    inch_val = cols[1].number_input(f"Inches", value=inch, key=f"in_{material}_{i}")
                    qty_val = cols[2].number_input(f"Qty", value=qty, key=f"qty_{material}_{i}")
                    updated_stock_entries.append((ft_val, inch_val, qty_val))

                # Add another stock length row
                if st.button(f"+ Add Another Length", key=f"add_{material}"):
                    updated_stock_entries.append((0, 0, 1))

                st.session_state[f"stock_entries_{material}"] = updated_stock_entries

                # Run optimization
                if st.button(f"Optimize {material}", key=f"btn_{material}"):
                    st.session_state["last_optimized"] = material
                    stock_lengths = [(to_inches(ft, inch), qty) for ft, inch, qty in updated_stock_entries]
                    layouts = optimize_cuts(stock_lengths, cuts)
                    st.write(f"Total stock used: **{len([l for l in layouts if l['cuts']])} pieces**")
                    display_layout(layouts)

            elif mode == "Total Linear Inventory":
                ft = st.number_input("Total Linear Feet", value=400, key=f"lin_ft_{material}")
                stock_len_ft = st.number_input("Stock Length (Feet)", value=21, key=f"lin_stock_{material}")
                total_inches = to_inches(ft, 0)
                stock_length = to_inches(stock_len_ft, 0)

                # Run optimization using total available linear feet
                if st.button(f"Optimize {material} (by inventory)", key=f"btn_inv_{material}"):
                    st.session_state["last_optimized"] = material
                    layouts = optimize_by_total_inventory(total_inches, stock_length, cuts)
                    st.write(f"Total stock used: **{len([l for l in layouts if l['cuts']])} pieces**")
                    display_layout(layouts)
else:
    st.info("Load data to begin optimizing.")
