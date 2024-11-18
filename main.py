import os
import sys
import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar
import sqlite3
from collections import defaultdict
from datetime import datetime

# Funktion zum Abrufen des korrekten Pfads in der PyInstaller-Umgebung
def get_db_path():
    # Dynamisch den Pfad zur ausführbaren Datei abrufen
    if getattr(sys, 'frozen', False):
        # Wenn das Programm als .exe durch PyInstaller verpackt wurde
        base_path = sys._MEIPASS
    else:
        # Wenn das Programm als Python-Skript läuft
        base_path = os.path.dirname(os.path.abspath(__file__))

    # Verzeichnis für die Datenbank im Benutzerprofil abrufen
    user_documents = os.path.expanduser("~/Documents")
    db_directory = os.path.join(user_documents, "TaetigkeitsberichtData")

    # Erstelle das Verzeichnis, falls es nicht existiert
    if not os.path.exists(db_directory):
        os.makedirs(db_directory)

    db_path = os.path.join(db_directory, "taetigkeitsbericht.db")
    return db_path

# Pfad zur SQLite-Datenbank abrufen
db_path = get_db_path()

# Verbindung zur SQLite-Datenbank herstellen
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Tabelle erstellen (falls noch nicht vorhanden)
cursor.execute("""
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    ticket TEXT,
    school TEXT NOT NULL,
    task TEXT NOT NULL
)
""")
conn.commit()

# Schulen für Dropdown-Menü
schools = [
    "Allgemein", "FVM", "ODL", "RSU", "RSP", "GRG", "VIS", "GOL", "GPU",
    "MBG", "CSG", "GGZ", "BSF", "LWS", "FBF", "FOG", "PES", "EPS"
]

# Funktion zum Hinzufügen eines Eintrags in die Datenbank
def add_entry():
    selected_date = calendar.get_date()
    ticket = ticket_entry.get()
    school = school_dropdown.get()
    task = task_entry.get()

    if selected_date and school and task:
        cursor.execute(
            "INSERT INTO reports (date, ticket, school, task) VALUES (?, ?, ?, ?)",
            (selected_date, ticket or "Keine", school, task)
        )
        conn.commit()
        ticket_entry.delete(0, tk.END)
        task_entry.delete(0, tk.END)
        update_output()
        update_calendar()

# Funktion zum Abrufen und formatieren der Einträge
def update_output():
    selected_date = calendar.get_date()
    output_field.config(state="normal")  # Schreibschutz aufheben
    output_field.delete("1.0", tk.END)  # Alte Einträge löschen

    # Daten für das ausgewählte Datum abrufen
    cursor.execute("SELECT id, school, ticket, task FROM reports WHERE date = ?", (selected_date,))
    entries = cursor.fetchall()

    # Einträge nach Schule gruppieren
    grouped_entries = defaultdict(list)
    for entry_id, school, ticket, task in entries:
        grouped_entries[school].append((entry_id, ticket, task))

    # Schulen sortieren, Allgemein immer oben
    sorted_schools = sorted(grouped_entries.keys(), key=lambda x: ("Allgemein" != x, x))

    # Formatierte Ausgabe erstellen
    for school in sorted_schools:
        output_field.insert(tk.END, f"{school}:\n")
        for entry_id, ticket, task in grouped_entries[school]:
            if school == "Allgemein":
                output_field.insert(tk.END, f"- [{entry_id}] {task}\n")
            else:
                output_field.insert(tk.END, f"- [{entry_id}] Ticket [{ticket}]: {task}\n")
        output_field.insert(tk.END, "\n")  # Leerzeile zwischen Schulen
    output_field.config(state="disabled")  # Schreibschutz aktivieren

# Funktion zum Aktualisieren der Kalender-Markierungen
def update_calendar():
    calendar.calevent_remove("all")  # Alte Markierungen entfernen
    cursor.execute("SELECT DISTINCT date FROM reports")
    dates_with_entries = cursor.fetchall()
    for date_entry in dates_with_entries:
        date_str = date_entry[0]
        # String zu datetime.date konvertieren
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        calendar.calevent_create(date_obj, "Eintrag", "task")
    calendar.tag_config("task", background="lightblue", foreground="black")

# Funktion zum Exportieren der Berichte in ein neues Fenster
def export_report():
    selected_date = calendar.get_date()

    # Neues Fenster erstellen
    export_window = tk.Toplevel(root)
    export_window.title(f"Tätigkeitsbericht: {selected_date}")

    # Textfeld für die exportierten Berichte
    export_output = tk.Text(export_window, width=60, height=20, state="normal")
    export_output.grid(row=0, column=0, padx=10, pady=10)

    # Daten für das ausgewählte Datum abrufen
    cursor.execute("SELECT school, ticket, task FROM reports WHERE date = ?", (selected_date,))
    entries = cursor.fetchall()

    # Einträge nach Schule gruppieren
    grouped_entries = defaultdict(list)
    for school, ticket, task in entries:
        grouped_entries[school].append((ticket, task))

    # Schulen sortieren, Allgemein immer oben
    sorted_schools = sorted(grouped_entries.keys(), key=lambda x: ("Allgemein" != x, x))

    # Formatierte Ausgabe ohne IDs erstellen
    for school in sorted_schools:
        export_output.insert(tk.END, f"{school}:\n")
        for ticket, task in grouped_entries[school]:
            if school == "Allgemein":
                export_output.insert(tk.END, f"- {task}\n")
            else:
                export_output.insert(tk.END, f"- Ticket [{ticket}]: {task}\n")
        export_output.insert(tk.END, "\n")  # Leerzeile zwischen Schulen

    # Nur-Lese-Modus für das Textfeld aktivieren
    export_output.config(state="disabled")

# Funktion zum Löschen eines Eintrags anhand der ID
def delete_entry():
    try:
        entry_id = int(delete_entry_field.get())  # ID aus dem Eingabefeld
        cursor.execute("DELETE FROM reports WHERE id = ?", (entry_id,))
        conn.commit()
        delete_entry_field.delete(0, tk.END)
        update_output()
        update_calendar()
        status_label.config(text=f"Eintrag mit ID {entry_id} gelöscht.")
    except ValueError:
        status_label.config(text="Bitte eine gültige ID eingeben!")
    except sqlite3.Error as e:
        status_label.config(text=f"Fehler: {e}")

# GUI erstellen
root = tk.Tk()
root.title("Tätigkeitsbericht")

# Fenstergröße fixieren
root.resizable(width=False, height=False)

# Allgemeine Padding-Einstellungen
padding = {"padx": 10, "pady": 5}  # 10 Pixel horizontal, 5 Pixel vertikal

# Kalender
tk.Label(root, text="Tag auswählen:").grid(row=0, column=0, sticky="w", **padding)
calendar = Calendar(root, date_pattern="yyyy-MM-dd")
calendar.grid(row=0, column=1, **padding)
calendar.bind("<<CalendarSelected>>", lambda e: update_output())  # Aktualisierung bei Auswahl
update_calendar()

# Eingabefeld für Ticketnummer
tk.Label(root, text="Ticket Nr.:").grid(row=1, column=0, sticky="w", **padding)
ticket_entry = tk.Entry(root)
ticket_entry.grid(row=1, column=1, **padding)

# Dropdown für Schulen
tk.Label(root, text="Schule:").grid(row=2, column=0, sticky="w", **padding)
school_dropdown = ttk.Combobox(root, values=schools, state="readonly")
school_dropdown.grid(row=2, column=1, **padding)
school_dropdown.set("Allgemein")  # Standardauswahl

# Eingabefeld für Tätigkeit
tk.Label(root, text="Tätigkeit:").grid(row=3, column=0, sticky="nw", **padding)
task_entry = tk.Entry(root, width=50)
task_entry.grid(row=3, column=1, **padding)

# Button zum Hinzufügen
add_button = tk.Button(root, text="Hinzufügen", command=add_entry)
add_button.grid(row=4, column=1, sticky="e", **padding)

# Ausgabefeld für Berichte
tk.Label(root, text="Ausgabe:").grid(row=5, column=0, sticky="nw", **padding)
output_field = tk.Text(root, width=60, height=10)
output_field.grid(row=5, column=1, **padding)
output_field.config(state="disabled")  # Schreibschutz aktivieren

# Eingabefeld für Eintrags-ID
tk.Label(root, text="Eintrags-ID löschen:").grid(row=6, column=0, sticky="w", **padding)
delete_entry_field = tk.Entry(root)
delete_entry_field.grid(row=6, column=1, sticky="w", **padding)

# Button zum Löschen
delete_button = tk.Button(root, text="Löschen", command=delete_entry)
delete_button.grid(row=6, column=1, sticky="e", **padding)

# Export-Button
export_button = tk.Button(root, text="Exportieren", command=export_report)
export_button.grid(row=7, column=1, sticky="e", **padding)

# Statusanzeige
status_label = tk.Label(root, text="")
status_label.grid(row=8, column=0, columnspan=2, **padding)

# Ausgabe beim Start aktualisieren
update_output()

# Hauptloop starten
root.mainloop()

# Verbindung zur Datenbank schließen, wenn das Programm beendet wird
conn.close()
