import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from datetime import datetime, timedelta, date
import uuid

#Page structure
st.set_page_config("Prayer Intentions for YAG", layout="wide")


#Database and dictionary
db = "Prayer intentions.pkl"
df = pd.read_pickle(db)
df['Date submitted'] = pd.to_datetime(df['Date submitted'])
df['Date submitted'] = df['Date submitted'].dt.date
df['Expiry date'] = pd.to_datetime(df['Expiry date'])
df['Expiry date'] = df['Expiry date'].dt.date


today = datetime.now().date()
expiry_dict = {
    "1 week": 7,
    "2 weeks": 14,
    "3 weeks": 21,
    "4 weeks": 28,
    "8 weeks": 56,
}

#Database functions
def dbAddPrayer(name, prayer, datesubmitted, expiry_date):
    df.loc[len(df.index)] = [name, prayer, datesubmitted, expiry_date]
    df.to_pickle(db)


#Add prayer function
@st.dialog("Add a prayer")
def addPrayer():
    name = st.text_input("Name")
    prayer = st.text_input("Prayer intention")
    datesubmitted = st.date_input("Date submitted", today)
    expiry = st.selectbox("Expiry date", expiry_dict.keys())
    expiry_date = datesubmitted + timedelta(expiry_dict[expiry])

    submitted = st.button("Submit")
    if submitted:
        dbAddPrayer(name, prayer, datesubmitted, expiry_date)

        st.session_state.addedprayer = {
            "name": name,
            "prayer": prayer,
            "datesubmit": datesubmitted,
            "expiry": expiry_date,
        }
        st.rerun()

@st.dialog("Edit prayer")
def editPrayer(input):
    return




#Header
with st.container():
    st.title("Norwich YAG Prayer Database")
    

#Tabs
tab1, tab2, tab3 = st.tabs(["Prayer list","Advanced Edit","Output"])
with st.container():
    with tab1:
        df_sorted_active = df[df['Expiry date'] > today].sort_values(by='Date submitted', ascending=False).set_index('Name')
        st.dataframe(df_sorted_active, 
                     use_container_width=True,
                     hide_index=False,
                     on_select="rerun",
                     selection_mode="single-row",
                     )

        if st.checkbox('Show inactive prayer requests'):
            df_sorted_inactive = df[df['Expiry date'] < today].sort_values(by='Date submitted', ascending=False)
            st.dataframe(df_sorted_inactive, use_container_width=True)

        st.button("Add prayer",on_click=addPrayer)


        if "addedprayer" in st.session_state:
            with st.container(border=True):
                st.write(f"The intention '{st.session_state.addedprayer['prayer']}' has been submitted for {st.session_state.addedprayer['name']} on {st.session_state.addedprayer['datesubmit']}.")
                st.write(f"Expiry is {st.session_state.addedprayer['expiry']}")


    with tab2:
        st.subheader("Advanced Edit")
        
        if 'authenticated' not in ss:
            ss.authenticated = False
            
        if not ss.authenticated:
            password = st.text_input("Enter Admin Password:", type="password")
            if st.button("Authenticate"):
                if password == "Yagadmin":
                    ss.authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password")
            
        if ss.authenticated:
            if 'advKey' not in ss:
                ss.advKey = str(uuid.uuid4())
                
            advanced_df = st.data_editor(df, num_rows="dynamic", key=ss.advKey, use_container_width=True)

            def update_value():
                ss.advKey = str(uuid.uuid4())

            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Save"):
                    advanced_df.to_pickle(db)
                    st.rerun()
            
            with col2:
                st.button("Restore Previous Version", on_click=update_value)
        


    with tab3:
        def generate_whatsapp_message(df):
            if df.empty:
                return "No active prayer requests currently"
            message = ["🌟 *YAG Prayer Update* 🌟\n"]
            message.append(f"Date: {datetime.now().date()}\n")
            
            # Weekly rotating rosary mysteries
            mysteries = ["Sorrowful", "Glorious", "Joyful", "Luminous"]
            current_week = datetime.now().isocalendar()[1]
            current_mystery = mysteries[current_week % 4]
            message.append(f"🌹 This Week's Rosary Mystery: {current_mystery}\n")
            
            message.append("Active Prayer Requests:\n")
            for _, row in df.iterrows():
                message.append(f"🙏 {row['Name']} - {row['Prayer']}\n")
            return "\n".join(message)
        
        # Recalculate active prayers to ensure scope accessibility
        tab3_active_df = df[df['Expiry date'] > today].sort_values(by='Date submitted', ascending=False)
        
        if st.button("Generate WhatsApp Message"):
            ss.whatsapp_message = generate_whatsapp_message(tab3_active_df)
            
        if 'whatsapp_message' in ss:
            st.text_area("Copy this message:",
                        value=ss.whatsapp_message,
                        height=300,
                        key="whatsapp_output")
