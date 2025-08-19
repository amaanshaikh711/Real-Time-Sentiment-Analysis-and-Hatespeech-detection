# Test for offensive word count and vulgarity functions

from utils.cleaning import count_offensive_words, calculate_vulgarity_level

def test_offensive_count_and_vulgarity():
    text = "This is a badword and insult in the text."
    counts = count_offensive_words(text)
    assert 'total' in counts
    percentage, label = calculate_vulgarity_level(counts)
    assert isinstance(percentage, float)
    assert label in ["Mild", "Moderate", "Severe"]

if __name__ == "__main__":
    test_offensive_count_and_vulgarity()
    print("Tests passed.")
