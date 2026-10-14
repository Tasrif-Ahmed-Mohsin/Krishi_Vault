"""The backtest replays the price outlook on past seasons it has not seen."""

from src.models.backtest import backtest, backtest_season, seasons_to_test
from src.models.price_outlook import calibrate


def test_seasons_with_real_prices_and_crop_size():
    assert seasons_to_test() == [2023, 2024]


def test_a_season_is_never_predicted_by_a_model_that_saw_it():
    for season in seasons_to_test():
        label = f"{season}-{str(season + 1)[-2:]}"
        result = backtest_season(season)
        assert label not in result["trained_on"]
        assert result["trained_on"]
    assert [s["season"] for s in calibrate((2024,)).seasons] == ["2023-24"]
    assert len(calibrate().seasons) == 2  # the everyday model still learns from both


def test_only_past_drops_a_season_with_nothing_earlier():
    result = backtest(only_past=True)
    assert [s["season"] for s in result["seasons"]] == ["2024-25"]
    assert result["seasons"][0]["trained_on"] == ["2023-24"]


def test_scores_and_honest_limits():
    result = backtest()
    assert result["months_scored"] >= 10
    assert not result["enough_data"]
    assert any("far too few" in line for line in result["limits"])
    for method in ("outlook", "usual", "no_change"):
        assert result["summary"][method]["average_miss_pct"] >= 0
    for season in result["seasons"]:
        for row in season["months"]:
            assert row["actual"] > 0
            assert isinstance(row["outlook"]["inside"], bool)
            assert row["outlook"]["low"] <= row["outlook"]["mid"] <= row["outlook"]["high"]
    # The crop-size link is assumed when one season is left out, so the slope check is shown
    assert len(result["slope_check"]) == 5


def test_big_crop_season_says_sell_and_normal_season_says_store():
    seasons = {s["season"]: s for s in backtest()["seasons"]}
    assert seasons["2024-25"]["storage"]["outlook"]["says"] == "sell at the start"
    assert seasons["2024-25"]["storage"]["real"]["storing_paid"] is False
    assert seasons["2023-24"]["storage"]["outlook"]["says"].startswith("store until")
    assert seasons["2023-24"]["storage"]["real"]["storing_paid"] is True
