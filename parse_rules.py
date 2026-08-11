import unicodedata
import os

from constants import Constants as C

if __name__ == "__main__":
    with open(C.COMP_RULES, "r") as f:
        lines = unicodedata.normalize("NFKD", f.read()).split("\n")

    lines = list(filter(lambda line: line != " ", lines))

    cur_file = None
    cur_dir = None
    in_kw_actions = False
    in_kw_abilities = False

    # These rules consist of over 90 and 200 sub-rules respectively, one each for each action and ability
    # Each one will be split to a separate file, since the context of the nearby actions/abilities does not matter
    kw_actions_dir = C.RULES_DIR + "/7. Additional Rules/701. Keyword Actions"
    kw_abiities_dir = C.RULES_DIR + "/7. Additional Rules/702. Keyword Abilities"

    os.makedirs(kw_actions_dir, exist_ok=True)
    os.makedirs(kw_abiities_dir, exist_ok=True)

    # Magic's comprehensive rules have a rigid structure that is exploited here
    # For example, we know that the rules are sorted and prefaced by a number.
    for line in lines:
        line = line.replace("/", ",")
        words = line.split(" ")

        if len(words[0]) == 2:
            cur_dir = C.RULES_DIR + "/" + line
            os.makedirs(cur_dir, exist_ok=True)
            continue

        num = words[0][:3]
        if num.isnumeric():
            if int(num) == 701:
                in_kw_actions = True
                in_kw_abilities = False
            elif int(num) == 702:
                in_kw_actions = False
                in_kw_abilities = True
            else:
                in_kw_actions = False
                in_kw_abilities = False

        if len(words[0]) == 4:
            if cur_file is not None:
                cur_file.close()

            # keyword actions and abilities: header rule parsed here
            if in_kw_actions:
                cur_file = open(kw_actions_dir + "/" + line + ".txt", "w")
            elif in_kw_abilities:
                cur_file = open(kw_abiities_dir + "/" + line + ".txt", "w")
            else:
                assert cur_dir is not None, "assumption about CR structure has been broken"
                cur_file = open(cur_dir + "/" + line + ".txt", "w")

        assert cur_file != None, "assumption about CR structure has been broken"

        # keyword actions and abilities: body (i.e not the header/general one) rules parsed here
        if in_kw_actions and (len(words[0]) > 6 or not words[0].startswith("701.1")):
            if words[0][-1] == ".":
                cur_file.close()
                cur_file = open(kw_actions_dir + "/" + line + ".txt", "w")
        if in_kw_abilities and (len(words[0]) > 6 or not words[0].startswith("702.1")):
            if words[0][-1] == ".":
                cur_file.close()
                cur_file = open(kw_abiities_dir + "/" + line + ".txt", "w")

        cur_file.write(line + "\n")

    assert cur_file != None, "assumption about CR structure has been broken"
    cur_file.close()
    
