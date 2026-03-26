import os
import json
from config import URI, USERNAME, PASSWORD, FILES
from loaders import DnDKnowledgeGraph

if __name__ == "__main__":
    kg = DnDKnowledgeGraph(URI, USERNAME, PASSWORD)
    
    print("Constraints")
    labels_to_constrain = [
        "Class", "Subclass", "Race", "Subrace", "Level", "Spell", 
        "Skill", "Stat", "Background", "Equipment", "Weapon", "Armor", 
        "Feat", "Trait", "Feature", "Language", "Alignment", "MagicSchool", "Proficiency", "DamageType"
    ]
    with kg.driver.session() as session:
        for label in labels_to_constrain:
            query = f"""
            CREATE CONSTRAINT {label.lower()}_unique IF NOT EXISTS 
            FOR (n:{label}) REQUIRE (n.index, n.srd_version) IS UNIQUE
            """
            session.run(query)
    print("constraints created!")

    for version, paths in FILES.items():
        print(f"\n starting with SRD {version}")
        
        def load_json(key):
            filepath = paths.get(key)
            if not filepath:
                return None 
            
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                print(f"missing file: {filepath} (key: {key})")
                return None

        # Define order for loading
        loaders = [
            ("ability_scores", kg.load_ability_scores),
            ("skills", kg.load_skills),
            ("languages", kg.load_languages),
            ("alignments", kg.load_alignments),
            ("magic_schools", kg.load_magic_schools),
            ("equipment", kg.load_equipment),
            ("magic_items", kg.load_magic_items),
            ("proficiencies", kg.load_proficiencies),
            ("traits", kg.load_traits),
            ("feats", kg.load_feats),
            ("backgrounds", kg.load_backgrounds),
            ("races", kg.load_races),
            ("subraces", kg.load_subraces),
            ("classes", kg.load_classes),
            ("subclasses", kg.load_subclasses),
            ("levels", kg.load_levels),
            ("spells", kg.load_spells),
            ("features", kg.load_features),
            ("Features_Integrated", kg.load_features),
            ("Subclasses_Integrated", kg.load_subclasses),
            ("Spells_Integrated", kg.load_spells),
            ("Feats_Integrated", kg.load_feats),
            ("Traits_Integrated", kg.load_traits),
            ("Backgrounds_Integrated", kg.load_backgrounds),
            ("Alignments_Integrated", kg.load_alignments),
            ("Species_Integrated", kg.load_races)
        ]

      
        for key, loader_func in loaders:
            data = load_json(key)
            if data is not None and len(data) > 0:
                print(f"Loading {key.replace('_', ' ').title()}...")
                loader_func(data, version)

    kg.close()
    print("\nCompleted!")