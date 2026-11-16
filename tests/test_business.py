from decimal import Decimal

import pytest

from app.business import UngueltigeDaten, fortschritt_berechnen, menge_validieren, name_validieren
from app.models import Einkaufsartikel


@pytest.mark.parametrize("menge", [None, Decimal("1"), Decimal("0.5"), Decimal("1.125"), Decimal("1.500000"), Decimal("0.001"), Decimal("2.000000")])
def test_gueltige_menge(menge):
    assert menge_validieren(menge) == menge


@pytest.mark.parametrize("menge", ["0", "-1", "NaN", "Infinity"])
def test_ungueltige_menge(menge):
    with pytest.raises(UngueltigeDaten):
        menge_validieren(Decimal(menge))


@pytest.mark.parametrize("menge", ["1.1251", "0.0001", "1.2345000"])
def test_mehr_als_drei_nachkommastellen(menge):
    with pytest.raises(UngueltigeDaten, match="maximal drei Nachkommastellen"):
        menge_validieren(Decimal(menge))


@pytest.mark.parametrize("status, gekauft, prozent", [
    ([], 0, 0),
    ([False, False], 0, 0),
    ([True, False, False], 1, 33.3),
    ([True, True], 2, 100),
])
def test_fortschritt(status, gekauft, prozent):
    artikel = [Einkaufsartikel(name="Milch", gekauft=wert) for wert in status]
    fortschritt = fortschritt_berechnen(artikel)
    assert fortschritt.gesamt == len(status)
    assert fortschritt.gekauft == gekauft
    assert fortschritt.prozent == prozent


def test_name_wird_getrimmt():
    assert name_validieren("  Migros  ") == "Migros"
    with pytest.raises(UngueltigeDaten):
        name_validieren("   ")
