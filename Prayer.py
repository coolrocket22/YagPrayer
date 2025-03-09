import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db, firestore
from datetime import datetime, timedelta, date
import uuid
import json

# Page structure
st.set_page_config("Prayer Intentions for YAG", layout="wide")

# Today's date
today = datetime.now().date()

# Expiry dictionary
expiry_dict = {
    "1 week": 7,
    "2 weeks": 14,
    "3 weeks": 21,
    "4 weeks": 28,
    "8 weeks": 56,
}


# Initialize Firebase Admin SDK with Streamlit secrets
firebase_config = dict(st.secrets["firebase_credentials"])
firebase_config["private_key"] = firebase_config["private_key"].replace('\\n', '\n')
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)

# Get a reference to the database
db = firestore.client()
prayer_collection_ref = db.collection('prayers')



# Database functions

# Function to read data from Firestore
def read_data():
    docs = prayer_collection_ref.stream()
    data = []
    
    for doc in docs:
        doc_dict = doc.to_dict()
        doc_dict['id'] = doc.id  # Store document ID for reference
        data.append(doc_dict)

    return data

# Add prayer function
@st.dialog("Add a prayer")
def addPrayer():
    name = st.text_input("Name")
    prayer = st.text_input("Prayer intention")
    datesubmitted = st.date_input("Date submitted", datetime.now().date())
    expiry = st.selectbox("Expiry date", expiry_dict.keys())
    expiry_date = datesubmitted + timedelta(expiry_dict[expiry])

    submitted = st.button("Submit")
    if submitted:
        formatted_datesubmitted = datesubmitted.strftime('%Y-%m-%d')
        formatted_expiry_date = expiry_date.strftime('%Y-%m-%d')

        new_prayer = {
            'Name': name,
            'Prayer': prayer,
            'Date submitted': formatted_datesubmitted,
            'Expiry date': formatted_expiry_date
        }
        prayer_collection_ref.add(new_prayer)
        st.success("Prayer added successfully!")
        st.rerun()

# Header
with st.container():
    st.title("Norwich YAG Prayer Database")

# Tabs
tab1, tab2, tab3 = st.tabs(["Prayer list", "Advanced Edit", "Output"])

# Load data from Firebase
prayer_data = read_data()
#st.write("Raw Firestore Data:", prayer_data)

# Convert the list of dictionaries to a Pandas DataFrame
df = pd.DataFrame(prayer_data)

# Ensure the DataFrame is not empty before proceeding
if not df.empty:
    # Convert date columns to datetime objects
    df['Date submitted'] = pd.to_datetime(df['Date submitted']).dt.date
    df['Expiry date'] = pd.to_datetime(df['Expiry date']).dt.date

df_display = df.drop(columns=['id'])
df_display = df_display[['Name', 'Prayer', 'Date submitted', 'Expiry date']]


with st.container():
    with tab1:
        df_sorted_active = df_display[df_display['Expiry date'] > today].sort_values(by='Date submitted', ascending=False).set_index('Name')
        st.dataframe(df_sorted_active,
                        use_container_width=True,
                        hide_index=False,
                        on_select="rerun",
                        selection_mode="single-row",
                        )

        if st.checkbox('Show expired prayer requests'):
            df_sorted_inactive = df_display[df_display['Expiry date'] < today].sort_values(by='Date submitted', ascending=False)
            st.dataframe(df_sorted_inactive, use_container_width=True, hide_index=True)

        st.button("Add prayer", on_click=addPrayer)

    with tab2:
        st.subheader("Advanced Edit")

        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False

        if not st.session_state.authenticated:
            password = st.text_input("Enter Admin Password:", type="password")
            if st.button("Authenticate"):
                if password == st.secrets["adminpass"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password")

        if st.session_state.authenticated:
            if 'advKey' not in st.session_state:
                st.session_state.advKey = str(uuid.uuid4())

            advanced_df = st.data_editor(df, num_rows="dynamic", key=st.session_state.advKey, use_container_width=True)

            def update_value():
                st.session_state.advKey = str(uuid.uuid4())

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Save"): #DOESN'T WORK YET
                    # Get the list of IDs in the original DataFrame (df)
                    original_ids = df['id'].tolist()

                    
                    # Get the list of IDs in the edited DataFrame (advanced_df)
                    updated_ids = advanced_df['id'].tolist()

                    # Track and delete rows from Firestore that have been deleted from advanced_df
                    for original_index, original_row in df.iterrows():
                        prayer_key = original_row['id']  # ID of the row in Firestore
                        
                        # If this row is in the original df but not in the advanced_df, it means it's deleted
                        if prayer_key not in updated_ids:
                            try:
                                # Delete this row from Firestore
                                prayer_collection_ref.document(prayer_key).delete()
                                st.success(f"Prayer with ID {prayer_key} deleted from Firestore.")
                            except Exception as e:
                                st.error(f"Error deleting prayer with ID {prayer_key}: {e}")
                    
                    # Now update the rows that are in both df and advanced_df
                    batch = db.batch()
                    for index, row in advanced_df.iterrows():
                        prayer_key = row['id']  # ID of the row in Firestore
                        
                        if prayer_key in original_ids:  # Update the existing prayer only if it exists in original data
                            try:
                                doc_ref = prayer_collection_ref.document(prayer_key)
                                
                                row_dict = row.to_dict()
                                row_dict["Date submitted"] = row_dict["Date submitted"].strftime('%Y-%m-%d')
                                row_dict["Expiry date"] = row_dict["Expiry date"].strftime('%Y-%m-%d')
                                row_dict.pop('id', None)
                                
                                print(prayer_key)
                                print(row_dict)
                                # Update the existing Firestore document
                                #prayer_collection_ref.document(prayer_key).update(row_dict, merge=True)
                                #update_prayer_collection_ref = prayer_collection_ref.document(prayer_key)
                                #update_prayer_collection_ref.update(row_dict)
                                #                                 
                                batch.set(doc_ref, row_dict, merge=True)
                            except Exception as e:
                                st.error(f"Error updating prayer with ID {prayer_key}: {e}")
                            
                    
                    batch.commit()
                    # Refresh the app to reload the latest data
                    st.rerun()

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
            message.append(f"🌹 This Week's Rosary Mystery: {current_mystery}")
            message.append("Active Prayer Requests:\n")
            for _, row in df.iterrows():
                message.append(f"🙏 {row['Name']} - {row['Prayer']}\n")
            return "\n".join(message)

        # Recalculate active prayers to ensure scope accessibility
        tab3_active_df = df[df['Expiry date'] > today].sort_values(by='Date submitted', ascending=False)

        if st.button("Generate WhatsApp Message"):
            st.session_state.whatsapp_message = generate_whatsapp_message(tab3_active_df)

        if 'whatsapp_message' in st.session_state:
            st.text_area("Copy this message:",
                        value=st.session_state.whatsapp_message,
                        height=300,
                        key="whatsapp_output")
        else:
            st.write("No prayer requests found.")
