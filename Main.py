import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go

# --- Convert Feet + Inches to Inches ---
def to_inches(feet, inches):
    return feet * 12 + inches

# --- Convert Inches to Feet and Inches (for display) ---
def to_feet_inches(inches):
    feet = int(inches) // 12
    remaining_inches = round(inches - feet * 12, 2)
    return f"{feet}' {remaining_inches}\""

# --- Greedy Cut Optimization (First Fit Decreasing) ---
def optimize_cuts(stock_length, cuts, stock_qty):
    cuts = sorted(cuts, key=lambda x: x[0], reverse=True)
    layouts = [[] for _ in range(stock_qty)]

    for length, qty, label in cuts:
        for _ in range(qty):
            placed = False
            for layout in layouts:
                used = sum([c[0] for c in layout])
                if used + length <= stock_length:
                    layout.append((length, label))
                    placed = True
                    break
            if not placed:
                layouts.append([(length, label)])

    return layouts

# --- Visualization Helper ---
def display_layout(layouts, stock_length):
    for i, layout in enumerate(layouts):
        if not layout:
            continue

        st.markdown(f"### Layout {chr(65 + i)}")
        st.write(f"Stock Length: {to_feet_inches(stock_length)}")

        df = pd.DataFrame(layout, columns=["Length", "Label"])
        part_summary = df.groupby(["Length", "Label"]).size().reset_index(name="Qty")
        part_summary["Length (ft/in)"] = part_summary["Length"].apply(to_feet_inches)
        st.dataframe(part_summary[["Length (ft/in)", "Label", "Qty"]])

        waste = stock_length - sum(df["Length"])
        st.write(f"Material remnant: {to_feet_inches(waste)}")

        # Plotly bar layout
        fig = go.Figure(layout=dict(margin=dict(l=60, r=60, t=30, b=30), autosize=False, width=1400))
        for j, row in df.iterrows():
            fig.add_trace(go.Bar(
                x=[row["Length"]],
                y=["Layout " + chr(65 + i)],
                orientation='h',
                name=row["Label"],
                text=f"{row['Label']}\n{to_feet_inches(row['Length'])}",
                textposition='inside',
                insidetextanchor='start',
                hoverinfo='text',
                marker=dict(line=dict(width=1))
            ))

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

# --- Streamlit UI ---
st.title("Linear Cutting Calculator")

st.sidebar.header("Cutting Inputs")
use_ft_in = st.sidebar.checkbox("Enter lengths in feet & inches", value=True)

if use_ft_in:
    stock_feet = st.sidebar.number_input("Stock Length - Feet", min_value=0, value=21)
    stock_inches = st.sidebar.number_input("Stock Length - Inches", min_value=0, value=0)
    stock_length = to_inches(stock_feet, stock_inches)
else:
    stock_length = st.sidebar.number_input("Stock Length (in)", min_value=1, value=252)

stock_qty = st.sidebar.number_input("Number of Stock Pieces", min_value=1, value=1)

# Upload CSV or manually enter
method = st.sidebar.radio("Input Method", ["Manual Entry", "Upload CSV"])

cuts = []
if method == "Manual Entry":
    num_rows = st.sidebar.number_input("# of Cut Sizes", min_value=1, max_value=50, value=5)
    for i in range(num_rows):
        st.markdown(f"#### Cut #{i+1}")
        col1, col2, col3, col4 = st.columns([1,1,1,2])
        if use_ft_in:
            with col1:
                feet = st.number_input(f"Feet #{i+1}", min_value=0, key=f"ft_{i}")
            with col2:
                inches = st.number_input(f"Inches #{i+1}", min_value=0.0, key=f"in_{i}")
            length = to_inches(feet, inches)
        else:
            with col1:
                length = st.number_input(f"Length #{i+1} (in)", min_value=0.0, key=f"len_{i}")
        with col3:
            qty = st.number_input(f"Qty #{i+1}", min_value=1, key=f"qty_{i}")
        with col4:
            label = st.text_input(f"Label #{i+1}", value=f"Part {i+1}", key=f"label_{i}")
        cuts.append((length, qty, label))

else:
    uploaded_file = st.sidebar.file_uploader("Upload CSV (length, qty, label)", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        if len(df.columns) >= 3:
            cuts = list(zip(df.iloc[:, 0], df.iloc[:, 1], df.iloc[:, 2]))
        else:
            st.error("CSV must have three columns: length, qty, label")

# --- Run Optimizer ---
if st.button("Optimize Cuts") and cuts:
    layouts = optimize_cuts(stock_length, cuts, stock_qty)

    st.subheader("Optimized Layouts")
    st.write(f"Total stock used: **{len([l for l in layouts if l])} / {stock_qty} available**")

    display_layout(layouts, stock_length)
else:
    st.info("Enter cut sizes and click 'Optimize Cuts'")
