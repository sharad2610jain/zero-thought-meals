from models import MealResponse
from history import list_history, save_generation, toggle_favorite


def _response(food_detected=False):
    return MealResponse(food_detected=food_detected, ingredients_detected=["eggs"] if food_detected else [])


def test_save_and_list_history_round_trips(tmp_path):
    db_path = str(tmp_path / "history.db")

    save_generation(_response(), db_path=db_path, created_at="2026-08-17T10:00:00+00:00")
    save_generation(_response(), db_path=db_path, created_at="2026-08-17T11:00:00+00:00")

    entries = list_history(db_path=db_path)

    assert len(entries) == 2
    # Most recent first.
    assert entries[0]["created_at"] == "2026-08-17T11:00:00+00:00"
    assert entries[1]["created_at"] == "2026-08-17T10:00:00+00:00"
    assert isinstance(entries[0]["response"], MealResponse)
    assert entries[0]["favorite"] is False


def test_list_history_respects_limit(tmp_path):
    db_path = str(tmp_path / "history.db")
    for i in range(5):
        save_generation(_response(), db_path=db_path, created_at=f"2026-08-17T{i:02d}:00:00+00:00")

    entries = list_history(db_path=db_path, limit=2)

    assert len(entries) == 2


def test_toggle_favorite_flips_state(tmp_path):
    db_path = str(tmp_path / "history.db")
    entry_id = save_generation(_response(), db_path=db_path, created_at="2026-08-17T10:00:00+00:00")

    toggle_favorite(entry_id, db_path=db_path)
    entries = list_history(db_path=db_path)
    assert entries[0]["favorite"] is True

    toggle_favorite(entry_id, db_path=db_path)
    entries = list_history(db_path=db_path)
    assert entries[0]["favorite"] is False


def test_list_history_empty_db_returns_empty_list(tmp_path):
    db_path = str(tmp_path / "history.db")

    assert list_history(db_path=db_path) == []
