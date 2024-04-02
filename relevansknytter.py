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

def finn_emnekoder_og_aarstall_i_tekst(tekst):
    emnekoder_og_aarstall = []
    # Mønsteret søker etter emnekode på en linje, overser den neste linjen (beskrivelsen),
    # og fanger så opp årstallet og sesongen på den tredje linjen.
    mønster = re.compile(
        r'([A-ZÆØÅ]+\d{2,})\s*\r?\n.*\r?\n\s*(\d{4})\s*(Høst|Vår)',
        re.MULTILINE
    )

    funn = mønster.findall(tekst)
    for emnekode, aarstall, _ in funn:
        emnekoder_og_aarstall.append((emnekode, aarstall))

    return emnekoder_og_aarstall

pdf_fil = 'Resultater_fra_Vitnemalsportalen.pdf'
tekst = hent_tekst_fra_pdf(pdf_fil)
emnekoder_og_aarstall = finn_emnekoder_og_aarstall_i_tekst(tekst)
ord_liste = ["SIKT", "TJENESTELEVERANDØR", "KUNNSKAPSSEKTORENS"]
filtrert_tekst = filtrer_eksplisitte_ord(tekst, ord_liste)
emnekoder_fra_pdf = finn_emnekoder_i_tekst(filtrert_tekst)
print(emnekoder_fra_pdf)

def hent_emne_info(emnekode, aarstall):
    api_url = 'https://dbh.hkdir.no/api/Tabeller/hentJSONTabellData'
    query = {
        "tabell_id": 208,
        "api_versjon": 1,
        "statuslinje": "N",
        "decimal_separator": ".",
        "filter": [
            {
                "variabel": "Emnekode",
                "selection": {
                    "filter": "like",
                    "values": [emnekode + "%"]  # Legger til wildcard for å fange opp alle versjoner av emnekoden
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

    data_funnet, data = gjor_foresporsel(api_url, query)
    if data_funnet:
        return data
    else:
        return None

#emnekode_input = input("Vennligst skriv inn basis emnekode (uten versjon): ")
resultater = {}
for emnekode, aarstall in emnekoder_og_aarstall:
    data = hent_emne_info(emnekode, aarstall)
    if data:
        resultater[emnekode + " " + aarstall] = data

print(resultater) 
#hent_emne_info_grunnlag(emnekoder_fra_pdf)
