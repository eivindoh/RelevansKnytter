import requests
import fitz  # PyMuPDF
import re
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QFileDialog, QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Emneinfo Viewer")
        self.setGeometry(100, 100, 1000, 800)
        
        layout = QVBoxLayout()
        
        self.button = QPushButton("Velg PDF-fil")
        self.button.clicked.connect(self.velg_pdf_fil)
        layout.addWidget(self.button)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)  # Antall kolonner i tabellen
        self.table.setHorizontalHeaderLabels(["Emnekode", "Årstall", "Emnenavn", "Studiepoeng", "Nivåkode"])
        layout.addWidget(self.table)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
    
    def velg_pdf_fil(self):
        filnavn, _ = QFileDialog.getOpenFileName(self, "Åpne PDF-fil", "", "PDF-filer (*.pdf)")
        if filnavn:
            self.behandle_pdf_fil(filnavn)
    
    def behandle_pdf_fil(self, filnavn):
        emnekoder_og_aarstall = self.finn_emnekoder_og_aarstall_i_tekst(self.hent_tekst_fra_pdf(filnavn))
        unike_data = {}  # Bruk en ordbok for å holde styr på unike kombinasjoner av emnekode og årstall

        for emnekode, aarstall in emnekoder_og_aarstall:
            data = self.hent_emne_info(emnekode, aarstall)
            if data:
                for item in data:
                    key = (item['Emnekode'], item['Årstall'])
                    if key not in unike_data:  # Sjekker om nøkkelen allerede eksisterer
                        unike_data[key] = item  # Lagrer kun den første forekomsten

        data_for_tabell = [
            (emnekode, aarstall, item['Emnenavn'], item['Studiepoeng'], item['Nivåkode'])
            for (emnekode, aarstall), item in unike_data.items()
        ]

        self.oppdater_tabell(data_for_tabell)
                    
    
    def oppdater_tabell(self, data):
        self.table.setRowCount(len(data))  # Setter antall rader basert på antall datasett
        for row, (emnekode, aarstall, emnenavn, studiepoeng, nivakode) in enumerate(data):
            # Legger til dataene i hver celle i tabellen
            self.table.setItem(row, 0, QTableWidgetItem(emnekode))
            self.table.setItem(row, 1, QTableWidgetItem(aarstall))
            self.table.setItem(row, 2, QTableWidgetItem(emnenavn))
            self.table.setItem(row, 3, QTableWidgetItem(studiepoeng))
            self.table.setItem(row, 4, QTableWidgetItem(nivakode))
        self.table.sortByColumn(1, Qt.SortOrder(0))

    def gjor_foresporsel(self, api_url, query):
        response = requests.post(api_url, json=query)
        if response.status_code == 200:
            try:
                data = response.json()
                if data:  # Sjekker om listen er tom
                    return True, data
            except requests.exceptions.JSONDecodeError:
                print("Kunne ikke dekode JSON.")
        return False, None

    def hent_tekst_fra_pdf(self, pdf_fil):
        doc = fitz.open(pdf_fil)
        samlet_tekst = ""
        for side in doc:
            samlet_tekst += side.get_text("text")
        print(f"Tekst fra pdf i fullformat: {samlet_tekst}")
        return samlet_tekst

    def filtrer_eksplisitte_ord(tekst, ord_liste):
        for ord in ord_liste:
            tekst = re.sub(f'\\b{ord}\\b', '', tekst, flags=re.IGNORECASE)
        
        return tekst

    def finn_emnekoder_i_tekst(tekst):
        emnekoder_fra_pdf = []
        # Regulært uttrykk som matcher din beskrivelse
        pattern = re.compile(r'\b([A-ZÆØÅ]{2,}\d+[A-ZÆØÅ\d]*)|([A-ZÆØÅ]{4,})\b')
        funn = pattern.findall(tekst)
        for gruppe in funn:
            # Velger den første matchen (enten det er en kombinasjon av bokstaver og tall, eller kun bokstaver)
            kode = gruppe[0] if gruppe[0] else gruppe[1]
            if kode:  # Sjekker at vi faktisk har en kode
                emnekoder_fra_pdf.append(kode)
        return list(set(emnekoder_fra_pdf))  # Fjerner duplikater

    def finn_emnekoder_og_aarstall_i_tekst(self, tekst):
        emnekoder_og_aarstall = []
        semester_mønster = re.compile(r'(\d{4})\s*(Høst|Vår)')
        semester_funn = semester_mønster.finditer(tekst)

        for match in semester_funn:
            aarstall, semester = match.groups()
            # Søk bakover fra starten av semester-matchen
            tekst_bakover = tekst[:match.start()]
            emnekode_mønster = re.compile(r'\b([A-ZÆØÅ\d\-]+)\b')
            emnekode_funn = list(emnekode_mønster.finditer(tekst_bakover))
            
            ord_telt = 0
            linjer_telt = 0

            for emnekode_match in reversed(emnekode_funn):
                emnekode = emnekode_match.group()
                if len(re.findall(r'[A-ZÆØÅ]', emnekode)) >= 3 and re.search(r'\d', emnekode):
                    emnekoder_og_aarstall.append((emnekode, aarstall))
                    break  # Stopp når en gyldig kode er funnet
                ord_telt += len(emnekode.split())
                linjer_telt += emnekode.count('\n')
                # Avbryt søket hvis vi har telt mer enn 25 ord eller 3 linjeskift
                if ord_telt > 25 or linjer_telt >= 3:
                    break

        print(f"Antatte emnekoder og årstall: {emnekoder_og_aarstall}")
        return emnekoder_og_aarstall

#Finn Høst og Vår. Gå bakover til vi finner et ord som inneholder mist tre store bokstaver og ingen små bokstaver. Dette er emnekoden.

   # pdf_fil = 'Resultater_fra_Vitnemalsportalen.pdf'
   # tekst = hent_tekst_fra_pdf(pdf_fil)
   # emnekoder_og_aarstall = finn_emnekoder_og_aarstall_i_tekst(tekst)
   # ord_liste = ["SIKT", "TJENESTELEVERANDØR", "KUNNSKAPSSEKTORENS"]
    #filtrert_tekst = filtrer_eksplisitte_ord(tekst, ord_liste)
   # emnekoder_fra_pdf = finn_emnekoder_i_tekst(filtrert_tekst)
   # print(emnekoder_fra_pdf)

    def hent_emne_info(self, emnekode, aarstall):
        api_url = 'https://dbh.hkdir.no/api/Tabeller/hentJSONTabellData'
        query = {
            "tabell_id": 208,
            "api_versjon": 1,
            "filter": [
                {
                    "variabel": "Emnekode",
                    "selection": {
                        "filter": "like",
                        "values": [emnekode + "-%"]  # Legger til wildcard for å fange opp alle versjoner av emnekoden
                    }
                },
                {
                    "variabel": "Årstall",
                    "selection": {
                        "filter": "item",
                        "values": [aarstall]  # Inkluderer årstallet som en del av spørringen
                    }
                }
            ]
        }

        data_funnet, data = self.gjor_foresporsel(api_url, query)
        return data if data_funnet else []

    #emnekode_input = input("Vennligst skriv inn basis emnekode (uten versjon): ")
    #resultater = {}
    #for emnekode, aarstall in emnekoder_og_aarstall:
    #    data = hent_emne_info(emnekode, aarstall)
    #    if data:
    #        resultater[emnekode + " " + aarstall] = data

    #print(resultater) 
    #hent_emne_info_grunnlag(emnekoder_fra_pdf)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
