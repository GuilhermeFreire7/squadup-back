from app.services.geo import haversine_km


def test_haversine_returns_zero_for_same_point() -> None:
    distance = haversine_km(-22.9519, -43.1889, -22.9519, -43.1889)

    assert distance == 0.0


def test_haversine_returns_known_distance_between_rio_landmarks() -> None:
    # Praia de Botafogo -> Praia de Copacabana, ~2km em linha reta.
    botafogo = (-22.9519, -43.1889)
    copacabana = (-22.9711, -43.1822)

    distance = haversine_km(*botafogo, *copacabana)

    assert 1.5 < distance < 3.0


def test_haversine_is_symmetric() -> None:
    a = (-22.9519, -43.1889)
    b = (-22.9711, -43.1822)

    assert haversine_km(*a, *b) == haversine_km(*b, *a)
