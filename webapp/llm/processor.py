from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import google.generativeai as genai


from .analytics.employee import get_avg_booking_per_employee, get_booking_clusters, get_booking_repeat_pattern, get_booking_repeat_pattern_plot


genai.configure(api_key="AIzaSyBiMSDASMQ3IYmbd-Dckm2Cscq2mXFHVX8")



def call_llm_and_execute(question):
    prompt = f"""
        Ich habe folgende Funktionen zur Verfügung:

        1. get_avg_booking_per_employee(granularity="week", weekdays=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],start_date=None, end_date=None)
        - Berechnet die durchschnittliche Anzahl an Buchungen pro Mitarbeiter.


        2. get_booking_repeat_pattern(min_repeat_count=2, weekdays=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], start_date=None, end_date=None)
        - Identifiziert Benutzer, die dieselben Schreibtische wiederholt buchen.

        3. get_booking_clusters(distance_threshold=3, co_booking_count_min, weekdays=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], start_date=None, end_date=None)
        - Findet Buchungscluster, d. h. Gruppen von Benutzern, die häufig nahe gelegene Schreibtische buchen.

        4. get_booking_repeat_pattern_plot(distance_threshold=3, co_booking_count_min, weekdays=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], start_date=None, end_date=None)
        - Plottet Buchungscluster von Gruppen, die häufig nahe gelegene Schreibtische buchen.


        Ich möchte nun basierend auf der folgenden Nutzerfrage entscheiden, welche Funktion ich aufrufe und mit welchen Parametern:

        Frage: "{question}"

        Bitte gib eine Python-Funktionszeile zurück, wie z.B.:
        plot_wochentag_verteilung(start_date=datetime.today() - timedelta(days=30))

        Nur den Funktionsaufruf – kein Text, keine Erklärung.
        """

    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt)
    code = response.text.strip('` \n')

    try:
        result = eval(code)
        print(result)
        promt_2 = f"""
             Ich habe eine Frage "{question}". Diese wurde bereits verarbeitet mit folgender Antowrt "{result["html"]}". 
             Bitte gib einen kurzen Text zu der Antwort aus. Falls bei der Antwort ein Fehler vorhanden ist,
             dann soll eine andere Frage gestellt werden.
             Fasse dich sehr kurz! 
             Wenn du keine Antwort erhälts, dann gebe nichts zurück, keine Rückfragen und auch keine alternativen!
             """
        
        llm_text = model.generate_content(promt_2)
        result["text"] = llm_text.candidates[0].content.parts[0].text
        return result
    except Exception as e:
        return f"Fehler beim Ausführen: {e}"

