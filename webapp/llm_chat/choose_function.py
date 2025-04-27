from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import google.generativeai as genai

genai.configure(api_key="AIzaSyBiMSDASMQ3IYmbd-Dckm2Cscq2mXFHVX8")

df = pd.read_csv("bookings.csv")
df['date'] = pd.to_datetime(df['date'])
df['day'] = df['date'].dt.day_name()


def plot_wochentag_verteilung(df, start_date=None, end_date=None):
    if start_date is None:
        start_date = (datetime.today() - timedelta(days=60)).date()
    if end_date is None:
        end_date = datetime.today().date()

    df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) & 
                     (df['date'] <= pd.to_datetime(end_date))]

    plt.figure(figsize=(8,5))
    df_filtered['day'].value_counts().reindex([
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
    ]).plot(kind='bar')

    start_str = start_date.strftime('%d.%m.%Y')
    end_str = end_date.strftime('%d.%m.%Y')
    plt.title(f'Anwesenheiten pro Wochentag ({start_str} bis {end_str})')
    plt.ylabel("Anzahl Buchungen")
    plt.tight_layout()
    plt.show()


def plot_woechentliche_anwesenheiten(df, start_date=None, end_date=None):
    if start_date is None:
        start_date = (datetime.today() - timedelta(days=60)).date()
    if end_date is None:
        end_date = datetime.today().date()

    df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) & 
                     (df['date'] <= pd.to_datetime(end_date))]
    df_filtered['week'] = df_filtered['date'].dt.to_period('W').astype(str)

    weekly_counts = df_filtered.groupby('week').size()
    plt.figure(figsize=(10,5))
    weekly_counts.plot(kind='line', marker='o')

    start_str = start_date.strftime('%d.%m.%Y')
    end_str = end_date.strftime('%d.%m.%Y')
    plt.title(f'Summe der Anwesenheiten pro Woche ({start_str} bis {end_str})')
    plt.ylabel("Anzahl Buchungen")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def call_llm_and_execute(question):
    prompt = f"""
        Ich habe folgende Funktionen zur Verfügung:

        1. plot_wochentag_verteilung(df, start_date=None, end_date=None)
        - Plottet die Verteilung der Buchungen pro Wochentag in einem gegebenen Zeitraum.

        2. plot_woechentliche_anwesenheiten(df, start_date=None, end_date=None)
        - Plottet die Summe der Buchungen pro Woche in einem gegebenen Zeitraum.

        Ich möchte nun basierend auf der folgenden Nutzerfrage entscheiden, welche Funktion ich aufrufe und mit welchen Parametern:

        Frage: "{question}"

        Bitte gib eine Python-Funktionszeile zurück, wie z.B.:
        plot_wochentag_verteilung(start_date=datetime.today() - timedelta(days=30))

        Nur den Funktionsaufruf – kein Text, keine Erklärung.
        """

    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt)
    code = response.text.strip('` \n')
    print(">> LLM-Antwort:", code)

    try:
        result = eval(code)
        return result
    except Exception as e:
        return f"Fehler beim Ausführen: {e}"


frage = "Zeig mir die Verteilung pro Wochentag in den letzten 2 Monaten"
antwort = call_llm_and_execute(frage)
print(antwort)