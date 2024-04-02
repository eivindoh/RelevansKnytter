import requests
import fitz  # PyMuPDF
import re

def gjor_foresporsel(api_url, query):
    response = requests.post(api_url, json=query)
    if response.status_code == 200:
        try:
            data = response.json()
            if data:  # Sjekker om listen er tom
                return True, data
        except requests.exceptions.JSONDecodeError:
            print("Kunne ikke dekode JSON.")
    return False, None

def hent_tekst_fra_pdf(pdf_fil):
    doc = fitz.open(pdf_fil)
    samlet_tekst = ""
    for side in doc:
        samlet_tekst += side.get_text("text")
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

pdf_fil = 'Resultater_fra_Vitnemalsportalen.pdf'
tekst = hent_tekst_fra_pdf(pdf_fil)
ord_liste = ["SIKT", "TJENESTELEVERANDØR", "KUNNSKAPSSEKTORENS"]
filtrert_tekst = filtrer_eksplisitte_ord(tekst, ord_liste)
emnekoder_fra_pdf = finn_emnekoder_i_tekst(filtrert_tekst)
print(emnekoder_fra_pdf)

def hent_emne_info_grunnlag(emnekode_grunnlag):
    api_url = 'https://dbh.hkdir.no/api/Tabeller/hentJSONTabellData'
    versjon = 0  # Starter med 0 for å sjekke grunnlaget først
    fant_data = False

    while True:
        full_emnekode = f"{emnekode_grunnlag}" if versjon == 0 else f"{emnekode_grunnlag}-{versjon}"
        query = {
            "tabell_id": 208,
            "api_versjon": 1,
            "statuslinje": "N",
            "decimal_separator": ".",
            "filter": [
                {
                    "variabel": "Emnekode",
                    "selection": {
                        "filter": "item",
                        "values": [full_emnekode]
                    }
                }
            ]
        }

        data_funnet, data = gjor_foresporsel(api_url, query)

        if data_funnet:
            print(f"Data funnet for {full_emnekode}: {data}")
            fant_data = True  # Markerer at vi har funnet data
        else:
            if fant_data:  # Hvis vi tidligere har funnet data, men nå får tom respons
                print(f"Ingen flere data funnet etter {full_emnekode}. Stoppet søket.")
                break  # Avslutter søket etter første tomme respons etter å ha funnet data
            elif versjon == 0:
                versjon += 1  # Prøver -1 versjonen hvis den opprinnelige forespørselen var tom
                continue
            else:
                print(f"Ingen data funnet for {emnekode_grunnlag} og ingen versjoner funnet.")
                break  # Avslutter hvis både den opprinnelige og -1 versjonen er tomme

        versjon += 1  # Øker versjonen for neste iterasjon

#emnekode_input = input("Vennligst skriv inn basis emnekode (uten versjon): ")
for emnekode in emnekoder_fra_pdf:
    hent_emne_info_grunnlag(emnekode)        
#hent_emne_info_grunnlag(emnekoder_fra_pdf)
