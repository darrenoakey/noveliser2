"""Unit tests for the deterministic prose sanitizer."""

from sanitize import sanitize_prose


# ##################################################################
# fuse mid-word stray space
def test_fuses_lowercase_midword_split():
    assert sanitize_prose("The rain h ad stopped.") == "The rain had stopped."
    assert sanitize_prose("It wa s already late.") == "It was already late."
    assert sanitize_prose("She di d not look back.") == "She did not look back."


# ##################################################################
# leaves legit two-letter words alone
def test_leaves_legit_two_letter_words():
    # "he ran" must NOT become "heran"
    assert sanitize_prose("he ran") == "he ran"
    # "it is" must NOT become anything else
    assert sanitize_prose("it is") == "it is"
    assert sanitize_prose("so we left") == "so we left"


# ##################################################################
# splits fused sentence boundary
def test_splits_fused_boundary():
    assert sanitize_prose("He left.She stayed.") == "He left. She stayed."


# ##################################################################
# lowercases stray mid-word capital
def test_lowercases_stray_capital():
    assert sanitize_prose("he RAN down") == "he ran down"
    assert sanitize_prose("it WAS cold") == "it was cold"


# ##################################################################
# preserves clean prose
def test_preserves_clean_prose():
    text = "The hall was silent. Elena crossed it slowly, listening."
    assert sanitize_prose(text) == text


# ##################################################################
# combined
def test_combined_artifacts():
    text = "It wa s dark.She RAN and the h air lifted."
    out = sanitize_prose(text)
    assert out == "It was dark. She ran and the hair lifted."
