from scripts.gold_scalp_state_survival_shadow.common import SELECTED_STATE_ACTIONS


def test_frozen_2026h2_state_action_list():
    assert SELECTED_STATE_ACTIONS == {
        "S08|UP|LOW|UP|NORM|WEAK": "SHORT",
        "S08|UP|MID|UP|COMP|WEAK": "SHORT",
        "S01|UP|LOW|UP|NORM|WEAK": "LONG",
        "S08|MIXED|LOW|UP|EXP|BULL": "SHORT",
    }
