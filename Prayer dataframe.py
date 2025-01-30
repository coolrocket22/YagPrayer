import pandas as pd

df = pd.DataFrame({
    'Name': ["Adriel", "Adela"],
    'Prayer': ["Test1","Test2"],
    'Date submitted': ['2024-09-02', '2024-09-02'],
    'Expiry date':['2024-09-09','2024-09-09'],
})

df.to_pickle("Prayer intentions.pkl")