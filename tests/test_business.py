from app.business import restmenge_berechnen, status_berechnen
from app.models import Einkaufsartikel


def test_status_aus_gespeicherten_werten():
    artikel = Einkaufsartikel(name="Kartoffeln", menge=3, gekaufte_menge=0, gekauft=False)
    assert status_berechnen(artikel) == "offen"

    artikel.gekaufte_menge = 2
    assert status_berechnen(artikel) == "teilweise_gekauft"

    artikel.gekauft = True
    assert status_berechnen(artikel) == "gekauft"


def test_restmenge_aus_geplanter_und_gekaufter_menge():
    artikel = Einkaufsartikel(name="Reis", menge=3, gekaufte_menge=2)
    assert restmenge_berechnen(artikel) == 1
    artikel.menge = None
    assert restmenge_berechnen(artikel) is None
