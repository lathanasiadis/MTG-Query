from constants import Constants as C
from utils import flatten_list, load_json_file

def get_example_cards(tag, id_to_card, N=5):
    examples = ""
    i = 0
    for tagging in tag["taggings"]:
        tagged_card = id_to_card[tagging["oracle_id"]]
        oracle_text = tagged_card.get("oracle_text")
        if oracle_text is not None:
            # better separation between each example
            if i > 0:
                examples += "\n"

            examples += "- " + oracle_text + "\n"
            i += 1
            if i == N:
                break
    return examples

class TreeNode:
    def __init__(self, tag, example_cards=""):
        self.tag = tag
        self.children = []
        self.parents = []
        self.example_cards = example_cards

    def get_label(self):
        return self.tag["label"]

    def get_children(self):
        return [c.get_label() for c in self.children]

    def get_parents(self):
        return [p.get_label() for p in self.parents]

    def get_descendants(self):
        if self.children == []:
            return None
        descendants = [child.get_descendants() for child in self.children]
        descendants = list(filter(lambda x: x is not None, descendants))
        return flatten_list(self.get_children() + descendants)

    def get_ancestries(self, path=""):
        if path == "":
            new_path = self.get_label()
        else:
            new_path = self.get_label() + " > " + path

        if self.parents == []:
            return new_path

        ret = []
        for parent in self.parents:
            ret.append(parent.get_ancestries(new_path))
        return flatten_list(ret)

    def describe(self):
        text = f"Tag:\n{self.get_label()}\n"
        
        if self.parents != []:
            text += "\nHierarchy:\n"
            for item in self.get_ancestries():
                text += item + "\n"
        
        if self.tag["aliases"] != []:
            text += "\nAliases:\n"
            for al in self.tag["aliases"]:
                text += al + "\n"
        
        if self.tag["description"] is not None:
            text += f"\nDescription:\n{self.tag['description']}\n"

        if self.example_cards != "":
            text += f"\nExample cards:\n{self.example_cards}"
            
        return text

class TagTree:
    def __init__(self, otags_file):
        otags = load_json_file(otags_file)
        ocards = load_json_file(C.ORACLE["CARDS"])
        id_to_card = {card["oracle_id"]: card for card in ocards}

        self.root_nodes = []
        self.nodes = []
        
        self.name_to_id = {t["label"]: t["id"] for t in otags}

        # First pass: create a TreeNode for every tag        
        self.id_to_node = {t["id"]: TreeNode(t, get_example_cards(t, id_to_card)) for t in otags}

        # Second pass: add each tag's children to its TreeNode as TreeNodes themselves
        # Also, create a list of every parentless node (root nodes)
        for tag in otags:
            tag_node = self.node_from_id(tag["id"])
            tag_node.children = [self.node_from_id(child_id) for child_id in tag_node.tag["child_ids"]]
            tag_node.parents = [self.node_from_id(parent_id) for parent_id in tag_node.tag["parent_ids"]]
            
            if tag["parent_ids"] == []:
                self.root_nodes.append(tag_node)
            self.nodes.append(tag_node)

    def node_from_id(self, node_id):
        return self.id_to_node[node_id]

    def node_from_label(self, label):
        node_id = self.name_to_id.get(label)
        return self.node_from_id(node_id) if node_id is not None else None

if __name__ == "__main__":
    from pprint import pprint
    tt = TagTree(C.ORACLE["TAGS"])