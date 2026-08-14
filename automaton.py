from collections import defaultdict
from functools import reduce
import ahocorasick
from card import Card, load_cards

class Automaton:
    def __init__(self, cards: list[Card]):
        """
        Creates an Aho-Corasick automaton that finds card names in a given text
        """

        # stuff we want to be able to search for
        # key: normalized value (just lowercase for now)
        # value: original value
        needles = defaultdict(list)

        for c in cards:
            needles[c.name.lower()].append(c.name)

        normal_cards = filter(lambda x: x.card_faces == [], cards)
        normal_cards = [c.name for c in normal_cards]

        # We're looking for cards named "X, Y" (e.g Jetmir, Nexus of Revels)
        # This templating is usually found in legendary creatures, hence the variable name
        # We're mapping X to the full card name, so that the user can refer to it in a more natural way
        # Some legendaries have multiple versions of themselves.
        # In this case, the list of possible full names is kept, so that it can be shown to the user for
        # disambiguation.
        for card in normal_cards:
            if "," in card:
                name = card.split(",")[0]
                needles[name.lower()].append(card)

        # Map face names of cards with multiple faces to the full, official card name
        # e.g For the card "Fire // Ice", "Fire" and "Ice" are mapped to "Fire // Ice"
        split_cards = list(filter(lambda x: x.card_faces != [], cards))
        for card in split_cards:
            needles[card.card_faces[0].name.lower()].append(card.name)
            needles[card.card_faces[1].name.lower()].append(card.name)

        # Finally, we go over every split card part and find which ones are templated like legendaries
        # We want them to be retrievable from the legend name of both parts
        # E.g for a card A, B // C, D we want it to be retrievable by A or C
        split_cards = [[c.card_faces[0].name, c.card_faces[1].name] for c in split_cards]
        split_cards = reduce(lambda x, y: x + y, split_cards, initial=[])

        for card in split_cards:
            if "," in card:
                name = card.split(",")[0]
                needles[name.lower()].append(card)

        self._automaton = ahocorasick.Automaton()
        # Besides the original card's name (the value),
        # we're also keeping the key used to find it in the Trie.
        # this will help us with filtering unwanted results
        for k,v in needles.items():
            key = k.lower()
            val = v[0] if len(v) == 1 else v
            self._automaton.add_word(key, (key, val))
        self._automaton.make_automaton()

    def detect(self, haystack) -> list[str | list[str]]:
        found = defaultdict(list)
        key_to_orig = {}
        for end_idx, (key, orig) in self._automaton.iter(haystack.lower()):
            start_idx = end_idx - len(key) + 1

            start_ok = start_idx == 0 or not haystack[start_idx - 1].isalnum()
            end_ok = end_idx == len(haystack) - 1 or not haystack[end_idx+1].isalnum()

            if start_ok and end_ok:
                found[key].append((start_idx, end_idx))
                key_to_orig[key] = orig

        # After gathering the results, we want to filter out the ones that only appear
        # as substrings in other results.
        # For example, for the haystack "Glory Seeker", we want to return ["Glory Seeker"],
        # not ["Glory Seeker", "Glory", "Seeker"] ! (real cards btw)
        results = []
        for k,v in found.items():
            # returned results that are superstrings of the result we're examining
            candidate_keys = list(filter(lambda x: k in x and k != x, found.keys()))
            # no superstrings? add to final results
            if len(candidate_keys) == 0 and key_to_orig[k] not in results:
                results.append(key_to_orig[k])
                continue

            # for every occurence of the needle
            for start_idx, end_idx in v: 
                # for every superstring found of the needle
                for candidate_k in candidate_keys: 
                    # A needle occurence must not overlap with any superstring needle occurence
                    # in order to be appear on its own.
                    found_overlap = False
                    # for every occurence of the superstring needle
                    for candidate_start_idx, candidate_end_idx in found[candidate_k]:
                        if start_idx >= candidate_start_idx and end_idx <= candidate_end_idx:
                            found_overlap = True
                    if not found_overlap and key_to_orig[k] not in results:
                        results.append(key_to_orig[k])
                        break
        return results


def test_automaton(automaton, haystack, expected_needles):
    results = automaton.detect(haystack)
    if set(results) != set(expected_needles):
        print(f"[TEST FAILED] Haystack: {haystack}")
        print(f"\tExpected needles: {expected_needles}")
        print(f"\tActual results: {results}")


# Some tests
if __name__ == "__main__":
    cards = load_cards()
    automaton = Automaton(cards)

    # Legendary name expansion
    test_automaton(automaton, "Isshin", ["Isshin, Two Heavens as One"])
    # Split card name expansion
    test_automaton(automaton, "Fire", ["Fire // Ice"])
    # substring filtering (needle contained in a word -- we don't want to match "Ith")
    test_automaton(automaton, "with", []) 
    test_automaton(automaton, "ithw", [])
    # Substring filtering (needle contained in another needle)
    test_automaton(automaton, "Glory Seeker Glory Seeker Glory Seeker", ["Glory Seeker"])
    # add some extra "Glory"
    test_automaton(automaton, "Glory Glory Seeker Glory Glory Seeker Glory Seeker", ["Glory", "Glory Seeker"])


